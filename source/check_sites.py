"""Check every campaign website listed in data/lwv_candidates.json and record the URL that answered, its HTTP status and,
when the request didn't finish, curl's exit code. Run after parse_lwv.py, before build_learn.py:   python3 source/check_sites.py

A site is broken (build_learn.py shows it unlinked) only on a definite failure: 404 or 410, or a request that can't
finish because the name doesn't resolve (curl exit 6), the secure connection can't be made (35) or the certificate is
refused (60: expired, self-signed, for another name), whatever status came before (#85: a site whose https fails that
way, and whose http redirects into the same failure). A certificate whose chain is merely incomplete is not broken:
browsers fetch the missing piece, so the site is asked again without curl's own check. 403/429/503/999 and timeouts
were bot walls on sites that load in a normal browser (checked Oct 14), so they stay linked. A break is recorded only
if it happens twice, a few seconds apart, so one bad moment can't unlink a site.

A site that moved hosts (it redirects to another name, not just to www., and answers 2xx there) is linked by the address
it ended at, without its query string (round 2 #23, #120); a site that stays on its own name keeps the address it was given.

It also writes data/sites_checked.json: the rule's version (RULE) and a digest of the sites checked and their results.
build_learn.py stops when either no longer matches (stale()), so a change to the rule can't ship with results the old
rule made (round-2 audit #2: the 1.1.3 rule never reached the shipped data), nor a re-parsed guide with sites never
checked, nor a result edited by hand. A run with --behind-proxy records its results but no stamp: its breaks may be the
proxy's.

Run it from an ordinary connection. Behind a proxy (HTTPS_PROXY and the like), the proxy's own refusals look exactly
like broken sites (Oct 18: from a proxied sandbox, the same three sites failed and answered by turns), so it stops
there unless given --behind-proxy.
"""
import datetime, hashlib, json, os, pathlib, subprocess, sys, time, concurrent.futures as cf
P = pathlib.Path(__file__).resolve().parent / 'data/lwv_candidates.json'
STAMP = P.with_name('sites_checked.json')
RULE = 2   # the broken-link rule's version: bump it with any change to what a site is recorded as (1: Oct 14; 2: #85, 1.1.3)
UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Safari/605.1.15'
BROKEN_EXIT = {6: 'the name does not resolve', 35: 'the secure connection fails', 60: 'the certificate is refused'}   # an incomplete chain is not: see curl()


def broken(http, curl=None):
    """The one rule for a broken link, shared with build_learn.py. curl's exit code counts whatever status came before
    it: with -L, a redirect into a failing https leaves the redirect's 301 as the status and the failure as the exit."""
    return str(http) in ('404', '410') or curl in BROKEN_EXIT


CHAIN_ONLY = 'unable to get local issuer certificate'   # curl's words for a chain it won't complete; browsers do (Pass 3)


def curl(url, insecure=False):
    p = subprocess.run(['curl', '-sS', '-o', '/dev/null', '-L', '-A', UA, '-w', '%{http_code} %{url_effective}', '--max-time', '20', *(['-k'] if insecure else []), url],
                       capture_output=True, text=True)
    if p.returncode == 60 and CHAIN_ONLY in p.stderr and not insecure:
        return curl(url, insecure=True)          # only the missing intermediate: ask what a browser, which fetches it, would get
    code, _, final = p.stdout.strip().partition(' ')
    return (code or '000'), p.returncode, final   # the address it ended at, after any redirects (#120)


def answered(code, ex):
    """A status came back and nothing definitely failed after it (a reset mid-page or a slow body after a 200 is still
    a site that answers; Pass 2)."""
    return ex == 0 or (code != '000' and ex not in BROKEN_EXIT)


def moved(url, final):
    """The address to link: the final one, without query or fragment, only when it is on another host (#120)."""
    from urllib.parse import urlsplit, urlunsplit
    host = lambda u: (urlsplit(u).hostname or '').removeprefix('www.')
    if not str(final).startswith(('https://', 'http://')) or not host(final) or host(final) == host(url): return url
    f = urlsplit(final)
    return urlunsplit((f.scheme, f.netloc, f.path, '', ''))
def once(s):
    """https first; http only if https didn't answer. When both fail, https's failure is the one recorded: http's own
    (a reset, or its redirect into the same broken https) says nothing about the link we'd show."""
    def ask(url):
        r = curl(url)
        return r[0], r[1], (moved(url, r[2] if len(r) > 2 else '') if str(r[0]).startswith('2') else url)   # a bot wall's
                                                                     # challenge host or a 404 elsewhere is never the link
    code, ex, final = ask('https://' + s)
    if answered(code, ex): return final, code, ex          # where it ended up, when it answered (#120)
    hcode, hex_, hfinal = ask('http://' + s)
    if hex_ == 0: return hfinal, hcode, hex_   # only a clean http answer replaces https (a redirect that then fails doesn't; Pass 3)
    return 'https://' + s, code, ex


def check(item, wait=5):
    ch, v = item
    s = v['site'].split('@')[-1]  # the guide lists one email address as a "website"; link its domain
    url, code, ex = once(s)
    if broken(code, ex):
        time.sleep(wait); url, code, ex = once(s)
    return ch, url, code, ex


def digest(r):
    """The sites checked and what each check found, as one value: a result edited by hand after the check no longer
    matches (Pass 1)."""
    sites = {ch: [v['site'], v.get('url'), str(v.get('http')), v.get('curl')] for ch, v in r.items() if v.get('site')}
    return hashlib.sha256(json.dumps(sites, ensure_ascii=False, sort_keys=True).encode('utf-8')).hexdigest()


def stale(r, stamp):
    """Why the recorded results can't be used, or None. They must come from a run with today's rule, over today's list of
    sites, and be complete: every site has a status, and every site that never answered ('000') has curl's exit code,
    which this checker always records (round-2 audit #2: the shipped data, from Oct 14, had none)."""
    if not stamp: return 'no record of a check (data/sites_checked.json)'
    if stamp.get('rule') != RULE: return f"checked with rule {stamp.get('rule')}, and the rule is now {RULE}"
    if stamp.get('sites') != digest(r): return 'the sites, or their results, changed after the check'
    miss = sorted(ch for ch, v in r.items() if v.get('site') and ('http' not in v or (str(v['http']) == '000' and 'curl' not in v)))
    return f'no complete result for {miss[:5]}' if miss else None


def proxied(env=os.environ):
    return sorted(k for k in env if k.lower() in ('https_proxy', 'http_proxy', 'all_proxy') and env[k])


if __name__ == '__main__':
    if proxied() and '--behind-proxy' not in sys.argv[1:]:
        sys.exit(f"not checking: {', '.join(proxied())} is set, and a proxy's failures look like broken sites. "
                 "Run it from an ordinary connection (or pass --behind-proxy if you're sure).")
    r = json.load(open(P, encoding='utf-8'))
    items = [(ch, v) for ch, v in r.items() if v.get('site')]
    with cf.ThreadPoolExecutor(12) as pool:
        for ch, url, code, ex in pool.map(check, items):
            r[ch]['url'], r[ch]['http'] = url, code
            if ex: r[ch]['curl'] = ex
            else: r[ch].pop('curl', None)
            if ex or not code.startswith(('2', '3')): print('not 2xx/3xx:', ch, url, code, f'(curl exit {ex}' + (f': {BROKEN_EXIT[ex]})' if ex in BROKEN_EXIT else ')') if ex else '')
    json.dump(r, open(P, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    if proxied():   # --behind-proxy: results, but no stamp (Pass 1), so build_learn.py stops until a run from an ordinary connection
        STAMP.unlink(missing_ok=True); print('behind a proxy: no stamp written; build_learn.py will stop until a check from an ordinary connection')
    else:
        json.dump({'rule': RULE, 'checked': datetime.date.today().isoformat(), 'sites': digest(r)}, open(STAMP, 'w'), indent=1)
    print(len(items), 'sites checked')
