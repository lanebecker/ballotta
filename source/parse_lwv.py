"""Parse the LWV Austin Area 2026 voters guide line by line in reading order (page, column, y):
per-candidate page, listed campaign website, and whether answers were received."""
import sys, json, re, unicodedata, pathlib
import pymupdf
pdf, key_path, out = sys.argv[1:4]
key = json.load(open(key_path, encoding='utf-8'))

def clean(s): return s.replace('​', '').replace('­', '').replace(' ', ' ')
def norm(s):
    s = unicodedata.normalize('NFKD', clean(s))
    s = ''.join(ch for ch in s if not unicodedata.combining(ch))
    s = re.sub(r'\((REP|DEM|LIB|GRN|R|D|L|G|WI|Independent)\)', '', s)
    s = re.sub(r'\(continued\)', '', s, flags=re.I)
    s = re.sub(r'[“”"‘’\'.,]', '', s)
    return re.sub(r'\s+', ' ', s).strip().lower()

doc = pymupdf.open(pdf)
lines = []  # (page, col, y, text, bold)
for i, p in enumerate(doc):
    d = p.get_text('dict')
    for b in d['blocks']:
        for l in b.get('lines', []):
            t = clean(''.join(s['text'] for s in l['spans'])).strip()
            if not t: continue
            x0, y0 = l['bbox'][0], l['bbox'][1]
            if y0 > 715: continue  # footer
            col = 0 if x0 < 250 else (1 if x0 < 500 else 2)
            bold = any('Bold' in s['font'] or 'Black' in s['font'] or (s['flags'] & 16) for s in l['spans'])
            wide = (l['bbox'][2] - x0) > 300 or any('Black' in sp['font'] for sp in l['spans'])
            lines.append([i + 1, col, round(y0, 1), t, bold, wide, tuple(l['bbox'])])
# Full-width section headers split a page into bands; text flows column by column within each band.
for pg in {r[0] for r in lines}:
    hy = sorted(r[2] for r in lines if r[0] == pg and r[5])
    for r in lines:
        if r[0] == pg: r.append(sum(1 for h in hy if h <= r[2] + 0.5))
lines.sort(key=lambda r: (r[0], r[7], r[1], r[2]))
bbox = {id(r): r[6] for r in lines}
full = lines
lines = [tuple(r[:5]) + (r[6],) for r in lines]

cands = []
for c in key['contests']:
    if c['type'] != 'candidate': continue
    for ch in c['choices']:
        if ch != 'Write-in': cands.append((c['id'], ch, norm(ch)))
names = {n: (cid, ch) for cid, ch, n in cands}
# The guide sometimes prints a fuller or shorter form of the ballot name (verified against the PDF, Oct 14, 2026).
ALIASES = {'Mike Randolph': 'Michael Randolph', 'Josh Castro': 'Joshua Castro', 'Skyler A. Korgel': 'Skyler Korgel'}
for cid, ch, n in cands:
    if ch in ALIASES: names[norm(ALIASES[ch])] = (cid, ch)
# Sites the line parser misses (wrapped columns); each value must appear verbatim in the PDF text (asserted below).
SITE_OVERRIDES = {'Pat Dixon (LIB)': 'patdixon.org', 'Thomas Smith (REP)': 'www.smithfortexas.org'}

# Every line that is a candidate-name heading (ours or anyone's: any short bold line followed by Qualifications/No response/Please see)
heads = []
for k, (pg, col, y, t, bold, _bb) in enumerate(lines):
    if 'continued' in t.lower(): continue
    n = norm(t)
    nxt = ' '.join(x[3] for x in lines[k + 1:k + 3])
    is_head = bold and len(t) < 60 and re.match(r'(Qualifications|No response|Please see|Unopposed|Campaign Website|Biographical|Background|Training|Experience)', nxt)
    if n in names or is_head:
        heads.append(k)
res = {}
for idx, k in enumerate(heads):
    n = norm(lines[k][3])
    if n not in names or names[n][1] in res: continue
    cid, ch = names[n]
    end = heads[idx + 1] if idx + 1 < len(heads) else len(lines)
    seg = lines[k:end]
    text = '\n'.join(x[3] for x in seg)
    site = None
    for j, x in enumerate(seg):
        m = re.match(r'Campaign Website:\s*(.*)$', x[3])
        if m:
            s = m.group(1).strip()
            bb = x[5]
            cont = [y for y in lines if y[0] == x[0] and abs(y[5][0] - bb[0]) < 30 and 0 < y[5][1] - bb[1] < 20 and ' ' not in y[3].strip()]
            if cont: s += cont[0][3].strip()
            site = re.sub(r'^https?://', '', s.replace(' ', '')).rstrip('/')
            break
    noresp = bool(re.search(r'No response received|Please see VOTE411', text))
    # Unopposed only when the guide says so directly under this candidate's name (not anywhere in the segment).
    # Geometric: the guide prints "Unopposed" directly under the name. (Reading order alone fails where two
    # names sit side by side in one column, e.g. Brigid Shea / George Morales III on p.24.)
    hb = lines[k][5]
    unopposed = any(l[0] == lines[k][0] and abs(l[5][0] - hb[0]) < 15 and 0 < l[5][1] - hb[1] < 26 and l[3].strip().startswith('Unopposed') for l in lines)
    if ch in SITE_OVERRIDES: site = SITE_OVERRIDES[ch]
    res[ch] = {'contest': cid, 'in_guide': True, 'page': lines[k][0], 'site': site, 'answered': not (noresp or unopposed), 'unopposed': unopposed}
for cid, ch, n in cands:
    res.setdefault(ch, {'contest': cid, 'in_guide': False})
# Keep earlier link-check results for unchanged sites.
try:
    old = json.load(open(out, encoding='utf-8'))
    for ch, v in res.items():
        o = old.get(ch, {})
        if v.get('site') and o.get('site') == v['site'] and 'http' in o: v['url'], v['http'] = o['url'], o['http']
except FileNotFoundError:
    pass
alltext = ''.join(clean(p.get_text()) for p in doc).replace('\n', '')
for ch, s_ in SITE_OVERRIDES.items():
    assert res.get(ch, {}).get('in_guide') and s_ in alltext and res[ch]['site'] == s_, ('override not verifiable in the PDF', ch, s_)
# A contested race can't contain an "unopposed" candidate.
by_race, sole_check = {}, []
for ch, v in res.items(): by_race.setdefault(v['contest'], []).append(v)
for cid, vs in by_race.items():
    ing = [v for v in vs if v.get('in_guide')]
    assert not (len(vs) > 1 and any(v.get('unopposed') for v in ing)), ('unopposed candidate in a contested race', cid)
    # ...and a sole printed candidate the guide covers is either marked unopposed or has real answers under the name.
    if len(vs) == 1 and ing and not ing[0].get('unopposed'): sole_check.append((cid, ing[0]))
# Every "Campaign Website" in the guide must be credited to a ballot candidate or belong to a race not on the Travis ballot.
credited = {re.sub(r'[^a-z0-9]', '', (v.get('site') or '').lower().split('@')[-1]) for v in res.values()}
unclaimed = []
for (pg, col, y, t, bold, bb) in lines:
    m = re.match(r'Campaign Website:\s*(\S+)', t)
    if m:
        key_ = re.sub(r'[^a-z0-9]', '', re.sub(r'^https?://', '', m.group(1).lower()).split('@')[-1])
        if not any(c and (c.startswith(key_[:14]) or key_.startswith(c[:14])) for c in credited): unclaimed.append((pg, m.group(1)))
print('guide sites not credited to a Travis ballot candidate:', unclaimed)
# Checked by hand against the PDF (Oct 14, 2026): Dyana Limon-Mercado (County Clerk, opposed only by a write-in) answered.
SOLE_ANSWERED_OK = {'c053'}
assert {c for c, v in sole_check} == SOLE_ANSWERED_OK, ('sole candidate marked as answering; check the PDF by hand', sole_check)
json.dump(res, open(out, 'w'), ensure_ascii=False, indent=1)
print(sum(1 for v in res.values() if v['in_guide']), 'of', len(res), 'in guide;', sum(1 for v in res.values() if v.get('site')), 'with sites')

# ---- measures: first page of each (entity, proposition letter) ----
meas = {}
ent = None
for (pg, col, y, t, bold, bb) in lines:
    m = re.match(r'^LOCAL\s+(.*)$', t.strip())
    if m: ent = m.group(1).strip(); continue
    m = re.match(r'^PROPOSITION(?:\s+([A-Z]))?(\s*\(continued\))?$', t.strip())
    if m and ent and not m.group(2):
        letter = m.group(1) or 'A'
        meas.setdefault(ent + '|' + letter, pg)
# Reading-order artifact: Georgetown ISD's Prop A heading on p.50 follows the end of Del Valle ISD's section; the guide
# has no Del Valle ISD proposition (checked by hand, Oct 14, 2026).
meas.pop('DEL VALLE INDEPENDENT SCHOOL DISTRICT|A', None)
json.dump(meas, open(pathlib.Path(out).with_name('lwv_measures.json'), 'w'), indent=1)
print(meas)
