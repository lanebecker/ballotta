"""Build the Ballotta site from template-travis.html and the routing data.

    python3 source/build_site.py             # index.html: the live site
    python3 source/build_site.py --preview   # next/index.html: the same page with the laptop layout on; counts nothing

Rebuild rules first if the answer key or district data change:  python3 source/build_rules.py
"""
import json, re, pathlib, sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
# Public address of the site.
BASE_URL = "https://ballotta.org/"
# Umami Cloud website ID (anonymous, cookieless counts). Empty string = no analytics script at all.
UMAMI_ID = "51b98962-382e-4070-bbd0-f43aba4143ae"
# Hostnames whose visits count; anything else (local test runs, previews) is ignored by the tracker.
UMAMI_DOMAINS = "ballotta.org,www.ballotta.org,lanebecker.github.io"
# The laptop layout (1024px and wider) is marked in the template: /*DESK*/ ... /*/DESK*/ in CSS and JS,
# <!--DESK--> ... <!--/DESK--> in HTML. Until Lane approves the preview at ballotta.org/next/, the live build
# removes every marked block, so index.html stays byte-for-byte what it was. Promotion: set DESK_LIVE = True.
DESK_LIVE = True

OPEN, CLOSE = r'(?:/\*DESK\*/|<!--DESK-->)', r'(?:/\*/DESK\*/|<!--/DESK-->)'


ALONE_OPEN, ALONE_CLOSE = re.compile(r'[ \t]*' + OPEN + r'[ \t]*'), re.compile(r'[ \t]*' + CLOSE + r'[ \t]*')


def strip_desk(html):
    """Remove every laptop-layout block. A marker alone on its line (spaces or tabs around it, nothing else) opens or
    closes a block of whole lines; a marker pair inside a line removes just the text between and including them.
    One loop both checks and removes; a marker that is neither alone nor in a one-line pair stops the build."""
    opens, closes = len(re.findall(OPEN, html)), len(re.findall(CLOSE, html))
    assert opens == closes, f"DESK markers unpaired: {opens} open, {closes} close"
    out, in_block = [], False
    for n, line in enumerate(html.split('\n'), 1):
        if ALONE_OPEN.fullmatch(line):
            assert not in_block, f"line {n}: a DESK block opens inside another (is a closing marker sharing its line?)"
            in_block = True
        elif ALONE_CLOSE.fullmatch(line):
            assert in_block, f"line {n}: a DESK block closes without opening"
            in_block = False
        elif not in_block:
            out.append(line)
        else:
            assert not re.search(OPEN + '|' + CLOSE, line), f"line {n}: a DESK marker inside a block isn't alone on its line"
    assert not in_block, "a DESK block is never closed (is its closing marker sharing its line with other characters?)"
    html = re.sub(OPEN + r'[^\n]*?' + CLOSE, '', '\n'.join(out))
    assert not re.search(OPEN + '|' + CLOSE, html), "a DESK marker survived stripping"
    return html


def build(preview=False, desk=None):
    """desk: include the laptop layout (default: on for the preview, or once DESK_LIVE). The phone-parity test builds both."""
    key = json.load(open(HERE / "answer_key.json", encoding="utf-8"))
    rules = json.load(open(HERE / "rules.json"))
    tlc = json.load(open(HERE / "tlc_precincts.json"))
    contests = [{k: c[k] for k in ("id", "title", "type", "choices", "level", "entity")}
                | ({"text": c.get("text", "")} if c["type"] == "measure" else {})
                for c in key["contests"]]
    learn = json.load(open(HERE / "learn.json", encoding="utf-8"))      # built by build_learn.py
    sites = json.load(open(HERE / "vote_sites.json", encoding="utf-8"))  # Travis County Clerk site lists, geocoded
    data = json.dumps({"contests": contests, "rules": rules, "tlc": tlc, "learn": learn, "sites": sites}, ensure_ascii=False)
    data = data.replace("</", "<\\/")  # never let data close the inline <script>
    html = (HERE / "template-travis.html").read_text(encoding="utf-8")
    if not (desk if desk is not None else (preview or DESK_LIVE)):
        html = strip_desk(html)
    html = html.replace("__DATA__", data)

    # Self-hosted fonts: the only third-party requests are the county and Census lookups.
    fonts = ("<style>@font-face{font-family:'Zilla Slab';src:url('fonts/ZillaSlab-SemiBold.woff2') format('woff2');font-weight:600;font-display:swap}"
             "@font-face{font-family:'Zilla Slab';src:url('fonts/ZillaSlab-Bold.woff2') format('woff2');font-weight:700;font-display:swap}"
             "@font-face{font-family:'Public Sans';src:url('fonts/PublicSans-wght.woff2') format('woff2');font-weight:100 900;font-display:swap}</style>")
    html = re.sub(r"<!--FONTS-->.*?<!--/FONTS-->", fonts, html, flags=re.S).replace("__OG_IMAGE__", BASE_URL + "og.png")
    # Analytics: no URL search or #fragment is ever sent (the fragment is also stripped before this script loads).
    # The tracker is a pinned copy of https://cloud.umami.is/script.js (umami.js, fetched 2026-10-14) served from this
    # site, so a change on Umami's side can never run new code on this page. It still reports to gateway.umami.is.
    analytics = (f'<script defer src="umami.js" data-website-id="{UMAMI_ID}" '
                 f'data-domains="{UMAMI_DOMAINS}" data-exclude-search="true" data-exclude-hash="true" '
                 # The privacy firewall in the page checks every payload; Do Not Track is honoured twice (here and there);
                 # page-speed measurements (load time, responsiveness) carry no personal data (Lane, Oct 15).
                 f'data-do-not-track="true" data-before-send="ballottaBeforeSend" data-performance="true"></script>') if UMAMI_ID else ""
    # Fail closed: until the page's own check is defined, the tracker's before-send drops everything.
    if analytics: analytics = '<script>window.ballottaBeforeSend = () => null;</script>' + analytics
    if preview:
        # The preview lives one folder down (next/index.html). It loads the same pinned tracker, so it behaves like the
        # live page, but with a domain list no real site matches: the tracker then never sends anything.
        if analytics:
            analytics = analytics.replace('src="umami.js"', 'src="../umami.js"').replace(f'data-domains="{UMAMI_DOMAINS}"', 'data-domains="preview.invalid"')
            assert 'preview.invalid' in analytics and '../umami.js' in analytics
        html = html.replace("<title>Ballotta ·", "<title>[Preview] Ballotta ·", 1)
        for a, b in [("url('fonts/", "url('../fonts/"), ('href="favicon.svg"', 'href="../favicon.svg"'),
                     ('href="apple-touch-icon.png"', 'href="../apple-touch-icon.png"')]:
            assert a in html, a
            html = html.replace(a, b)
    return html.replace("<!--ANALYTICS-->", analytics)


if __name__ == "__main__":
    preview = "--preview" in sys.argv[1:]
    if preview and DESK_LIVE:
        print("The laptop layout is live, and next/index.html is a redirect to the main page: not overwriting it.")
        sys.exit(0)  # not an error, so `--preview && build_site.py` still builds the live page (Pass 2)
    html = build(preview)
    out = ROOT / ("next/index.html" if preview else "index.html")
    out.parent.mkdir(exist_ok=True)
    out.write_text(html, encoding="utf-8")
    print(out.relative_to(ROOT).as_posix(), len(html) // 1024, "KB")
