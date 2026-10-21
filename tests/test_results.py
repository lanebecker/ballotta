"""The results back end, without a browser (docs/plans/2026-10-20-results.md, Tasks 2-4). About a second.

    python3 tests/test_results.py

1. The verdict rules (source/results_rules.py), one at a time, at and around every threshold the plan sets.
2. The parsers (source/results_parse.py) on real files, trimmed (tests/fixtures/results): the Nov 2025 City of Austin
   Prop Q across three counties equals the City's official canvass; the May 2026 runoff's SOS feed equals its Official
   Canvass Report; and each parser refuses a file that doesn't add up.
3. The build (source/build_results.py), end to end in a scratch folder, on those real files: Lane's downloads filed
   (and refused in the wrong folder), the partial rule from a missing county, official only through the contest's own
   canvasser, the ledger (seq, changed, corrected), the kill switch, and a stop (never a guess) on anything unmapped.
4. The fetcher (source/fetch_results.py) with a stand-in network: what it fetches, when, and that one failure doesn't
   stop the rest.
5. The map (source/results_map.json, written by source/build_results_map.py): every contest, every canvasser, every
   county known; the 42 SOS contests against the live Nov 3 feed, write-ins included, through a full build.
"""
import pathlib, sys, traceback

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'source'))
import results_rules as R, results_parse as P, build_results as B, fetch_results as FR
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
    assert R.official('candidate', V(('A', 5000), ('B', 4000), ('C', 3999)), seats=2) == ('elected', ['A', 'B'], [])   # several winners: elected (#135)

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
    assert R.official('candidate', V(('A', 9000), ('W', 0)), seats=2, write_ins=('W',)) == ('elected', ['A'], [])   # a several-seat race, one filled (#135)

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
def road_bonds_need_two_thirds():
    # Tex. Const. art. III §52(b): of 3,000 cast, two-thirds is 2,000; half a point and 10 switching voters either side
    m = lambda f, n=3000, **k: R.unofficial('measure', V(('FOR', f), ('AGAINST', n - f)), needs='two_thirds', **k)[0]
    assert (m(2015), m(2014), m(1986), m(1985)) == ('passing', 'too_close', 'too_close', 'failing')
    assert m(1900) == 'failing', '63% is a clear majority, and still fails a two-thirds measure'
    o = lambda f, n=3000: R.official('measure', V(('FOR', f), ('AGAINST', n - f)), needs='two_thirds')[0]
    assert (o(2000), o(1999), o(1500)) == ('passed', 'failed', 'failed'), 'at least two-thirds; a tie just fails'

@test
def an_unsettled_threshold_gives_a_verdict_only_where_both_agree():
    u = lambda f, n=10000: R.unofficial('measure', V(('FOR', f), ('AGAINST', n - f)), needs='unsure')[0]
    assert (u(7000), u(6000), u(4000)) == ('passing', 'too_close', 'failing')
    o = lambda f, n=10000: R.official('measure', V(('FOR', f), ('AGAINST', n - f)), needs='unsure')[0]
    assert (o(7000), o(4000)) == ('passed', 'failed')
    try: o(6000); raise AssertionError('canvassed at 60% with the threshold unsettled was decided')
    except ValueError: pass

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
def an_unsettled_majority_rule_gives_a_verdict_only_where_both_agree():
    u = lambda *v: R.unofficial('candidate', V(*v), majority='unsure')
    assert u(('A', 6000), ('B', 3000), ('C', 1000)) == ('leading', ['A'], []), '60%: leads either way'
    assert u(('A', 4500), ('B', 3500), ('C', 2000)) == ('none', [], []), '45%: leads a plurality, headed to a runoff under a majority'
    assert u(('A', 5060), ('B', 4940)) == ('leading', ['A'], []) and u(('A', 5040), ('B', 4960))[0] == 'too_close', 'two candidates: the same either way'
    o = lambda *v: R.official('candidate', V(*v), majority='unsure')
    assert o(('A', 6000), ('B', 3000), ('C', 1000)) == ('won', ['A'], [])
    try: o(('A', 4500), ('B', 3500), ('C', 2000)); raise AssertionError('canvassed at 45% with the rule unsettled was decided')
    except ValueError: pass

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
        # the change list, in plain words: first-seen contests with no votes are one line
        assert ch['lines'] == ['- 1 contest now shown, no votes yet', '- City of Austin Proposition A: Failing (unofficial) (c071)'], ch['lines']
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
        assert '- City of Austin Proposition A: Failing (unofficial) → Failed (official) (c071)' in ch['lines'], ch['lines']
        # Hays's file was bad: excluded, the verdict moves (official -> partial is refused, so take the canvass back too)
        s.official()
        hays = s.raw('hays')[0]
        s.exclude({'path': hays, 'reason': 'test', 'date': '2026-11-09', 'contests': ['c071']})
        mp = copy.deepcopy(MAP); del mp['contests']['c071']['registered']
        three, ch = s.build(prev=two, mp=mp)
        e = three['contests']['c071']
        assert (e['state'], e['verdict'], e['corrected'], three['seq']) == ('partial', 'none', '2026-11-09', 3), e
        assert '- City of Austin Proposition A: Failed (official) → No call yet (partial: Hays County missing) (c071)' in ch['lines'], ch['lines']
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


def clarity(contests, stamp='11/5/2026 9:00:00 AM CST', region='Travis'):
    """A valid Detail XML with chosen numbers: {key: (name, [(choice, votes)])}, one precinct, one vote type."""
    out = [f'<?xml version="1.0" encoding="utf-8"?><ElectionResult><Timestamp>{stamp}</Timestamp><ElectionName>Test</ElectionName>'
           f'<ElectionDate>11/3/2026</ElectionDate><Region>{region}</Region><VoterTurnout totalVoters="5000" ballotsCast="0" voterTurnout="0">'
           '<Precincts><Precinct name="101" totalVoters="5000" ballotsCast="0" voterTurnout="0" percentReporting="4" /></Precincts></VoterTurnout>']
    for k, (name, ch) in contests.items():
        out.append(f'<Contest key="{k}" text="{name}" voteFor="1" isQuestion="false" precinctsReporting="1" precinctsReported="1">')
        for i, (n, v) in enumerate(ch):
            out.append(f'<Choice key="{i:03d}" text="{n}" party="NON" totalVotes="{v}"><VoteType name="Election Day" votes="{v}">'
                       f'<Precinct name="101" votes="{v}" /></VoteType></Choice>')
        out.append('</Contest>')
    return ('\n'.join(out) + '</ElectionResult>').encode('utf-8')

def scratch_with(files):
    """A results folder holding just these Travis files (filed through the inbox, as Lane's are)."""
    d = pathlib.Path(tempfile.mkdtemp()); res = d / 'results'
    for c in ('travis', 'bastrop', 'williamson', 'hays'): (res / 'inbox' / c).mkdir(parents=True)
    for i, data in enumerate(files):
        (res / 'inbox/travis' / f'f{i}.xml').write_bytes(data); B.file_inbox(res)
    return d, res

def one_map(**contests):
    mp = copy.deepcopy(MAP); mp['contests'] = contests
    mp['canvassers'].update({k: {'label': f'the {k} board', 'kind': 'local'} for k in ('eastwood-mud', 'esd-9', 'esd-4')})
    return mp

M = lambda key, **k: {'source': 'counties', 'canvasser': k.pop('canvasser', 'eastwood-mud'), 'electorate': ['travis'], 'keys': {'travis': key}, **k}
FA = lambda f, a: [('FOR', f), ('AGAINST', a)]

@test
def clarity_times_in_utc_read_as_austin_time():
    assert P.parse_clarity(clarity({}, stamp='11/5/2026 3:00:00 PM UTC'))['posted'] == '2026-11-05T09:00'   # CST: UTC-6
    assert P.parse_clarity(clarity({}, stamp='10/30/2026 3:00:00 PM UTC'))['posted'] == '2026-10-30T10:00'  # CDT: UTC-5
    assert P.parse_clarity(clarity({}, stamp='11/5/2026 9:00:00 AM CST'))['posted'] == '2026-11-05T09:00'

@test
def a_failed_confirmation_marks_the_whole_district():
    d, res = scratch_with([clarity({'1': ('Confirmation', FA(300, 700)), '2': ('Bonds', FA(600, 400))})])
    try:
        mp = one_map(c147=M('1'), c148=M('2', depends_on='c147'))
        out, _ = B.build(res=res, mp=mp)
        assert out['contests']['c148']['note'] is None, 'failing (unofficial) is not yet failed'
        (res / 'official.json').write_text(json.dumps({'canvasses': {'eastwood-mud': {'canvassed': '2026-11-10'}}}))
        out, _ = B.build(res=res, mp=mp)
        assert out['contests']['c147']['verdict'] == 'failed' and out['contests']['c148']['note'] == 'district_not_confirmed'
        assert out['contests']['c148']['verdict'] == 'passed', 'its own result stands, with the note'
    finally: shutil.rmtree(d)

@test
def an_annexation_gets_one_outcome_from_both_votes():
    d, res = scratch_with([clarity({'1': ('ESD 9 district', FA(400, 600)), '2': ('ESD 9 territory', FA(80, 20))})])
    try:
        mp = one_map(c206=M('1', canvasser='esd-9', who='district', pair='c208'), c208=M('2', canvasser='esd-9', who='area', pair='c206'))
        (res / 'official.json').write_text(json.dumps({'canvasses': {'esd-9': {'canvassed': '2026-11-10'}}}))
        out, _ = B.build(res=res, mp=mp)
        assert [out['contests'][c]['note'] for c in ('c206', 'c208')] == ['annex_district_rejected'] * 2, out['contests']['c206']['note']
        assert (out['contests']['c206']['who'], out['contests']['c208']['who']) == ('district', 'area')
    finally: shutil.rmtree(d)

@test
def an_outcome_one_total_cant_show_waits_for_the_canvass():
    d, res = scratch_with([clarity({'1': ('ESD 4 annexation', FA(900, 100))})])
    try:
        mp = one_map(c205=M('1', canvasser='esd-4', outcome_from_canvass=True))
        e = B.build(res=res, mp=mp)[0]['contests']['c205']
        assert (e['state'], e['verdict']) == ('unofficial', 'none'), '90% for, and still no call: two majorities, one total'
        (res / 'official.json').write_text(json.dumps({'canvasses': {'esd-4': {'canvassed': '2026-11-12'}}}))
        try: B.build(res=res, mp=mp); raise AssertionError('canvassed without its outcome entered')
        except B.Problem as x: assert 'outcomes' in str(x), x
        (res / 'official.json').write_text(json.dumps({'canvasses': {'esd-4': {'canvassed': '2026-11-12'}}, 'outcomes': {'c205': 'failed'}}))
        assert B.build(res=res, mp=mp)[0]['contests']['c205']['verdict'] == 'failed', "the canvass's outcome, not the total's"
    finally: shutil.rmtree(d)

@test
def a_generic_write_in_line_is_left_out():
    d, res = scratch_with([clarity({'1': ('Prop', [('FOR', 600), ('AGAINST', 400), ('Write-in', 7)])})])
    try:
        e = B.build(res=res, mp=one_map(c148=M('1')))[0]['contests']['c148']
        assert [x[:2] for x in e['choices']] == [['FOR', 600], ['AGAINST', 400]] and e['choices'][0][2] == 60.0, e['choices']
    finally: shutil.rmtree(d)

@test
def a_race_decided_in_travis_alone_has_no_travis_breakdown():
    d, res = scratch_with([clarity({'9': ('U.S. Senator', [('James Talarico', 10), ('Ken Paxton', 9), ('Ted Brown', 1)])})])
    try:
        data = fx('sos-53815-travis.json'); r = P.parse_sos(data)
        raw = B.raw_dir(res, 'sos', r['posted'], data); raw.mkdir(parents=True); (raw / 'election.json').write_bytes(data)
        mp = copy.deepcopy(MAP); del mp['contests']['c071']; mp['contests']['c001']['keys']['travis'] = '9'
        assert B.build(res=res, mp=mp)[0]['contests']['c001']['travis'] == [['Ken Paxton', 9, 45.0], ['James Talarico', 10, 50.0], ['Ted Brown', 1, 5.0]]   # ballot order, not the file's
        mp['contests']['c001']['travis_only'] = True
        assert B.build(res=res, mp=mp)[0]['contests']['c001']['travis'] is None
    finally: shutil.rmtree(d)


# ---------------------------------------------------------------- 4. the fetcher, with a stand-in network
def net(pages):
    asked = []
    def fetch(url):
        asked.append(url)
        if url not in pages: raise OSError(f'{url}: HTTP 404')
        return pages[url]
    return fetch, asked

META = {'sos_election': '53815', 'sos_time_zone': 'America/Chicago',
        'fetch': {'williamson': 'https://wc.example/results', 'hays': ['https://hays.example/Cumulative%20Results%20Unofficial.pdf']}}

@test
def the_fetcher_files_what_it_gets_and_skips_what_fails():
    d = pathlib.Path(tempfile.mkdtemp())
    try:
        sos = f'{FR.SOS}/election/53815'
        fetch, asked = net({sos: fx('sos-53815-travis.json'), 'https://wc.example/results': fx('williamson-2025-11.html')})
        out = FR.fetch_all(META, res=d, fetch=fetch)
        assert [(s, bool(p), bool(e)) for s, p, e in out] == [('sos', True, False), ('williamson', True, False), ('hays', False, True)], out
        assert not any('electionReports' in u for u in asked), 'no canvass report until the feed lists one'
        out = FR.fetch_all(META, res=d, fetch=fetch)
        assert [p for _, p, _ in out] == [None, None, None], 'nothing new: nothing written'
        # once the feed lists the Official Canvass Report, it's fetched (from its {"upload": base64} wrapper) and filed
        m = dict(META, sos_election='58314')
        pdf = json.dumps({'upload': __import__('base64').b64encode(fx('sos-58314-canvass.pdf')).decode()}).encode()
        fetch, asked = net({f'{FR.SOS}/election/58314': fx('sos-58314.json'), f'{FR.SOS}/electionReports/58314/OfficialCanvassReport/pdf': pdf})
        out = dict((s, p) for s, p, _ in FR.fetch_all(m, res=d, fetch=fetch))
        assert out['sos_canvass'] and out['sos_canvass'].name == 'official-canvass.pdf', out
        # a page that doesn't add up is never filed
        bad = fx('williamson-2025-11.html').replace(b'>2,498<', b'>2,499<')
        fetch, _ = net({sos: fx('sos-53815-travis.json'), 'https://wc.example/results': bad})
        out = FR.fetch_all(META, res=d, fetch=fetch)
        assert out[1][0] == 'williamson' and out[1][1] is None and 'disagree' in out[1][2], out
        # a file that breaks its parser any other way (an HTML not-found page served as Hays's PDF; broken JSON from the
        # state): that source's error, and the others still filed (#137)
        d2 = pathlib.Path(tempfile.mkdtemp())
        try:
            fetch, _ = net({sos: b'{"not json', 'https://wc.example/results': fx('williamson-2025-11.html'),
                            META['fetch']['hays'][0]: b'<html><body>Not Found</body></html>'})
            out = FR.fetch_all(META, res=d2, fetch=fetch)
            assert [(s, bool(p), bool(e)) for s, p, e in out] == [('sos', False, True), ('williamson', True, False), ('hays', False, True)], out
        finally: shutil.rmtree(d2)
    finally: shutil.rmtree(d)


# ---------------------------------------------------------------- 5. the map
def real_map(): return json.loads((ROOT / 'source/results_map.json').read_text(encoding='utf-8'))

@test
def the_map_is_what_its_tables_write_and_covers_every_contest():
    import subprocess, check_results
    r = subprocess.run([sys.executable, str(ROOT / 'source/build_results_map.py'), '--check'], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    mp, key = real_map(), check_results.answer_key()
    assert set(mp['contests']) == set(key), set(key) ^ set(mp['contests'])
    for cid, m in mp['contests'].items():
        cv = mp['canvassers'].get(m['canvasser'])
        assert cv and cv['label'].startswith('the ') and cv['kind'] in ('local', 'state', 'legislature'), cid
        if m['source'] == 'counties':
            assert m['electorate'] and set(m['keys']) == set(m['electorate']) and all(c in P.LABELS for c in m['electorate']), cid
            assert cv['kind'] == 'local', (cid, 'a county-counted contest is canvassed locally')
        assert m['majority'] in (True, False, 'unsure') and m.get('needs') in (None, 'two_thirds', 'unsure'), cid
        if m.get('needs'): assert key[cid]['type'] == 'measure', cid
        if m.get('depends_on'): assert key[m['depends_on']]['type'] == 'measure' and key[m['depends_on']]['entity'] == key[cid]['entity'], cid
        if m.get('pair'): assert mp['contests'][m['pair']]['pair'] == cid and {m['who'], mp['contests'][m['pair']]['who']} == {'district', 'area'}, cid
        if m.get('write_ins'): assert 'Write-in' in key[cid]['choices'], (cid, 'a declared write-in where the ballot has no write-in line')
    assert mp['contests']['c006']['canvasser'] == mp['contests']['c007']['canvasser'] == 'legislature'

@test
def every_sos_contest_reads_from_the_live_feed_through_a_full_build():
    d = pathlib.Path(tempfile.mkdtemp())
    try:
        res = d / 'results'; data = fx('sos-53815-travis.json'); r = P.parse_sos(data)
        raw = B.raw_dir(res, 'sos', r['posted'], data); raw.mkdir(parents=True); (raw / 'election.json').write_bytes(data)
        out, ch = B.build(res=res, mp=real_map())
        sos = [cid for cid, m in real_map()['contests'].items() if m['source'] == 'sos']
        assert sorted(out['contests']) == sorted(sos) and len(sos) == 42, sorted(set(sos) ^ set(out['contests']))
        import check_results; key = check_results.answer_key()
        for cid, e in out['contests'].items():   # no votes yet: counting, except a one-candidate race, unopposed from the start
            one = len(check_results.pick_names(key[cid])) == 1 and not any(x[3] for x in e['choices'])
            assert (e['state'], e['verdict']) == (('unofficial', 'unopposed') if one else ('counting', 'none')), (cid, e['state'], e['verdict'])
        assert sum(e['verdict'] == 'unopposed' for e in out['contests'].values()) == 11
        assert sum(x[3] for e in out['contests'].values() for x in e['choices']) == 11, 'the 11 declared write-ins'
        assert out['contests']['c006']['canvass'] == {'kind': 'legislature', 'by': None, 'on': None, 'done': None}
        assert check_results_ok(out)
    finally: shutil.rmtree(d)


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
