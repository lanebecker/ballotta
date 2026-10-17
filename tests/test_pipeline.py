"""The answer key against the ballot itself (cold audit, Oct 17: #1, #2, #3, #5). No browser; about 20 seconds.

    python3 tests/test_pipeline.py

1. source/ballot/build_answer_key.py reproduces the committed source/answer_key.json byte for byte, so no correction
   lives only in the JSON (a rerun would silently undo it).
2. Every candidate contest lists its choices in the order the ballot PDF prints them, top to bottom.
3. Every measure's text is exactly the ballot's English text (no Spanish caption carried along).
4. Every party label on the ballot (104, legend aside) is on the same name in the key, and the key has no others.
5. The ballot's FOR / AGAINST pairs number exactly the key's measures.
"""
import json, pathlib, re, subprocess, sys, tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'source/ballot'))
import pdf_lines

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
def every_measure_text_is_the_ballots_english():
    pdf = pdf_lines.measures(L)
    key = [c for c in KEY['contests'] if c['type'] == 'measure']
    assert len(pdf) == len(key) == 93, (len(pdf), len(key))
    bad = [(c['id'], c['text'][-50:], t[-50:]) for (_, t), c in zip(pdf, key) if pdf_lines.norm(c['text']) != t]
    assert not bad, ('measure text differs from the ballot', bad[:5], len(bad))
    spanish = re.compile(r'(Núm\.|Condado de|Distrito |Ciudad de|Propuesta|Proposición)')
    assert not [c['id'] for c in key if spanish.search(c['text'][-60:])], 'a measure text ends in Spanish'


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


if __name__ == '__main__':
    failed = 0
    for fn in TESTS:
        try: fn(); print('PASS', fn.__name__)
        except AssertionError as e: failed += 1; print('FAIL', fn.__name__, '-', str(e)[:600])
    print(f'{len(TESTS) - failed}/{len(TESTS)} passed (pipeline)')
    sys.exit(1 if failed else 0)
