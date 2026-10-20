"""The results back end, without a browser (docs/plans/2026-10-20-results.md, Tasks 2-4). About a second.

    python3 tests/test_results.py

1. The verdict rules (source/results_rules.py), one at a time, at and around every threshold the plan sets.
2. The parsers (source/results_parse.py) on real files, trimmed (tests/fixtures/results): the Nov 2025 City of Austin
   Prop Q across three counties equals the City's official canvass; the May 2026 runoff's SOS feed equals its Official
   Canvass Report; and each parser refuses a file that doesn't add up.
"""
import pathlib, sys, traceback

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'source'))
import results_rules as R, results_parse as P
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
