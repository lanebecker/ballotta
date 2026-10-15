"""Check every campaign website listed in data/lwv_candidates.json and record the URL that answered and its HTTP status.
Run after parse_lwv.py, before build_learn.py:   python3 source/check_sites.py
build_learn.py treats only 404/410 as broken: 403/429/503/999 and timeouts were bot walls on sites whose DNS resolves.
"""
import json, pathlib, subprocess, concurrent.futures as cf
P = pathlib.Path(__file__).resolve().parent / 'data/lwv_candidates.json'
r = json.load(open(P, encoding='utf-8'))
UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Safari/605.1.15'
def check(item):
    ch, v = item
    s = v['site'].split('@')[-1]  # the guide lists one email address as a "website"; link its domain
    for scheme in ('https://', 'http://'):
        code = subprocess.run(['curl', '-s', '-o', '/dev/null', '-L', '-A', UA, '-w', '%{http_code}', '--max-time', '20', scheme + s],
                              capture_output=True, text=True).stdout.strip() or '000'
        if code != '000': return ch, scheme + s, code
    return ch, 'https://' + s, '000'
items = [(ch, v) for ch, v in r.items() if v.get('site')]
with cf.ThreadPoolExecutor(12) as ex:
    for ch, url, code in ex.map(check, items):
        r[ch]['url'], r[ch]['http'] = url, code
        if not code.startswith(('2', '3')): print('not 2xx/3xx:', ch, url, code)
json.dump(r, open(P, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(len(items), 'sites checked')
