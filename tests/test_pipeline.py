"""The answer key against the ballot itself (cold audit, Oct 17: #1, #2, #3, #5). No browser; about 20 seconds.

    python3 tests/test_pipeline.py

1. source/ballot/build_answer_key.py reproduces the committed source/answer_key.json byte for byte, so no correction
   lives only in the JSON (a rerun would silently undo it).
2. Every candidate contest lists its choices in the order the ballot PDF prints them, top to bottom.
3. Every measure's text is exactly the ballot's English text (no Spanish caption carried along).
4. Every party label on the ballot (104, legend aside) is on the same name in the key, and the key has no others.
5. The ballot's FOR / AGAINST pairs number exactly the key's measures.
6. Every English line on the ballot is in the key (a measure text or a choice) or is a page number, "Vote for" line or
   notice; each measure's text is all the upright text between its title and its Spanish, whatever the font weight.
7. Release bookkeeping (source/check_release.py): VERSION, CHANGELOG.md's newest release and version.json agree, and
   the check refuses each kind of drift.
"""
import json, os, pathlib, re, subprocess, sys, tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'source/ballot')); sys.path.insert(0, str(ROOT / 'source'))
import pdf_lines, check_release

KEY = json.loads((ROOT / 'source/answer_key.json').read_text(encoding='utf-8'))
L = pdf_lines.lines()
PARTY = re.compile(r'\s*\(\s*(R\s*E\s*P|D\s*E\s*M|L\s*I\s*B|G\s*R\s*N)\s*\)\s*$')
name = lambda s: PARTY.sub('', s).strip()
TESTS = []
def test(fn): TESTS.append(fn); return fn


@test
def key_is_rebuilt_exactly_by_the_script():
    with tempfile.TemporaryDirectory() as d:
        out = pathlib.Path(d) / 'key.json'
        r = subprocess.run([sys.executable, str(ROOT / 'source/ballot/build_answer_key.py'), '--out', str(out)], capture_output=True, text=True)
        assert r.returncode == 0, r.stderr[-800:]
        assert out.read_bytes() == (ROOT / 'source/answer_key.json').read_bytes(), 'the committed key is not what build_answer_key.py makes: put the change in the script'


@test
def every_choice_list_is_in_ballot_order():
    texts = [name(l['text']) for l in L]
    at = {}
    for i, t in enumerate(texts): at.setdefault(t, []).append(i)
    wrong, lost = [], []
    for c in KEY['contests']:
        if c['type'] != 'candidate': continue
        names = [name(x) for x in c['choices'] if x != 'Write-in']
        if any(n not in at for n in names): lost.append((c['id'], [n for n in names if n not in at])); continue
        if len(names) < 2: continue
        span, found = 4 * len(names) + 6, None   # the smallest stretch of ballot holding every name, read top to bottom
        for p in sorted({i for n in names for i in at[n]}):
            sel = {n: next((i for i in at[n] if p <= i <= p + span), None) for n in names}
            if None not in sel.values(): found = sel; break
        if not found: lost.append((c['id'], 'not together on the ballot')); continue
        order = sorted(names, key=lambda n: found[n])
        if order != names: wrong.append((c['id'], c['title'], order))
    assert not lost, ('names not found on the ballot', lost)
    assert not wrong, ('choices out of ballot order', wrong)


@test
def contests_within_a_level_are_in_ballot_order():
    # Round-2 audit #26 (#123): the page shows each level's contests in the key's order, and "County Judge" came after
    # "Judge, County Court at Law No. 1", which the ballot prints after it. Every candidate contest whose title is a line
    # of the ballot must follow the ballot within its level. US Rep, State Senator and State Rep districts are left out:
    # no voter gets two of one (build_rules.py stops otherwise), and the ballot doesn't list them by number.
    first = {}
    for i, l in enumerate(L): first.setdefault(l['text'].strip(), i)
    one_each = re.compile(r'^(United States Representative|State Senator|State Representative), District')
    at, levels = {}, {}
    for c in KEY['contests']:
        t = re.sub(r'\s*\(vote for up to \d\)$', '', c['title'])
        if c['type'] != 'candidate' or one_each.match(t) or t not in first: continue
        at[c['id']] = first[t]; levels.setdefault(c['level'], []).append(c['id'])
    assert len(at) >= 30 and 'c044' in at and 'c042' in at, (len(at), 'too few contest titles found on the ballot')
    wrong = {lv: ids for lv, ids in levels.items() if ids != sorted(ids, key=at.get)}
    assert not wrong, ('contests out of ballot order within their level', {lv: [(i, at[i]) for i in ids] for lv, ids in wrong.items()})

@test
def every_measure_text_is_the_ballots_english():
    pdf = pdf_lines.measures(L)
    key = [c for c in KEY['contests'] if c['type'] == 'measure']
    assert len(pdf) == len(key) == 93, (len(pdf), len(key))
    bad = [(c['id'], c['text'][-50:], t[-50:]) for (_, t), c in zip(pdf, key) if pdf_lines.norm(c['text']) != t]
    assert not bad, ('measure text differs from the ballot', bad[:5], len(bad))
    spanish = re.compile(r'(Núm\.|Condado de|Distrito |Ciudad de|Propuesta|Proposición)')
    assert not [c['id'] for c in key if spanish.search(c['text'][-60:])], 'a measure text ends in Spanish'


# English lines on the ballot that are neither a measure's text nor a choice: page numbers, "Vote for …" lines, and the
# notices of the Coupland and Manor ISD trustees elected unopposed (pages 7 and 8).
NOT_CONTENT = re.compile(r'^(Page \d+|of 18|Vote for .*|or five)$')
UNOPPOSED = {'Coupland Independent School', 'District School Board Trustee,', 'Special Election: Rhonda Suzanne', 'Dunlop Coupland Independent', 'School District School Board',
             'Trustees, General Election: Crystal', 'Ward, Michael Roepke', 'Manor ISD Board of Trustees,', 'Place 1: Stephanie Rodriguez',
             'Place 2: LaKesha Small', 'Place 3: Ana Cortez', 'Place 4: Fabian Martinez'}


@test
def every_english_line_on_the_ballot_is_in_the_key():
    # Independent of pdf_lines.measures() (wave 1 audit: the test above compares the key with the function that made
    # it): each upright, non-bold line of the ballot is in some measure's text, is a choice, or is listed above; and the
    # line after each measure's text starts its Spanish translation (all italic), so no English was cut off or added.
    texts = [pdf_lines.norm(c['text']) for c in KEY['contests'] if c['type'] == 'measure']
    choices = {name(x) for c in KEY['contests'] for x in c.get('choices', [])}
    titles = [i for i, l in enumerate(L) if pdf_lines.english(l) and pdf_lines.bold(l) and re.search(r'Proposition\s+[A-Z0-9]+$', l['text'])]
    assert len(titles) == 93, len(titles)
    inside = set()   # the English of each measure's text: checked whole against the key below, line by line
    for i in titles:
        j = i + 1
        while all(not it for _, it, _ in L[j]['words']): inside.add(j); j += 1
    # Outside a measure's text, a line is a choice, a notice, or an unopposed line: whole lines, never a piece of some
    # measure's text (a dropped candidate's name inside a measure passed before: round 2 #20, #118)
    left = [(l['page'], l['col'], l['text']) for k, l in enumerate(L) if k not in inside and pdf_lines.english(l) and not pdf_lines.bold(l)
            and not (name(pdf_lines.norm(l['text'])) in choices or NOT_CONTENT.match(l['text']) or l['text'] in UNOPPOSED)]
    assert not left, ('English on the ballot that the key does not carry', left[:8], len(left))
    # each measure is paired with its own title: its letter or number, and the entity printed above it (#118)
    measures = [c for c in KEY['contests'] if c['type'] == 'measure']
    wrong = []
    for i, c in zip(titles, measures):
        j, block = i, [L[i]['text']]                      # the whole bold title, wrapped lines and all
        while pdf_lines.english(L[j - 1]) and pdf_lines.bold(L[j - 1]): j -= 1; block.insert(0, L[j]['text'])
        isd = lambda t: pdf_lines.norm(t).replace('Independent School District', 'ISD')   # either form, on the ballot or in the key
        if isd(' '.join(block)) != isd(re.sub(r' \([^)]*\)$', '', c['title'])): wrong.append((c['id'], c['title'], ' '.join(block)))   # less the key's own note
    assert not wrong, ('a measure paired with another title', wrong[:5], len(wrong))
    for i, t in zip(titles, texts):
        j, words = i + 1, []
        while all(not it for _, it, _ in L[j]['words']): words.append(L[j]['text']); j += 1
        assert all(it for _, it, _ in L[j]['words']), ('a measure text runs into a line that is partly Spanish', L[j]['text'])
        assert pdf_lines.norm(' '.join(words)) == t, ('measure text differs from the English between its title and its Spanish', L[i]['text'], t[-60:])


@test
def write_ins_are_where_the_ballot_has_them():
    """Round 2 #20 (#118): each "Write-in / Voto Escrito" line of the ballot follows its contest's candidates; the
    contests it follows are exactly the key's contests with a write-in (all five were checked by hand before)."""
    on_ballot = set()
    for i, l in enumerate(L):
        if not l['text'].startswith('Write-in'): continue
        names, j = set(), i - 1
        while j >= 0 and PARTY.search(L[j]['text']) or (j >= 0 and any(name(L[j]['text']) == name(x) for c in KEY['contests'] for x in c.get('choices', []))):
            names.add(name(L[j]['text'])); j -= 1
        fits = [c['id'] for c in KEY['contests'] if c['type'] == 'candidate' and names and names == {name(x) for x in c['choices'] if x != 'Write-in'}]
        assert len(fits) == 1, ('a write-in line whose contest is unclear', L[i]['page'], sorted(names), fits)
        on_ballot.add(fits[0])
    in_key = {c['id'] for c in KEY['contests'] if 'Write-in' in c.get('choices', [])}
    assert on_ballot == in_key, ('write-ins differ from the ballot', sorted(on_ballot ^ in_key))

@test
def party_labels_match_the_ballot():
    on_ballot = {}
    for l in L:
        if PARTY.search(l['text']) and '=' not in l['text']:      # the legend ("Republican = (REP) …") aside
            on_ballot[name(l['text'])] = re.sub(r'\s', '', PARTY.search(l['text']).group(1))
    in_key = {name(x): re.sub(r'\s', '', PARTY.search(x).group(1)) for c in KEY['contests'] for x in c.get('choices', []) if PARTY.search(x)}
    assert len(on_ballot) == 104, len(on_ballot)
    assert in_key == on_ballot, ({k: (in_key.get(k), on_ballot.get(k)) for k in set(in_key) | set(on_ballot) if in_key.get(k) != on_ballot.get(k)})


@test
def for_and_against_pairs_match_the_measures():
    fors = sum(1 for l in L if l['text'].startswith('FOR / A FAVOR'))
    againsts = sum(1 for l in L if l['text'].startswith('AGAINST / EN CONTRA'))
    measures = sum(1 for c in KEY['contests'] if c['type'] == 'measure')
    assert fors == againsts == measures, (fors, againsts, measures)



@test
def release_bookkeeping_is_consistent():
    assert check_release.problems() == [], check_release.problems()


@test
def a_change_to_the_published_site_needs_a_new_version():
    # Round-2 audit #19 (#117): since 1.1.6 a page left open learns of a newer release only from a higher VERSION, so a
    # push that changes what the site publishes without a bump would never reach phones already in use (and
    # version.json would name a release that isn't what's live). source/check_bumped.py refuses it once v<VERSION> is
    # tagged; a docs or tests change, or a bumped VERSION (not tagged yet), passes.
    import shutil
    with tempfile.TemporaryDirectory() as d:
        d = pathlib.Path(d) / 'r'
        shutil.copytree(ROOT, d, ignore=shutil.ignore_patterns('.git', '__pycache__', '*.pdf', '.mutate-lock', '*.mutate-tmp', '_site'))
        git = lambda *a: subprocess.run(['git', '-c', 'user.name=t', '-c', 'user.email=t@t', '-c', 'commit.gpgsign=false', *a], cwd=str(d), capture_output=True, text=True, check=True)
        run = lambda: subprocess.run([sys.executable, 'source/check_bumped.py'], cwd=str(d), capture_output=True, text=True)
        git('init', '-q'); git('add', '-A'); git('commit', '-qm', 'base')
        r = run(); assert r.returncode != 0 and 'tags' in r.stderr, ('no release tags at all (a clone without them) passed', r.stdout, r.stderr)
        git('tag', 'v0.0.1')
        r = run(); assert r.returncode == 0, ('no tag yet: a new release', r.stdout, r.stderr)
        v = (d / 'VERSION').read_text().strip(); git('tag', 'v' + v)
        r = run(); assert r.returncode == 0, ('the tagged release itself', r.stdout, r.stderr)
        (d / 'README.md').write_text((d / 'README.md').read_text() + '\nmore\n'); git('commit', '-qam', 'docs')
        r = run(); assert r.returncode == 0, ('a docs change', r.stdout, r.stderr)
        (d / 'index.html').write_text((d / 'index.html').read_text(encoding='utf-8').replace('<title>', '<title> ', 1), encoding='utf-8'); git('commit', '-qam', 'page')
        r = run(); assert r.returncode != 0 and 'index.html' in r.stdout + r.stderr and 'VERSION' in r.stdout + r.stderr, ('a page change without a bump passed', r.stdout, r.stderr)
        (d / 'VERSION').write_text('99.0.0\n'); git('commit', '-qam', 'bump')
        r = run(); assert r.returncode == 0, ('a bumped VERSION, not tagged yet', r.stdout, r.stderr)
        git('tag', 'v99.0.0'); git('revert', '--no-edit', 'HEAD')   # Pass 1: a bare revert of a release puts the old VERSION back
        r = run(); assert r.returncode != 0 and 'lower' in r.stderr, ('a VERSION lower than a tagged release passed', r.stdout, r.stderr)
        shallow = d.parent / 'shallow'
        subprocess.run(['git', 'clone', '-q', '--depth', '1', 'file://' + str(d), str(shallow)], check=True, capture_output=True)
        r = subprocess.run([sys.executable, 'source/check_bumped.py'], cwd=str(shallow), capture_output=True, text=True)
        assert r.returncode != 0 and 'history' in r.stderr, ('a shallow clone passed', r.stdout, r.stderr)

@test
def release_check_refuses_drift():
    good = ('# Changelog\n\n## [Unreleased]\n\n_Nothing yet._\n\n## [1.1.0] — 2026-10-18\n\n- b\n\n## [1.0.0] — 2026-10-17\n\n- a\n')
    cases = {
        'fine': ('1.1.0', good, {'version': '1.1.0'}, False),
        'VERSION bumped, no CHANGELOG section': ('1.2.0', good, {'version': '1.2.0'}, True),
        'CHANGELOG section, VERSION not bumped': ('1.0.0', good, {'version': '1.0.0'}, True),
        'not semver': ('1.1', good, {'version': '1.1'}, True),
        'no Unreleased section': ('1.1.0', good.replace('## [Unreleased]\n\n_Nothing yet._\n\n', ''), {'version': '1.1.0'}, True),
        'Unreleased below a release': ('1.1.0', good.replace('## [Unreleased]\n\n_Nothing yet._\n\n', '') + '\n## [Unreleased]\n', {'version': '1.1.0'}, True),
        'release without a date': ('1.1.0', good.replace('[1.0.0] — 2026-10-17', '[1.0.0]'), {'version': '1.1.0'}, True),
        'out of order': ('1.1.0', good.replace('[1.0.0]', '[1.2.0]'), {'version': '1.1.0'}, True),
        'a version twice': ('1.1.0', good.replace('[1.0.0]', '[1.1.0]'), {'version': '1.1.0'}, True),
        'version.json stale': ('1.1.0', good, {'version': '1.0.0'}, True),
        'version.json missing': ('1.1.0', good, None, True),
    }
    wrong = []
    for name, (v, log, js, refused) in cases.items():
        with tempfile.TemporaryDirectory() as d:
            d = pathlib.Path(d); (d / 'VERSION').write_text(v + '\n'); (d / 'CHANGELOG.md').write_text(log, encoding='utf-8')
            if js is not None: (d / 'version.json').write_text(json.dumps(js))
            if bool(check_release.problems(d)) != refused: wrong.append((name, check_release.problems(d)))
    assert not wrong, wrong
    assert check_release.key('1.2.10') > check_release.key('1.2.9') > check_release.key('1.2.9-rc1')

@test
def build_check_catches_drift_and_broken_markers():
    # #81: `build_site.py --check` (what CI runs) rebuilds in memory, writes nothing, and fails when a committed output
    # differs from the build (a hand edit, a left-behind mutant) or when a rollback build's markers don't pair up.
    import shutil
    run = lambda root: subprocess.run([sys.executable, str(root / 'source/build_site.py'), '--check'], capture_output=True, text=True, cwd=str(root))
    r = run(ROOT); assert r.returncode == 0, ('the committed build is out of date', r.stdout[-600:], r.stderr[-600:])
    with tempfile.TemporaryDirectory() as d:
        d = pathlib.Path(d) / 'b'
        shutil.copytree(ROOT, d, ignore=shutil.ignore_patterns('.git', 'tests', '__pycache__', '*.pdf', '.mutate-lock', '*.mutate-tmp'))
        files = lambda: {p: p.read_bytes() for p in d.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
        before = files()
        assert run(d).returncode == 0
        assert files() == before, '--check wrote something'
        page = d / 'index.html'; page.write_text(page.read_text(encoding='utf-8').replace('<title>', '<title> ', 1), encoding='utf-8')
        r = run(d); assert r.returncode != 0 and 'index.html' in r.stdout + r.stderr, ('a changed index.html passed', r.stdout[-400:])
        page.write_bytes(before[page])
        tpl = d / 'source/template-travis.html'; s = tpl.read_text(encoding='utf-8')
        tpl.write_text(s.replace('<!--/DESK-->', '', 1), encoding='utf-8')
        r = run(d); assert r.returncode != 0 and 'DESK' in r.stdout + r.stderr, ('an unpaired marker passed', r.stdout[-400:])

@test
def rules_are_rebuilt_and_new_districts_stay_small():
    # Round-2 audit #1: build_rules.py reproduces the committed rules.json, and stops when a district holding its
    # confirmation election (so, just created) reaches more than 300 addresses: MUD No. 41 routed to M41 reached 1,217.
    import shutil
    with tempfile.TemporaryDirectory() as d:
        d = pathlib.Path(d) / 'source'
        shutil.copytree(ROOT / 'source', d, ignore=shutil.ignore_patterns('__pycache__', '*.pdf', '.mutate-lock', '*.mutate-tmp'))
        run = lambda: subprocess.run([sys.executable, 'build_rules.py'], capture_output=True, text=True, cwd=str(d))
        r = run(); assert r.returncode == 0, ('build_rules.py stopped', r.stdout[-600:], r.stderr[-600:])
        for f in ('rules.json', 'tlc_precincts.json'):
            assert (d / f).read_bytes() == (ROOT / 'source' / f).read_bytes(), f + ' is not what build_rules.py writes'
        src = d / 'build_rules.py'; s = src.read_text(encoding='utf-8')
        unrouted = 'return None, "unrouted", "No confirmed county code for this district yet; asking the Tax Office."'
        m41 = s.replace(unrouted, 'return [{"MUD": ["M41"]}, {"Temp": ["M41"]}], "medium", "M41"', 1)
        m41 = m41.replace('\n# A district holding its confirmation election', '\nUNREACHED_OK.pop("Travis County MUD No. 41")\n# A district holding its confirmation election', 1)
        assert m41.count('M41') >= 3 and 'UNREACHED_OK.pop' in m41, 'the test no longer finds what it changes'
        src.write_text(m41, encoding='utf-8'); r = run()
        assert r.returncode != 0 and "'Travis County MUD No. 41': 1217" in r.stdout + r.stderr, ('MUD No. 41 on M41 passed the build', r.stdout[-600:], r.stderr[-400:])
        src.write_text(m41.replace('CONFIRMATION_OK = {}', 'CONFIRMATION_OK = {"Travis County MUD No. 41": "test"}', 1), encoding='utf-8')
        assert run().returncode == 0, 'an explained new district still stops the build'

@test
def search_engines_may_list_the_page():
    # Round-2 audit #6 (Lane, Oct 18): from the public launch, search engines may list ballotta.org. The old preview
    # address (next/), now a page that sends people on, stays unlisted.
    robots = re.compile(r'<meta\s+name="robots"[^>]*noindex', re.I)
    assert not robots.search((ROOT / 'index.html').read_text(encoding='utf-8')), 'index.html still asks search engines not to list it'
    assert not robots.search((ROOT / 'source/template-travis.html').read_text(encoding='utf-8')), 'the template still carries noindex'
    assert robots.search((ROOT / 'next/index.html').read_text(encoding='utf-8')), 'the moved preview page lost its noindex'

@test
def site_folder_holds_only_the_site():
    # #83: Pages publishes the folder `build_site.py --site` writes: every built file and the files the pages point at,
    # nothing else (no tests/, docs/, source/), and nothing at all when the build check fails.
    import shutil
    sys.path.insert(0, str(ROOT / 'source')); import build_site
    want = set(build_site.site_files())
    assert {'index.html', 'census.html', 'sw.js', 'version.json', 'fonts/OFL.txt', 'umami.js'} <= want, want
    assert not [f for f in want if f.split('/')[0] in ('source', 'tests', 'docs', '.github') or f.endswith(('.md', '.py', '.pdf'))], want
    with tempfile.TemporaryDirectory() as d:
        d = pathlib.Path(d); out = d / 'site'
        r = subprocess.run([sys.executable, str(ROOT / 'source/build_site.py'), '--site', str(out)], capture_output=True, text=True)
        assert r.returncode == 0, r.stdout[-400:] + r.stderr[-400:]
        got = {str(p.relative_to(out)) for p in out.rglob('*') if p.is_file()}
        assert got == want, (got ^ want)
        assert all((out / f).read_bytes() == (ROOT / f).read_bytes() for f in got)
        r = subprocess.run([sys.executable, str(ROOT / 'source/build_site.py'), '--site', str(out)], capture_output=True, text=True)
        assert r.returncode != 0 and 'not empty' in r.stdout + r.stderr, ('wrote into a folder that already held files', r.stderr[-300:])
        repo = d / 'repo'; shutil.copytree(ROOT, repo, ignore=shutil.ignore_patterns('.git', 'tests', '__pycache__', '*.pdf', '.mutate-lock', '*.mutate-tmp'))
        (repo / 'index.html').write_text((repo / 'index.html').read_text(encoding='utf-8') + ' ', encoding='utf-8')
        r = subprocess.run([sys.executable, str(repo / 'source/build_site.py'), '--site', str(d / 'bad')], capture_output=True, text=True)
        assert r.returncode != 0 and not (d / 'bad').exists() and 'index.html' in r.stdout + r.stderr, ('a drifted build was published', r.stdout[-300:], r.stderr[-300:])
        (repo / 'index.html').write_bytes((ROOT / 'index.html').read_bytes()); (repo / 'og.png').unlink()
        r = subprocess.run([sys.executable, str(repo / 'source/build_site.py'), '--site', str(d / 'bad2')], capture_output=True, text=True)
        assert r.returncode != 0 and 'og.png is published but missing' in r.stdout + r.stderr and not (d / 'bad2').exists(), ('a missing file was not caught by the check', r.stderr[-300:])
        (repo / 'og.png').write_bytes((ROOT / 'og.png').read_bytes())
        run = lambda *a: subprocess.run([sys.executable, str(repo / 'source/build_site.py'), *a], capture_output=True, text=True, cwd=str(repo))
        cen = repo / 'census.html'; cen.write_bytes(cen.read_bytes().replace(b'\n', b'\r\n'))       # same text, other bytes
        r = run('--check'); assert r.returncode != 0 and 'census.html' in r.stdout, ('a CRLF copy passed the check', r.stdout[-300:])
        cen.write_bytes((ROOT / 'census.html').read_bytes())
        (repo / '.mutate-lock').write_text('1')                                                      # #79: no build while a mutation run holds the lock
        for args in ((), ('--site', str(d / 'bad3'))):
            r = run(*args); assert r.returncode != 0 and '.mutate-lock' in r.stderr and not (d / 'bad3').exists(), (args, r.stderr[-300:])
        (repo / '.mutate-lock').unlink()
        bs = repo / 'source/build_site.py'; src = bs.read_text(encoding='utf-8'); assert src.count('\nPHONE_LIVE = True\n') == 1
        bs.write_text(src.replace('\nPHONE_LIVE = True\n', '\nPHONE_LIVE = False\n', 1), encoding='utf-8')
        r = run(); assert r.returncode == 0, r.stderr[-300:]
        (repo / 'next/index.html').write_text(build_site.moved_page(), encoding='utf-8')              # next/ as it is when nothing is in preview (Oct 19)
        r = run('--site', str(d / 'stale'))                                                           # the rollback without --preview: next/ is still the hand-off page
        assert r.returncode != 0 and 'next/index.html' in r.stderr and not (d / 'stale').exists(), ('a rollback published the old next/', r.stderr[-300:])
        for args in (('--preview',), ('--site', str(d / 'rollback'))):                                # a phone rollback, as the README says
            r = run(*args); assert r.returncode == 0, (args, r.stdout[-300:], r.stderr[-300:])
        got = {str(x.relative_to(d / 'rollback')) for x in (d / 'rollback').rglob('*') if x.is_file()}
        assert {'next/index.html', 'next/sw.js', 'next/manifest.webmanifest', 'manifest.webmanifest', 'sw.js', 'index.html'} <= got, sorted(got)


@test
def every_early_site_is_spelled_as_on_election_day():
    # #85: all 45 early voting sites are Election Day sites too, but three were spelled differently ("Confrence Room",
    # "1201 E Runberg Ln", "5800 Mcneil Dr"). Name, room, street and city now match their Election Day row exactly.
    d = json.loads((ROOT / 'source/vote_sites.json').read_text(encoding='utf-8'))
    eday = {tuple(r[:4]) for r in d['eday']}
    odd = [r[:4] for r in d['early'] if tuple(r[:4]) not in eday]
    assert len(d['early']) == 45 and not odd, odd
    typos = re.compile(r'Confrence|Runberg|Mcneil')
    assert not [r[:4] for k in ('early', 'eday') for r in d[k] if typos.search(' '.join(map(str, r[:4])))]


@test
def every_browser_context_gets_the_county_stub():
    # #78, Pass 1: a context made outside new_page() (a tablet, JavaScript off) skipped route_county(), so with
    # BALLOTTA_STUB_COUNTY=1 its lookups still went to the live county. Every context the browser suite makes must route
    # it, on that same context, in code (Pass 2: comments don't count).
    import io, tokenize
    raw = (ROOT / 'tests/test_site.py').read_text(encoding='utf-8')
    lines = raw.splitlines()
    for t in tokenize.generate_tokens(io.StringIO(raw).readline):          # blank every comment, keep the line numbers
        if t.type == tokenize.COMMENT:
            r, c = t.start; lines[r - 1] = lines[r - 1][:c]
    code = '\n'.join(lines)
    np = code[code.index('def new_page('):code.index('\n    return ctx, pg', code.index('def new_page('))]
    assert re.search(r'^    ctx = browser\.new_' + r'context\(', np, re.M) and re.search(r'^    route_county\(ctx, county\)', np, re.M), 'new_page() no longer routes the county'
    made = [l.strip() for l in lines if '.new_' + 'context(' in l and not l.strip().startswith('ctx = browser.new_' + 'context(viewport=size or')]
    bare = [l for l in made if not re.match(r'(\w+) = \w+\.new_' + r'context\(.*;\s*route_county\(\1\)', l)]
    assert len(made) >= 4 and not bare, bare


@test
def stroked_letters_cover_unicode():
    # #93, Pass 1–2: letters with a stroke, hook or bar ("GØP", "Đemocrat", "GƟP") got a reserved share name past the
    # page's check. The page's STROKED table is every Latin letter Unicode names "... LETTER X WITH ...", "... BARRED X"
    # or "... X BAR" (small capitals, blackletter) that normalizing doesn't already strip. This regenerates it with this Python's Unicode data (all
    # of it below U+A7C0, where it is settled; what the page has above must be right) and checks that every letter the
    # page looks up, which is the lower case (the page lower-cases first), is there.
    import unicodedata
    src = (ROOT / 'source/template-travis.html').read_text(encoding='utf-8')
    m = re.search(r"const STROKED = \['([^']*)', '([^']*)'\];", src); assert m, 'no STROKED table'
    page = dict(zip(m.group(1), m.group(2)))                                     # Python strings are code points, like the page's Array.from
    assert len(m.group(1)) == len(m.group(2)) == len(page) > 240, (len(m.group(1)), len(m.group(2)))
    pat = re.compile(r'LATIN (?:SMALL |CAPITAL )?(?:LETTER )?(?:SMALL CAPITAL )?(?:LETTER )?(?:BARRED |BLACKLETTER )?([A-Z])(?: WITH (.*)| BAR)?$')
    def base(ch):
        nm = unicodedata.name(ch, ''); k = pat.match(nm)
        if not k or not (' WITH ' in nm or 'BARRED' in nm or nm.endswith(' BAR')): return None
        if ''.join(c for c in unicodedata.normalize('NFKD', ch) if not unicodedata.combining(c)).lower() == k.group(1).lower(): return None
        return k.group(1).lower()
    want = {chr(cp): base(chr(cp)) for lo, hi in [(0x80, 0x2B0), (0x1D00, 0x1DC0), (0x1E00, 0x1F00), (0x2C60, 0x2C80), (0xA720, 0xA7C0), (0xAB30, 0xAB70), (0x1DF00, 0x1E000)]
            for cp in range(lo, hi) if base(chr(cp))}
    missing = {c: b for c, b in want.items() if page.get(c) != b}
    wrong = {c: (b, unicodedata.name(c, '?')) for c, b in page.items() if unicodedata.name(c, '') and base(c) != b}
    unseen = [c for c in page if unicodedata.normalize('NFKD', c) == c and c.lower() != c and c.lower() not in page]
    assert not missing and not wrong and not unseen, (missing, wrong, unseen)
    assert all(page.get(c) == b for c, b in zip('ØĐŧƇƥƀɍłɠɗꝑƟɵɄʉᴃᴌᵻᵾꬾ', 'odtcpbrlgdpoouubliuo'))
    assert "return refused(LOOKALIKE) || refused(LOOKALIKE_STROKE) ? '' : n;" in src, 'a name must be checked with both readings (ʋ: u and v)'


@test
def guide_sites_are_compared_whole():
    # #85: parse_lwv.py reports guide sites it couldn't credit to a ballot candidate. It compared the first 14 characters,
    # so one credited Facebook page claimed every other; a URL cut short at a line wrap must still match its site.
    src = (ROOT / 'source/parse_lwv.py').read_text(encoding='utf-8')
    ns = {'re': re}; exec(src[src.index('def site_key'):src.index('credited = ')], ns)
    k, same = ns['site_key'], ns['same_site']
    cases = {('www.facebook.com/alice', 'www.facebook.com/bob'): False, ('facebook.com/alice', 'https://www.facebook.com/bob'): False, ('facebook.com/alice', 'facebook.com'): False,
             ('www.facebook.com/alice', 'https://facebook.com/alice/'): True, ('www.jeffbowenforaustincitycouncil', 'jeffbowenforaustincitycouncil.com'): True,
             ('janeforcouncil.com/about-jane-and-her', 'https://janeforcouncil.com/about-jane-and-her-plan'): True,
             ('jane.com', 'janeforcouncil.com'): False, ('jane', 'janeforcouncil.com'): False, ('Tishflores.com', 'tishflores.com/'): True}
    wrong = [(a, b) for (a, b), want in cases.items() if same(k(a), k(b)) != want or same(k(b), k(a)) != want]
    assert not wrong, wrong


@test
def every_guide_measure_belongs_to_a_contest():
    # #85: the guide's Williamson County measures went unread. parse_lwv.py leaves them out, and build_learn.py stops on
    # any guide measure no contest reads (a Travis entity missing from LWV_ENT would lose its voters the guide's page).
    import shutil
    m = json.loads((ROOT / 'source/data/lwv_measures.json').read_text(encoding='utf-8'))
    assert not [x for x in m if x.split('|')[0] in ('CITY OF GEORGETOWN', 'CITY OF HUTTO', 'CITY OF TAYLOR', 'GEORGETOWN INDEPENDENT SCHOOL DISTRICT')], m
    with tempfile.TemporaryDirectory() as d:
        d = pathlib.Path(d) / 's'; shutil.copytree(ROOT / 'source', d, ignore=shutil.ignore_patterns('*.pdf', '__pycache__', '.mutate-lock', '*.mutate-tmp'))
        run = lambda: subprocess.run([sys.executable, str(d / 'build_learn.py')], capture_output=True, text=True, cwd=str(d))
        r = run(); assert r.returncode == 0, r.stderr[-600:]
        assert (d / 'learn.json').read_bytes() == (ROOT / 'source/learn.json').read_bytes(), 'learn.json is not what build_learn.py makes'
        (d / 'data/lwv_measures.json').write_text(json.dumps(dict(m, **{'CITY OF ROUND ROCK|A': 9})), encoding='utf-8')
        r = run(); assert r.returncode != 0 and 'CITY OF ROUND ROCK|A' in r.stderr, ('an unread guide measure passed', r.stderr[-400:])


@test
def campaign_sites_were_checked_with_todays_rule():
    # Round-2 audit #2: 1.1.3 changed the broken-link rule but the shipped results came from the Oct 14 run, so a site
    # the new rule unlinks stayed linked. The results must carry today's rule and today's list of sites, and every site
    # that never answered must carry curl's exit code; build_learn.py stops otherwise (the same stale()).
    import copy, importlib
    cs = importlib.import_module('check_sites')
    r = json.loads(cs.P.read_text(encoding='utf-8')); stamp = json.loads(cs.STAMP.read_text()) if cs.STAMP.exists() else None
    assert cs.stale(r, stamp) is None, cs.stale(r, stamp)
    assert cs.stale(r, dict(stamp, rule=cs.RULE - 1)), 'results from an older rule passed'
    assert cs.stale(r, None), 'no record passed'
    moved = copy.deepcopy(r); ch = next(k for k, v in moved.items() if v.get('site')); moved[ch]['site'] += '.example'
    assert cs.stale(moved, stamp), 'a site changed after the check passed'
    edited = copy.deepcopy(r); edited[ch]['http'] = '404' if str(edited[ch].get('http')) != '404' else '200'
    assert cs.stale(edited, stamp), 'a result edited by hand after the check passed'
    old = copy.deepcopy(r); old[ch]['http'] = '000'; old[ch].pop('curl', None)                 # as if stamped after these results
    assert cs.stale(old, dict(stamp, sites=cs.digest(old))), 'an unanswered site without curl\'s exit code passed'
    old[ch]['curl'] = 35; assert cs.stale(old, dict(stamp, sites=cs.digest(old))) is None
    del old[ch]['http']; assert cs.stale(old, dict(stamp, sites=cs.digest(old))), 'a site with no result passed'
    import shutil                                                            # and build_learn.py stops on it
    with tempfile.TemporaryDirectory() as d:
        d = pathlib.Path(d) / 's'; shutil.copytree(ROOT / 'source', d, ignore=shutil.ignore_patterns('*.pdf', '__pycache__', '.mutate-lock', '*.mutate-tmp'))
        (d / 'data/sites_checked.json').write_text(json.dumps(dict(stamp, rule=cs.RULE - 1)), encoding='utf-8')
        r = subprocess.run([sys.executable, str(d / 'build_learn.py')], capture_output=True, text=True, cwd=str(d))
        assert r.returncode != 0 and 'out of date' in r.stderr, ('build_learn.py used results from an older rule', r.stderr[-300:])

@test
def a_site_is_broken_only_when_it_surely_is():
    # #85: check_sites.py took "no answer" as working, so a site whose name doesn't resolve, or whose secure connection
    # fails (Okey Anyiam's, Oct 17), stayed linked. Now curl's exit code counts (6, 35); bot walls and timeouts don't; a
    # break is recorded only if it repeats; and build_learn.py unlinks by the same rule.
    import importlib, shutil
    cs = importlib.import_module('check_sites')
    rule = {('404', None): True, ('410', None): True, ('000', 6): True, ('000', 35): True, ('000', 28): False, ('000', None): False, ('000', 60): True,
            ('403', None): False, ('429', None): False, ('503', None): False, ('200', None): False, ('301', 35): True, ('200', 0): False}
    assert {k: cs.broken(*k) for k in rule} == rule, {k: cs.broken(*k) for k in rule}
    def fake(seq):
        it = iter(seq); calls = []
        def c(url): calls.append(url); return next(it)
        return c, calls
    real = cs.curl
    try:
        cs.curl, calls = fake([('000', 35), ('000', 35), ('200', 0)])        # broken, then fine on the retry: fine
        assert cs.check(('X', {'site': 'x.org'}), wait=0)[2] == '200' and len(calls) == 3, calls
        cs.curl, calls = fake([('000', 35), ('000', 35), ('000', 35), ('000', 35)])
        assert cs.check(('X', {'site': 'x.org'}), wait=0)[2:] == ('000', 35)
        cs.curl, calls = fake([('000', 28), ('000', 28)])                    # a timeout: no retry, stays linked
        assert cs.check(('X', {'site': 'x.org'}), wait=0)[2:] == ('000', 28) and len(calls) == 2
        cs.curl, calls = fake([('000', 35), ('301', 35)] * 2)                # https fails; http redirects into the same failure
        assert cs.check(('X', {'site': 'x.org'}), wait=0)[1:] == ('https://x.org', '000', 35), calls
        cs.curl, calls = fake([('000', 35), ('000', 56)] * 2)                # https fails; http fails some other way: https's counts
        assert cs.check(('X', {'site': 'x.org'}), wait=0)[1:] == ('https://x.org', '000', 35), calls
        cs.curl, calls = fake([('000', 28), ('200', 0)])                     # https too slow, http answers: the http link
        assert cs.check(('X', {'site': 'x.org'}), wait=0)[1:] == ('http://x.org', '200', 0) and calls == ['https://x.org', 'http://x.org']
        cs.curl, calls = fake([('200', 0, 'https://www.newname.org/home?utm_source=x&sid=9#top')])   # moved hosts: linked where it
        assert cs.check(('X', {'site': 'x.org'}), wait=0)[1:] == ('https://www.newname.org/home', '200', 0), calls   # ended, bare (#120)
        cs.curl, calls = fake([('200', 0, 'https://www.x.org/en/?sid=9')])   # its own name, with www: the address it was given
        assert cs.check(('X', {'site': 'x.org'}), wait=0)[1:] == ('https://x.org', '200', 0), calls
        cs.curl, calls = fake([('000', 28, ''), ('200', 0, 'https://new.org/')])   # only http answered, on a new host
        assert cs.check(('X', {'site': 'x.org'}), wait=0)[1:] == ('https://new.org/', '200', 0), calls
        cs.curl, calls = fake([('403', 0, 'https://validate.wall.net/?u=x')])   # a bot wall's challenge host is never the link
        assert cs.check(('X', {'site': 'x.org'}), wait=0)[1:] == ('https://x.org', '403', 0), calls
        cs.curl, calls = fake([('403', 0)])                                  # a bot wall over https: no http try
        assert cs.check(('X', {'site': 'x.org'}), wait=0)[1:] == ('https://x.org', '403', 0) and len(calls) == 1
        for late in (56, 92, 28):                                            # https answered, then the page broke off: keep https (Pass 2)
            cs.curl, calls = fake([('200', late)])
            assert cs.check(('X', {'site': 'x.org'}), wait=0)[1:] == ('https://x.org', '200', late) and len(calls) == 1, (late, calls)
        cs.curl, calls = fake([('000', 28), ('301', 28)])                    # http redirects to the https that didn't answer: keep https (Pass 3)
        assert cs.check(('X', {'site': 'x.org'}), wait=0)[1:] == ('https://x.org', '000', 28)
        cs.curl, calls = fake([('403', 0)])
        assert cs.check(('X', {'site': 'x.org'}), wait=0)[1:] == ('https://x.org', '403', 0) and len(calls) == 1
    finally:
        cs.curl = real
    runs = []                                                                # an incomplete chain is asked again without curl's check;
    class P:                                                                 # any other refused certificate is not (Pass 3)
        def __init__(s, rc, err, out='200'): s.returncode, s.stderr, s.stdout = rc, err, out
    real_run = cs.subprocess.run
    try:
        for err, want in (('curl: (60) SSL certificate problem: unable to get local issuer certificate', ('200', 0)),
                          ('curl: (60) SSL certificate problem: certificate has expired', ('000', 60)),
                          ('curl: (60) SSL: no alternative certificate subject name matches target host name', ('000', 60))):
            runs.clear()
            cs.subprocess.run = lambda args, **k: (runs.append(args), P(0, '', '200 https://www.x.org/') if '-k' in args else P(60, err, ''))[1]
            got = cs.curl('https://x.org')
            assert got[:2] == want and got[2] == ('https://www.x.org/' if want[1] == 0 else '') and (('-k' in runs[-1]) == (want[1] == 0)), (err, runs)
    finally:
        cs.subprocess.run = real_run
    assert cs.proxied({'HTTPS_PROXY': 'http://p:1'}) == ['HTTPS_PROXY'] and cs.proxied({'https_proxy': ''}) == [] and cs.proxied({}) == []
    with tempfile.TemporaryDirectory() as d:
        d = pathlib.Path(d) / 's'; shutil.copytree(ROOT / 'source', d, ignore=shutil.ignore_patterns('*.pdf', '__pycache__', '.mutate-lock', '*.mutate-tmp'))
        before = (d / 'data/lwv_candidates.json').read_bytes()
        r = subprocess.run([sys.executable, str(d / 'check_sites.py')], capture_output=True, text=True, env=dict(os.environ, HTTPS_PROXY='http://127.0.0.1:9'))
        assert r.returncode != 0 and 'proxy' in r.stderr and (d / 'data/lwv_candidates.json').read_bytes() == before, ('checked links behind a proxy', r.stderr[-300:])
        lwv = json.loads((d / 'data/lwv_candidates.json').read_text(encoding='utf-8'))
        lwv['Okey Anyiam (DEM)'].update(http='000', curl=35)
        (d / 'data/lwv_candidates.json').write_text(json.dumps(lwv), encoding='utf-8')
        (d / 'data/sites_checked.json').write_text(json.dumps({'rule': cs.RULE, 'sites': cs.digest(lwv)}), encoding='utf-8')   # as a check that found it so
        r = subprocess.run([sys.executable, str(d / 'build_learn.py')], capture_output=True, text=True, cwd=str(d)); assert r.returncode == 0, r.stderr[-600:]
        e = json.loads((d / 'learn.json').read_text(encoding='utf-8'))[lwv['Okey Anyiam (DEM)']['contest']]['cands']['Okey Anyiam']
        assert e.get('s') is None and e.get('sx') == 1, e
        # Pass 1 (round 2): a run behind a proxy, when told to go ahead, leaves no stamp, so build_learn.py stops.
        assert (d / 'data/sites_checked.json').exists()
        r = subprocess.run([sys.executable, str(d / 'check_sites.py'), '--behind-proxy'], capture_output=True, text=True, timeout=300,
                           env={**{k: v for k, v in os.environ.items() if k.lower() not in ('no_proxy', 'https_proxy', 'http_proxy', 'all_proxy')},   # every request fails at once,
                                **{k: 'http://127.0.0.1:9' for k in ('https_proxy', 'http_proxy', 'HTTPS_PROXY', 'ALL_PROXY')}})   # never reaching a site
        assert r.returncode == 0 and not (d / 'data/sites_checked.json').exists(), ('a run behind a proxy was stamped', r.stdout[-300:], r.stderr[-300:])
        got = json.loads((d / 'data/lwv_candidates.json').read_text(encoding='utf-8'))
        assert all(v['http'] == '000' for v in got.values() if v.get('site')), 'a request got past the dead proxy (a ~/.curlrc?): this test reached a site'
        r = subprocess.run([sys.executable, str(d / 'build_learn.py')], capture_output=True, text=True, cwd=str(d))
        assert r.returncode != 0 and 'out of date' in r.stderr, r.stderr[-300:]


def street_problems(d):
    """What is wrong with the street map's data d (source/data/streets.json, parsed), as a list; [] when nothing is."""
    import fetch_streets as F
    out, q = [], d.get('q')
    if set(d) != {'v', 'q', 'fwy', 'hwy', 'art', 'water', 'tags', 'order'} or d['v'] != 1 or q != F.Q: return ['keys or version: ' + str(sorted(d))]
    for layer, box, least in (('fwy', F.VIEW, 50), ('hwy', F.VIEW, 150), ('art', F.NEAR, 300), ('water', F.VIEW, 5)):
        if len(d[layer]) < least: out.append(f'{layer}: only {len(d[layer])}')
        for a in d[layer]:
            if len(a) < 4 or len(a) % 2 or not all(type(v) is int for v in a): out.append(f'{layer}: malformed {a[:6]}'); continue
            x, y, pts = a[0], a[1], [(a[0], a[1])]
            for i in range(2, len(a), 2): x += a[i]; y += a[i + 1]; pts.append((x, y))
            if not all(box[0] - 1 / q <= px / q <= box[2] + 1 / q and box[1] - 1 / q <= py / q <= box[3] + 1 / q for px, py in pts): out.append(f'{layer}: a point outside {box}')
            if layer == 'water' and pts[0] != pts[-1]: out.append('water: an outline not closed')
    if d['order'] != [label for label, _ in F.TAGS] or {t[0] for t in d['tags']} != set(d['order']): out.append('tags: a label with no place, or a place with no label')
    if not all(len(t) == 3 and type(t[1]) is int and type(t[2]) is int and F.VIEW[0] <= t[1] / q <= F.VIEW[2] and F.VIEW[1] <= t[2] / q <= F.VIEW[3] for t in d['tags']): out.append('tags: a malformed place, or one outside the view')
    near = lambda lab, x, y: any(t[0] == lab and abs(t[1] / q - x) < 0.03 and abs(t[2] / q - y) < 0.03 for t in d['tags'])
    if not (near('I-35', -97.7357, 30.2672) and near('MoPac', -97.7700, 30.2950)): out.append('tags: I-35 or MoPac not near downtown')
    return out


@test
def street_data_is_whole_and_in_view():
    """source/data/streets.json, the street map's data (Lane, Oct 19), as source/fetch_streets.py writes it and the page
    reads it: compact, within its size cap, every layer there, every point inside the area the maps can show, every
    lake outline closed, a place for every highway label and the labels in the script's order. The check is shown to
    catch each kind of damage on a copy."""
    import copy, fetch_streets as F
    raw = (ROOT / 'source/data/streets.json').read_bytes()
    d = json.loads(raw)
    assert raw == (json.dumps(d, separators=(',', ':')) + '\n').encode('utf-8'), 'not as fetch_streets.py writes it (compact, one line)'
    assert len(raw) <= F.MAX_BYTES, (len(raw), F.MAX_BYTES)
    assert street_problems(d) == [], street_problems(d)
    for damage in (lambda e: e['water'][0].extend([1, 1]),                 # an outline left open
                   lambda e: e['art'][0].__setitem__(0, e['art'][0][0] - 20000),   # a street moved 2 degrees west
                   lambda e: e['tags'].__setitem__(slice(None), [t for t in e['tags'] if t[0] != '71']),   # a highway with no label place
                   lambda e: e['order'].reverse(),
                   lambda e: e['fwy'].__setitem__(slice(10, None), []),
                   lambda e: e['hwy'][0].append(5)):
        e = copy.deepcopy(d); damage(e)
        assert street_problems(e), 'the check missed a damaged copy'



# ---------------------------------------------------------------- results on your ballot (docs/plans/2026-10-20-results.md)
def results_mods():
    import importlib
    import check_results
    spec = importlib.util.spec_from_file_location('results_fixture', ROOT / 'tests/results_fixture.py')
    fx = importlib.util.module_from_spec(spec); spec.loader.exec_module(fx)
    return check_results, fx


@test
def the_published_results_file_and_every_scene_are_sound():
    """results.json (the placeholder until Nov 4, then each day's) and the test scenes pass source/check_results.py."""
    cr, fx = results_mods()
    key = cr.answer_key()
    assert cr.check(json.loads((ROOT / 'results.json').read_text(encoding='utf-8')), key) == []
    for sc in ('mixed', 'official', 'withdrawn'):
        assert cr.check(fx.scene(sc), key) == [], (sc, cr.check(fx.scene(sc), key))
    r = subprocess.run([sys.executable, 'source/check_results.py'], cwd=str(ROOT), capture_output=True, text=True)
    assert r.returncode == 0 and 'sound' in r.stdout, (r.stdout, r.stderr)


@test
def the_results_check_refuses_each_kind_of_wrong_file():
    """Each rule the page relies on: refused on a copy that breaks it (the check is shown to catch each one)."""
    import copy
    cr, fx = results_mods()
    key, good = cr.answer_key(), fx.scene('mixed')
    def broken(f):
        e = copy.deepcopy(good); f(e); return e
    C = lambda e, cid: e['contests'][cid]
    cases = {
        'unofficial says won': lambda e: C(e, 'c071').update(verdict='passed'),
        'official says leading': lambda e: C(e, 'c069').update(state='official', verdict='leading', leaders=['Selena Xie'], canvass={'kind': 'local', 'by': '2026-11-17', 'on': None, 'done': '2026-11-12'}),
        'a leader who is not a choice': lambda e: C(e, 'c113').update(leaders=['Someone Else', 'Sarah Ponder']),
        'choices out of ballot order': lambda e: C(e, 'c069')['choices'].reverse(),
        'a party suffix in a name': lambda e: C(e, 'c001')['choices'][0].__setitem__(0, 'Ken Paxton (REP)'),
        'a write-in before the ballot choices': lambda e: C(e, 'c001')['choices'].insert(0, C(e, 'c001')['choices'].pop()),
        'write_ins flag wrong': lambda e: C(e, 'c001').update(write_ins=False),
        'a measure with a write-in': lambda e: C(e, 'c071')['choices'].append(['Somebody', 5, 0.0, True]),
        'partial without a missing county': lambda e: C(e, 'c072').update(missing=[]),
        'a missing county without partial': lambda e: C(e, 'c071').update(missing=['Hays County']),
        'zero votes name a verdict': lambda e: C(e, 'c117').update(state='unofficial', verdict='too_close'),
        'counting with votes': lambda e: C(e, 'c117')['choices'][0].__setitem__(1, 3),
        'a percent over 100': lambda e: C(e, 'c071')['choices'][0].__setitem__(2, 101),
        'a posted time without a time': lambda e: C(e, 'c071')['sources'][0].__setitem__(1, '2026-11-04'),
        'state canvass outside its window': lambda e: C(e, 'c001').update(state='official', verdict='tied', canvass={'kind': 'state', 'by': '2026-12-07', 'on': None, 'done': '2026-11-20'}),
        'the Legislature before it meets': lambda e: C(e, 'c006').update(state='official', verdict='tied', canvass={'kind': 'legislature', 'by': None, 'on': None, 'done': '2026-12-01'}),
        'official numbers flag on an unofficial result': lambda e: C(e, 'c071').update(official_numbers=False),
        'changed after the file': lambda e: C(e, 'c071').update(changed=99),
        'a contest not on Travis ballots': lambda e: e['contests'].__setitem__('c999', C(e, 'c071')),
        'a recount link that is not https': lambda e: C(e, 'c071').update(recount='http://example.com'),
        'a race said to pass': lambda e: C(e, 'c069').update(verdict='passing'),
        'withdrawn not a boolean': lambda e: e.update(withdrawn='no'),
        'an extra key': lambda e: C(e, 'c071').update(extra=1),
        'runoff names one': lambda e: C(e, 'c121').update(verdict='runoff', runoff=['Cheryl Bradley']),
        'won names two (#135)': lambda e: C(e, 'c113').update(state='official', verdict='won', leaders=['Sarah Ponder', 'Robert Johnson'], canvass={'kind': 'local', 'by': '2026-11-17', 'on': None, 'done': '2026-11-12'}),
    }
    missed = [n for n, f in cases.items() if not cr.check(broken(f), key)]
    assert not missed, ('the check missed', missed)
    prev = fx.scene('mixed')
    same = copy.deepcopy(prev); same['seq'] += 1
    assert cr.check(same, key, prev), 'seq went up with nothing changed'
    up = copy.deepcopy(prev); up['contests']['c071']['choices'][0][1] += 10; up['contests']['c071']['choices'][0][2] = 60.0
    assert cr.check(up, key, prev), 'a change without seq + 1'
    up['seq'] = prev['seq'] + 1
    assert cr.check(up, key, prev) == [], cr.check(up, key, prev)
    back = copy.deepcopy(up); back['contests']['c071']['sources'][0][1] = '2026-11-03T20:00'
    assert cr.check(back, key, up), 'a posted time went backwards'
    back['contests']['c071']['corrected'] = '2026-11-05'; back['seq'] = up['seq'] + 1
    assert cr.check(back, key, up) == [], ('a correction may go back', cr.check(back, key, up))


@test
def results_alone_need_no_new_version():
    """Lane, Oct 20: results.json is exempt from the bump rule; anything published beside it still needs a bump."""
    import shutil
    with tempfile.TemporaryDirectory() as d:
        d = pathlib.Path(d) / 'r'
        shutil.copytree(ROOT, d, ignore=shutil.ignore_patterns('.git', '__pycache__', '*.pdf', '.mutate-lock', '*.mutate-tmp', '_site'))
        git = lambda *a: subprocess.run(['git', '-c', 'user.name=t', '-c', 'user.email=t@t', '-c', 'commit.gpgsign=false', *a], cwd=str(d), capture_output=True, text=True, check=True)
        run = lambda: subprocess.run([sys.executable, 'source/check_bumped.py'], cwd=str(d), capture_output=True, text=True)
        git('init', '-q'); git('add', '-A'); git('commit', '-qm', 'base'); git('tag', 'v' + (d / 'VERSION').read_text().strip())
        bump = lambda: (d / 'results.json').write_text(re.sub(r'"seq":(\d+)', lambda m: '"seq":' + str(int(m.group(1)) + 1), (d / 'results.json').read_text(), count=1))   # whatever seq the file is at (the Results workflow has run)
        bump(); git('commit', '-qam', 'results')
        r = run(); assert r.returncode == 0, ('a results update alone needed a bump', r.stdout, r.stderr)
        (d / 'index.html').write_text((d / 'index.html').read_text(encoding='utf-8').replace('<title>', '<title> ', 1), encoding='utf-8')
        bump(); git('commit', '-qam', 'both')
        r = run(); assert r.returncode != 0 and 'index.html' in r.stdout + r.stderr and 'results.json' not in r.stdout + r.stderr, ('the page beside it', r.stdout, r.stderr)


@test
def results_off_leaves_no_trace():
    """RESULTS_LIVE = False (the code rollback): the page carries none of the results code, no results/ link page is
    written, and the offline worker is exactly the one before results."""
    import build_site as B
    off = B.build(results=False)
    assert 'rs-top' not in off and 'results.json' not in off and 'results_seen' not in off and '/*RESULTS*/' not in off
    on = B.build()
    assert ('rs-top' in on) == B.RESULTS_LIVE   # kept blocks keep their markers, as DESK and PHONE do
    was = B.RESULTS_LIVE
    try:
        B.RESULTS_LIVE = False
        assert 'results/index.html' not in B.outputs(False) and 'savedCopy' not in B.sw_js(False)
    finally:
        B.RESULTS_LIVE = was
    if was:
        assert 'results/index.html' in B.outputs(False) and B.sw_js(False).count("u.pathname.endsWith('/results.json') ? savedCopy(kept)") == 1


@test
def vote_sites_match_the_clerks_lists():
    """Round 2 #20 (#118): vote_sites.json against the Travis County Clerk's own flyers, frozen in tests/fixtures/clerk/
    (votetravis.gov, early voting dated Sep 25, Election Day Oct 2, 2026; download the new ones if the Clerk updates
    them). Every site is one row of its list, found by street address and city; the count, the bus route ("B"), the
    early sites open till 10 pm Oct 29-30 (the list's *, "L") and the one open Friday Oct 30 only ("F") all agree."""
    import pdfplumber
    fixed = {('early', '1201 e rundberg ln'): '1201 e runberg ln'}   # the Clerk's typo on the early list; the page spells it right
    sites = json.loads((ROOT / 'source/vote_sites.json').read_text(encoding='utf-8'))
    row = re.compile(r'^(\d{3}) (.+) (\d{5}) (Yes|No)$')
    for kind, f in (('early', 'G26-Early-Voting-Flyer-2026-09-25.pdf'), ('eday', 'G26-Election-Day-Flyer-2026-10-02.pdf')):
        with pdfplumber.open(ROOT / 'tests/fixtures/clerk' / f) as pdf:
            text = [l.strip() for p in pdf.pages for l in (p.extract_text() or '').splitlines()]
        rows = [l for l in text if row.match(l)]
        assert len(rows) == len(sites[kind]), (kind, len(rows), len(sites[kind]))
        friday = ' '.join(l for l in text if 'only serve as an early voting polling location on Friday, October 30' in l)
        bad = []
        for nm, room, addr, city, fl, *_ in sites[kind]:
            a = fixed.get((kind, addr.lower()), addr.lower())
            hit = [r for r in rows if f' {a} {city.lower()} ' in r.lower() + ' ']
            if len(hit) != 1: bad.append(('no single row', nm, addr, len(hit))); continue
            r = hit[0]
            if r.endswith(' Yes') != ('B' in fl): bad.append(('bus route', nm, fl))
            if kind == 'early' and (nm + '*' in r) != ('L' in fl): bad.append(('open till 10 pm', nm, fl))
            if ('F' in fl) != (kind == 'early' and nm in friday): bad.append(('Friday only', nm, fl))
        assert not bad, (kind, bad)

@test
def browser_clocks_are_set_in_austins_time():
    """Round 2 #17 (#115): a naive datetime given to the page's clock is read in the runner's own zone, so the midnight
    tests checked the wrong day anywhere outside US Central. Every clock time in the site tests is zoned."""
    src = (ROOT / 'tests/test_site.py').read_text(encoding='utf-8')
    naive = re.findall(r'(?:clock\.install\(time=|clock\.set_fixed_time\(|clock\.set_system_time\()\s*(?:dt|_dt)\.datetime\([^)]*\)', src)
    assert not naive, naive

if __name__ == '__main__':
    failed = 0
    for fn in TESTS:
        try: fn(); print('PASS', fn.__name__)
        except AssertionError as e: failed += 1; print('FAIL', fn.__name__, '-', str(e)[:600])
    print(f'{len(TESTS) - failed}/{len(TESTS)} passed (pipeline)')
    sys.exit(1 if failed else 0)
