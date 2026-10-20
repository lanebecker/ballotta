"""The results back end, without a browser (docs/plans/2026-10-20-results.md, Tasks 2-4). About a second.

    python3 tests/test_results.py

1. The verdict rules (source/results_rules.py), one at a time, at and around every threshold the plan sets.
2. The parsers (source/results_parse.py) on real files, trimmed (tests/fixtures/results): the Nov 2025 City of Austin
   Prop Q across three counties equals the City's official canvass; the May 2026 runoff's SOS feed equals its Official
   Canvass Report; and each parser refuses a file that doesn't add up.
3. The build (source/build_results.py), end to end in a scratch folder, on those real files: Lane's downloads filed
   (and refused in the wrong folder), the partial rule from a missing county, official only through the contest's own
   canvasser, the ledger (seq, changed, corrected), the kill switch, and a stop (never a guess) on anything unmapped.
"""
import pathlib, sys, traceback

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'source'))
import results_rules as R, results_parse as P, build_results as B
import copy, shutil, tempfile
import io, json, re, zipfile
FX = ROOT / 'tests/fixtures/results'

TESTS = []
def test(fn): TESTS.append(fn); return fn
V = lambda *pairs: list(pairs)


# ---------------------------------------------------------------- 1. the verdict rules
@test
def zero_votes_name_nobody():
    assert R.unofficial('candidate', V(('A', 0), ('B', 0))) == ('none', [], [])
    assert R.unofficial('measure', V(('FOR', 0), ('AGAINST', 0))) == ('none', [], [])
    assert R.unofficial('candidate', V(('A', 0), ('B', 0), ('C', 0)), majority=True) == ('none', [], [])

@test
def the_twenty_vote_floor_and_the_one_point_rule():
    # 19 votes ahead is too close however big the share; 20 is enough once it's also a point
    assert R.unofficial('candidate', V(('A', 119), ('B', 100))) == ('too_close', [], [])          # 8.7 points, 19 votes
    assert R.unofficial('candidate', V(('A', 120), ('B', 100))) == ('leading', ['A'], [])
    # Cedar Park Place Two, May 2026 (Task 1 finding 9): 337 to 329 is 1.2 points but 8 votes
    assert R.unofficial('candidate', V(('A', 337), ('B', 329)))[0] == 'too_close'
    # a point, exactly: 20 votes of 2,000 is 1.0 point -> leading; 19.99 points' worth never rounds up
    assert R.unofficial('candidate', V(('A', 1010), ('B', 990)))[0] == 'leading'
    assert R.unofficial('candidate', V(('A', 10049), ('B', 9951)))[0] == 'too_close'                # 98 votes, 0.49 points
    assert R.clear(10100, 9900, 20000) and not R.clear(10099, 9901, 20000)                          # 1.0 vs 0.99 points

@test
def leaders_are_named_in_vote_order_never_ballot_order():
    assert R.unofficial('candidate', V(('A', 100), ('B', 5000), ('C', 300))) == ('leading', ['B'], [])

@test
def vote_for_two_tests_the_cut_between_second_and_third():
    assert R.unofficial('candidate', V(('A', 5000), ('B', 4000), ('C', 3000)), seats=2) == ('leading', ['A', 'B'], [])
    assert R.unofficial('candidate', V(('A', 5000), ('B', 4000), ('C', 3990)), seats=2)[0] == 'too_close'
    # a tie at the cut, official: state law decides
    assert R.official('candidate', V(('A', 5000), ('B', 4000), ('C', 4000)), seats=2) == ('tied', [], [])
    assert R.official('candidate', V(('A', 5000), ('B', 4000), ('C', 3999)), seats=2) == ('won', ['A', 'B'], [])

@test
def unopposed_only_without_a_declared_write_in():
    assert R.unofficial('candidate', V(('A', 0))) == ('unopposed', ['A'], [])
    assert R.unofficial('candidate', V(('A', 900), ('B', 800)), seats=2) == ('unopposed', ['A', 'B'], [])   # N for N
    assert R.official('candidate', V(('A', 900), ('B', 800)), seats=2) == ('elected', ['A', 'B'], [])
    # County Clerk (c053) has a declared write-in: the ordinary rules apply
    assert R.unofficial('candidate', V(('A', 9000), ('W', 300)), write_ins=('W',)) == ('leading', ['A'], [])
    assert R.official('candidate', V(('A', 9000), ('W', 300)), write_ins=('W',)) == ('won', ['A'], [])
    # two seats, one candidate, one declared write-in: both can be elected; no index past the end
    assert R.unofficial('candidate', V(('A', 9000), ('W', 30)), seats=2, write_ins=('W',)) == ('leading', ['A', 'W'], [])
    assert R.official('candidate', V(('A', 9000), ('W', 0)), seats=2, write_ins=('W',)) == ('won', ['A'], [])

@test
def measures_are_symmetric_around_half():
    m = lambda f, a: R.unofficial('measure', V(('FOR', f), ('AGAINST', a)))[0]
    assert m(5000, 5000) == 'too_close'                     # 50.0%
    assert m(5040, 4960) == 'too_close'                     # 50.4%
    assert m(5050, 4950) == 'passing'                       # 50.5%, 100 votes
    assert m(4950, 5050) == 'failing'                       # 49.5%
    assert m(4960, 5040) == 'too_close'
    assert m(101, 99) == 'too_close' and m(60, 40) == 'passing' and m(59, 40) == 'too_close'   # the 20-vote floor
    o = lambda f, a: R.official('measure', V(('FOR', f), ('AGAINST', a)))[0]
    assert (o(5001, 5000), o(5000, 5000), o(4999, 5000)) == ('passed', 'failed_tie', 'failed')

@test
def majority_contests_with_three_or_more():
    mj = lambda *v, **k: R.unofficial('candidate', V(*v), majority=True, **k)
    assert mj(('A', 5300), ('B', 3000), ('C', 1700)) == ('leading', ['A'], [])           # 53%
    assert mj(('A', 5200), ('B', 3000), ('C', 1800)) == ('may_runoff', [], [])           # exactly 52%: not over
    assert mj(('A', 4800), ('B', 3000), ('C', 2200)) == ('may_runoff', [], [])           # exactly 48%: not under
    assert mj(('A', 4700), ('B', 3000), ('C', 2300)) == ('runoff', [], ['A', 'B'])       # 47%, second clears third
    assert mj(('A', 4700), ('B', 2700), ('C', 2600)) == ('runoff', [], ['A', 'B'])       # second clears third by exactly a point
    assert mj(('A', 4700), ('B', 2700), ('C', 2610)) == ('runoff', [], [])               # second and third within a point
    # a declared write-in counts toward the three
    assert mj(('A', 4700), ('B', 4300), ('W', 1000), write_ins=('W',)) == ('runoff', [], ['A', 'B'])

@test
def two_way_majority_contests_use_the_leading_test():
    assert R.unofficial('candidate', V(('A', 5060), ('B', 4940)), majority=True) == ('leading', ['A'], [])   # 50.6%
    assert R.unofficial('candidate', V(('A', 5004), ('B', 4996)), majority=True)[0] == 'too_close'
    assert R.official('candidate', V(('A', 5000), ('B', 5000)), majority=True) == ('tied_runoff', [], [])
    assert R.official('candidate', V(('A', 5001), ('B', 5000)), majority=True) == ('won', ['A'], [])

@test
def official_majority_contests():
    o = lambda *v: R.official('candidate', V(*v), majority=True)
    assert o(('A', 5001), ('B', 3000), ('C', 1999)) == ('won', ['A'], [])               # 50.01%
    assert o(('A', 5000), ('B', 3000), ('C', 2000)) == ('runoff', [], ['A', 'B'])       # exactly half is not a majority
    assert o(('A', 4000), ('B', 3000), ('C', 3000)) == ('tied_second', [], [])          # §2.023(c)

@test
def official_ties_by_office():
    tie = V(('A', 5000), ('B', 5000), ('C', 10))
    assert R.official('candidate', tie, cid='c044') == ('tied', [], [])                  # County Judge: §2.002
    for cid in ('c006', 'c007', 'c008', 'c009', 'c010'):                                 # executive offices: the Legislature
        assert R.official('candidate', tie, cid=cid) == ('tied_legislature', [], []), cid
    assert R.official('candidate', tie, cid='c011') == ('tied', [], [])

@test
def a_missing_county_widens_every_margin():
    # 1,000 ahead of 11,000 cast, s still out: at worst 1,000 - s ahead of 11,000 + s, which is a point while s <= 881
    assert R.unofficial('candidate', V(('A', 6000), ('B', 5000)), slack=881)[0] == 'leading'
    assert R.unofficial('candidate', V(('A', 6000), ('B', 5000)), slack=882)[0] == 'too_close'
    assert R.unofficial('candidate', V(('A', 6000), ('B', 5000)), slack=0)[0] == 'leading'
    # unknown registration: no verdict until the file arrives
    assert R.unofficial('candidate', V(('A', 6000), ('B', 50)), slack=None) == ('none', [], [])
    assert R.unofficial('measure', V(('FOR', 6000), ('AGAINST', 50)), slack=None) == ('none', [], [])
    # a measure: the slack counts against the way it leans
    # 6,000 for of 10,000: at worst 6,000 of 10,000 + s, which is 50.5% while s <= 1,881 (and mirrored for against)
    assert R.unofficial('measure', V(('FOR', 6000), ('AGAINST', 4000)), slack=1881)[0] == 'passing'
    assert R.unofficial('measure', V(('FOR', 6000), ('AGAINST', 4000)), slack=1882)[0] == 'too_close'
    assert R.unofficial('measure', V(('FOR', 4000), ('AGAINST', 6000)), slack=1881)[0] == 'failing'
    assert R.unofficial('measure', V(('FOR', 4000), ('AGAINST', 6000)), slack=1882)[0] == 'too_close'
    # the majority zone: 53% now, but with 1,000 out it could fall under 52%
    assert R.unofficial('candidate', V(('A', 5300), ('B', 3000), ('C', 1700)), majority=True, slack=1000)[0] == 'may_runoff'
    # and the runoff call: 47% now could pass 48% with what's out
    assert R.unofficial('candidate', V(('A', 4700), ('B', 3000), ('C', 2300)), majority=True, slack=500)[0] == 'may_runoff'
    # unopposed stays unopposed whatever is missing
    assert R.unofficial('candidate', V(('A', 10)), slack=None) == ('unopposed', ['A'], [])

@test
def annexations_get_one_outcome_line():
    assert [R.annex_note(d, a) for d, a in ((True, True), (False, True), (True, False), (False, False))] == \
        ['annex_both', 'annex_district_rejected', 'annex_area_rejected', 'annex_both_rejected']

@test
def percents_round_to_two_places_and_never_divide_by_zero():
    assert R.pct(1, 3) == 33.33 and R.pct(0, 0) == 0 and R.pct(2, 3) == 66.67


# ---------------------------------------------------------------- 2. the parsers, on real files
def fx(name): return (FX / name).read_bytes()

@test
def prop_q_across_three_counties_equals_the_official_canvass():
    # Task 1 finding 1: Travis + Williamson + Hays = the City's canvass exhibit (Council backup, Nov 17, 2025)
    reps = [P.parse_clarity(fx('travis-2025-11-detail.xml')), P.parse_williamson(fx('williamson-2025-11.html')),
            P.parse_hays(fx('hays-2025-11-official.pdf'))]
    tot = {}
    for r in reps:
        q = [c for c in r['contests'].values() if P.norm(c['name']) == 'CITY OF AUSTIN PROPOSITION Q']
        assert len(q) == 1, (r['label'], len(q))
        for n, v in q[0]['choices']: tot[P.norm(n)] = tot.get(P.norm(n), 0) + v
    assert tot == {'FOR': 62952, 'AGAINST': 109375}, tot

@test
def clarity_reads_its_county_time_zone_and_registration():
    r = P.parse_clarity(fx('travis-2025-11-detail.xml'))
    assert (r['source'], r['label'], r['posted']) == ('travis', 'Travis County', '2025-11-12T15:00'), r['posted']
    q = [c for c in r['contests'].values() if 'Proposition Q' in c['name']][0]
    assert q['registered'] > 600000 and q['vote_for'] == 1
    p1 = [c for c in r['contests'].values() if c['name'] == 'State of Texas Proposition 1'][0]
    assert sum(v for _, v in p1['choices']) == 222442          # Travis's official count (Task 1 finding 6)
    z = io.BytesIO()
    with zipfile.ZipFile(z, 'w') as zf: zf.writestr('detail.xml', fx('travis-2025-11-detail.xml'))
    assert P.parse_clarity(z.getvalue())['contests'] == r['contests'], 'the zip Lane downloads reads the same'

@test
def clarity_refuses_what_it_cant_trust():
    x = fx('travis-2025-11-detail.xml').decode('utf-8')
    for name, bad in (('another county', x.replace('<Region>Travis</Region>', '<Region>Harris</Region>')),
                      ('a timestamp with no zone', re.sub(r'(<Timestamp>[^<]*) CST<', r'\1<', x)),
                      ('a choice whose vote types disagree with it', x.replace('totalVotes="', 'totalVotes="1', 1)),
                      ('a precinct that disagrees with its vote type', re.sub(r'(<Choice .*?<Precinct name="\d+" votes=")', r'\g<1>1', x, count=1, flags=re.S)),
                      ('not XML', '<ElectionResult>')):
        try: P.parse_clarity(bad.encode('utf-8'))
        except P.BadFile: continue
        raise AssertionError(name + ' was accepted')

@test
def the_sos_feed_reads_races_and_the_canvass_flag():
    r = P.parse_sos(fx('sos-58314.json'))
    assert r['posted'] == '2026-06-17T00:57' and r['canvass_report'] and len(r['contests']) == 27
    assert P.parse_sos(fx('sos-58314.json'), zone='UTC')['posted'] == '2026-06-16T19:57'   # the reading to settle Nov 3
    old = P.parse_sos(fx('sos-51031.json'))
    assert not old['canvass_report'] and old['posted'] == '2025-11-06T04:18', 'the frozen Nov 2025 feed never says canvassed'
    lt = [c for c in r['contests'].values() if c['name'] == 'LIEUTENANT GOVERNOR'][0]
    assert lt['choices'] == [['VIKKI GOODWIN', 376757], ['MARCOS ISAIAS VELEZ', 179238]]
    f = json.loads(fx('sos-58314.json'))
    sw = json.loads(__import__('base64').b64decode(f['StateWide'])); sw['Races'][0]['T'] += 1
    f['StateWide'] = __import__('base64').b64encode(json.dumps(sw).encode()).decode()
    try: P.parse_sos(json.dumps(f).encode()); raise AssertionError('a race whose total disagrees was accepted')
    except P.BadFile: pass

@test
def the_sos_canvass_report_equals_the_feed_name_by_name():
    feed, can = P.parse_sos(fx('sos-58314.json')), P.parse_sos_canvass(fx('sos-58314-canvass.pdf'))
    assert can['posted'] == '2026-08-03T14:17' and len(can['contests']) == 27
    for r in feed['contests'].values():
        o = can['contests'][P.norm(r['name'])]; names = [n for n, _ in r['choices']]
        got = sorted((P.match(n, names), v) for n, v in o['choices'])
        assert got == sorted(map(tuple, r['choices'])), (r['name'], o['choices'])   # wrapped and shortened names too

@test
def names_match_only_when_exactly_one_fits():
    assert P.match('JESUS GARCIA, JR', ['JESUS TOMAS GARCIA, JR', 'NOE GARZA']) == 'JESUS TOMAS GARCIA, JR'
    assert P.match('greg abbott (i)', ['GREG ABBOTT', 'GINA HINOJOSA']) == 'GREG ABBOTT'
    assert P.match('Bradford \u201cBrad\u201d Hall', ['BRADFORD "BRAD" HALL']) == 'BRADFORD "BRAD" HALL'
    assert P.match('SMITH', ['JOHN SMITH', 'JANE SMITH']) is None, 'two fit: no guess'
    assert P.match('Someone Else', ['JOHN SMITH']) is None

@test
def williamson_refuses_a_page_whose_two_copies_disagree():
    r = P.parse_williamson(fx('williamson-2025-11.html'))
    assert r['posted'] == '2026-09-30T14:07' and list(r['contests'].values())[0]['choices'] == [['For', 2498], ['Against', 5028]]
    bad = fx('williamson-2025-11.html').decode('utf-8').replace('class="content-data">2,498<', 'class="content-data">2,499<')
    try: P.parse_williamson(bad.encode()); raise AssertionError('accepted')
    except P.BadFile: pass

@test
def hays_reads_every_contest_and_its_run_time():
    r = P.parse_hays(fx('hays-2025-11-official.pdf'))
    assert r['posted'] == '2025-11-10T16:39' and r['official'] and len(r['contests']) == 88, (r['posted'], len(r['contests']))
    smd = r['contests']['CITY OF BUDA SINGLE MEMBER DISTRICT (SMD) C']
    assert smd['choices'] == [['Jeffrey Morales', 460], ['Emily Jones', 154], ['Kimberly Goodman', 465]]


# ---------------------------------------------------------------- 3. the build, end to end on real files
SENATE = next(k for k, c in P.parse_sos(fx('sos-53815-travis.json'))['contests'].items() if c['name'].strip() == 'U. S. SENATOR')
PROPQ = next(k for k, c in P.parse_clarity(fx('travis-2025-11-detail.xml'))['contests'].items() if 'Proposition Q' in c['name'])
MAP = {
    'meta': {'election': '2026-11-03', 'sos_election': '53815', 'sos_time_zone': 'America/Chicago', 'late_until': '2026-11-17'},
    'canvassers': {'state': {'label': 'the state', 'kind': 'state'}, 'city-of-austin': {'label': 'the Austin City Council', 'kind': 'local'}},
    'contests': {
        'c001': {'source': 'sos', 'canvasser': 'state', 'keys': {'sos': SENATE, 'travis': None}, 'sos_name': 'U. S. SENATOR',
                 'write_ins': [{'name': n} for n in ('Avery Ayers', 'Bradford "Brad" Hall', 'Zul Mohamed', 'Jade Simmons')]},
        # Prop Q (Nov 2025) stands in for Austin's Prop A (c071): three counties, real numbers
        'c071': {'source': 'counties', 'canvasser': 'city-of-austin', 'electorate': ['travis', 'williamson', 'hays'],
                 'keys': {'travis': PROPQ, 'williamson': '46', 'hays': 'CITY OF AUSTIN PROPOSITION Q'}, 'registered': {'hays': 565}},
    }}

class Scratch:
    """A results folder in a temp dir, with the real files put where the workflow and Lane put them."""
    def __init__(self, travis=True, williamson=True, hays=True, sos=True):
        self.d = pathlib.Path(tempfile.mkdtemp()); self.res = self.d / 'results'
        for c in ('travis', 'bastrop', 'williamson', 'hays'): (self.res / 'inbox' / c).mkdir(parents=True)
        if travis: (self.res / 'inbox/travis/detailxml.xml').write_bytes(fx('travis-2025-11-detail.xml'))
        if williamson: (self.res / 'inbox/williamson/results.html').write_bytes(fx('williamson-2025-11.html'))
        if hays: (self.res / 'inbox/hays/cumulative.pdf').write_bytes(fx('hays-2025-11-official.pdf'))
        B.file_inbox(self.res)
        if sos:
            data = fx('sos-53815-travis.json'); r = P.parse_sos(data)
            d = B.raw_dir(self.res, 'sos', r['posted'], data); d.mkdir(parents=True); (d / 'election.json').write_bytes(data)
    def official(self, **o): (self.res / 'official.json').write_text(json.dumps(o))
    def exclude(self, *x): (self.res / 'excluded.json').write_text(json.dumps(list(x)))
    def build(self, prev=None, mp=None): return B.build(res=self.res, mp=mp or MAP, prev=prev)
    def raw(self, source): return [f.relative_to(self.res).as_posix() for f in sorted((self.res / 'raw' / source).rglob('*')) if f.is_file()]
    def close(self): shutil.rmtree(self.d)

@test
def downloads_are_filed_by_county_and_posted_time():
    s = Scratch(sos=False)
    try:
        assert s.raw('travis') and re.fullmatch(r'raw/travis/2025-11-12T15-00-[0-9a-f]{8}/detailxml.xml', s.raw('travis')[0]), s.raw('travis')
        assert not [f for f in (s.res / 'inbox/travis').iterdir()], 'the inbox is emptied'
        (s.res / 'inbox/travis/again.xml').write_bytes(fx('travis-2025-11-detail.xml')); assert B.file_inbox(s.res) == [], 'the same file twice is filed once'
        (s.res / 'inbox/bastrop/detailxml.xml').write_bytes(fx('travis-2025-11-detail.xml'))
        try: B.file_inbox(s.res); raise AssertionError('a Travis file in the Bastrop folder was filed')
        except B.Problem as e: assert 'inbox/travis/' in str(e), e
    finally: s.close()

@test
def three_counties_make_one_unofficial_result():
    s = Scratch()
    try:
        out, ch = s.build()
        e = out['contests']['c071']
        assert (e['state'], e['verdict']) == ('unofficial', 'failing') and e['choices'] == [['FOR', 62952, 36.53, False], ['AGAINST', 109375, 63.47, False]], e
        assert [x[0] for x in e['sources']] == ['Williamson County', 'Travis County', 'Hays County'], e['sources']   # newest first
        assert e['travis'] == [['FOR', 60419, 36.69], ['AGAINST', 104256, 63.31]] and e['canvasser'] == 'the Austin City Council'
        assert e['canvass'] == {'kind': 'local', 'by': '2026-11-17', 'on': None, 'done': None}
        sen = out['contests']['c001']                                          # the live Nov 3 feed: no votes yet
        assert (sen['state'], sen['verdict']) == ('counting', 'none') and [x[0] for x in sen['choices'] if x[3]] == ['Avery Ayers', 'Bradford "Brad" Hall', 'Zul Mohamed', 'Jade Simmons']
        assert out['seq'] == 1 and ch['verdict_changed'] and check_results_ok(out)
    finally: s.close()

def check_results_ok(out):
    import check_results; bad = check_results.check(out, check_results.answer_key()); assert not bad, bad; return True

@test
def a_missing_county_makes_it_partial():
    s = Scratch(hays=False)
    try:
        e = s.build()[0]['contests']['c071']
        assert (e['state'], e['verdict'], e['missing']) == ('partial', 'failing', ['Hays County']), e   # 565 registered can't close 46,000
        mp = copy.deepcopy(MAP); del mp['contests']['c071']['registered']
        e = s.build(mp=mp)[0]['contests']['c071']
        assert (e['state'], e['verdict']) == ('partial', 'none'), 'unknown registration: no verdict until the file arrives'
        mp['contests']['c071']['keys']['hays'] = None
        s2 = Scratch(); e = s2.build(mp=mp)[0]['contests']['c071']; s2.close()
        assert e['state'] == 'partial' and e['missing'] == ['Hays County'], 'an unmapped county counts as missing, never as zero'
    finally: s.close()

@test
def official_only_through_its_own_canvasser():
    s = Scratch()
    try:
        s.official(canvasses={'state': {'canvassed': '2026-12-02'}})
        try: s.build(); raise AssertionError('canvassed with no votes loaded was accepted')
        except B.Problem as e: assert 'c001' in str(e) and 'no votes' in str(e), e
        mp = copy.deepcopy(MAP); del mp['contests']['c001']
        e = s.build(mp=mp)[0]['contests']['c071']; assert e['state'] == 'unofficial', 'the state canvass never makes a city measure official'
        s.official(canvasses={'city-of-austin': {'canvassed': '2026-11-12', 'link': 'https://example.org'}})
        e = s.build()[0]['contests']['c071']
        assert (e['state'], e['verdict'], e['canvass']['done']) == ('official', 'failed', '2026-11-12'), e
        assert e['official_numbers'] is False, 'files posted before the canvass: the last unofficial count (W11)'
        s.official(canvasses={'city-of-austin': {'canvassed': '2026-11-12', 'recount': {'link': 'https://example.org/recount'}}})
        assert s.build()[0]['contests']['c071']['state'] == 'recount'
        s.official(canvasses={'city-of-austin': {'canvassed': '2026-11-20'}})
        try: s.build(); raise AssertionError('a canvass after Nov 17 was accepted')
        except B.Problem as e: assert 'Nov 6' in str(e), e
    finally: s.close()

@test
def the_ledger_counts_changes_and_names_corrections():
    s = Scratch()
    try:
        one, _ = s.build()
        same, ch = s.build(prev=one)
        assert same == one and same['seq'] == 1 and not ch['verdict_changed'], 'nothing new: seq stays'
        s.official(canvasses={'city-of-austin': {'canvassed': '2026-11-12'}})
        two, ch = s.build(prev=one)
        assert two['seq'] == 2 and two['contests']['c071']['changed'] == 2 and two['contests']['c001']['changed'] == 1 and ch['verdict_changed']
        assert any('c071' in ln and 'unofficial failing → official failed' in ln for ln in ch['lines']), ch['lines']
        # Hays's file was bad: excluded, the verdict moves (official -> partial is refused, so take the canvass back too)
        s.official()
        hays = s.raw('hays')[0]
        s.exclude({'path': hays, 'reason': 'test', 'date': '2026-11-09', 'contests': ['c071']})
        mp = copy.deepcopy(MAP); del mp['contests']['c071']['registered']
        three, ch = s.build(prev=two, mp=mp)
        e = three['contests']['c071']
        assert (e['state'], e['verdict'], e['corrected'], three['seq']) == ('partial', 'none', '2026-11-09', 3), e
    finally: s.close()

@test
def the_kill_switch_hides_everything_and_says_so():
    s = Scratch()
    try:
        one, _ = s.build(); s.official(withdrawn=True)
        out, ch = s.build(prev=one)
        assert out['withdrawn'] and out['contests'] == {} and out['seq'] == 2 and ch['verdict_changed'] and 'WITHDRAWN' in ch['lines'][0]
    finally: s.close()

@test
def anything_unmapped_stops_the_build():
    s = Scratch()
    try:
        mp = copy.deepcopy(MAP); mp['contests']['c001']['write_ins'] = mp['contests']['c001']['write_ins'][:3]
        try: s.build(mp=mp); raise AssertionError('a write-in the map lacks was dropped silently')
        except B.Problem as e: assert 'JADE SIMMONS' in str(e), e
        mp = copy.deepcopy(MAP); mp['contests']['c071']['keys']['williamson'] = '999'
        try: s.build(mp=mp); raise AssertionError('a key the file lacks was accepted')
        except B.Problem as e: assert "'999'" in str(e), e
        data = fx('sos-53815-travis.json').replace(b'"Version"', b' "Version"'); r = P.parse_sos(data)
        d = B.raw_dir(s.res, 'sos', r['posted'], data); d.mkdir(parents=True); (d / 'election.json').write_bytes(data)
        try: s.build(); raise AssertionError('two different files posted the same minute were accepted')
        except B.Problem as e: assert 'exclude one' in str(e), e
    finally: s.close()


def main():
    failed = 0
    for fn in TESTS:
        try:
            fn(); print('PASS', fn.__name__)
        except Exception as e:
            failed += 1; print('FAIL', fn.__name__, '-', (str(e) or type(e).__name__)[:600])
            if os_debug(): traceback.print_exc()
    print(f'{len(TESTS) - failed}/{len(TESTS)} passed (results)')
    sys.exit(1 if failed else 0)

def os_debug():
    import os; return bool(os.environ.get('BALLOTTA_DEBUG'))

if __name__ == '__main__':
    main()
