"""Draw the Home Screen icons from the Ballotta logo (favicon.svg's shapes), with Chromium. Run from the repo root:
    python3 source/make_icons.py          # the icons
    python3 source/make_icons.py --og     # and the link-preview card, og.png, from source/og.html
Writes icon-192.png, icon-512.png (logo at 62% of the height) and icon-maskable-512.png (logo inside the middle 70%,
so a phone's round or squircle mask never clips it): a plum square, the gold sun, the porch-light bowl.
og.png (1200x630) is source/og.html as Chromium draws it (#85: the Oct 13 card had no source; og.html was fitted to it
on Oct 18, matching it but for anti-aliasing in the wordmark, and og.png was redrawn from it)."""
import hashlib, pathlib, struct, sys, zlib
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent
LOGO = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 86 104" width="{w}" height="{h}">'
        '<circle cx="43" cy="22" r="18" fill="#E9A92A"/>'
        '<path d="M8 52 C8 86 26 98 43 98 C60 98 78 86 78 52" fill="none" stroke="#FFF9F1" stroke-width="8" stroke-linecap="round"/>'
        '<path d="M2 52 H84" stroke="#FFF9F1" stroke-width="8" stroke-linecap="round"/></svg>')


def page(size, share):
    h = round(size * share); w = round(h * 86 / 104)
    return ('<!doctype html><html><body style="margin:0;width:%dpx;height:%dpx;background:#4B2A6B;display:flex;'
            'align-items:center;justify-content:center">%s</body></html>') % (size, size, LOGO.format(w=w, h=h))


OG_FROM = ('source/og.html', 'fonts/ZillaSlab-SemiBold.woff2', 'fonts/ZillaSlab-Bold.woff2', 'fonts/PublicSans-wght.woff2')


def og_source():
    """sha256 of everything og.png is drawn from. og.png carries it, so a test can tell on any machine whether the card
    still matches its source (Pass 2: pixels differ by thousands between font renderers)."""
    h = hashlib.sha256()
    for f in OG_FROM:
        h.update(f.encode() + b'\0' + (ROOT / f).read_bytes())
    return h.hexdigest()


def png_text(png):
    """The tEXt chunks of a PNG, as {keyword: text}."""
    out, i = {}, 8
    while i < len(png):
        n, kind = struct.unpack('>I4s', png[i:i + 8])
        if kind == b'tEXt':
            k, _, v = png[i + 8:i + 8 + n].partition(b'\0'); out[k.decode('latin-1')] = v.decode('latin-1')
        i += 12 + n
    return out


def og(browser):
    """The link-preview card as PNG bytes, drawn from source/og.html with its own fonts, carrying og_source()."""
    pg = browser.new_page(viewport={'width': 1200, 'height': 630})
    pg.goto((ROOT / 'source/og.html').as_uri()); pg.evaluate('document.fonts.ready'); pg.wait_for_timeout(200)
    png = pg.screenshot(clip={'x': 0, 'y': 0, 'width': 1200, 'height': 630}); pg.close()
    data = b'ballotta-source\0' + og_source().encode()
    chunk = struct.pack('>I', len(data)) + b'tEXt' + data + struct.pack('>I', zlib.crc32(b'tEXt' + data))
    end = png.rindex(b'IEND') - 4                            # before the IEND chunk's length field
    return png[:end] + chunk + png[end:]


if __name__ == '__main__':
    with sync_playwright() as p:
        b = p.chromium.launch()
        for name, size, share in (('icon-192.png', 192, .62), ('icon-512.png', 512, .62), ('icon-maskable-512.png', 512, .5)):
            pg = b.new_page(viewport={'width': size, 'height': size})
            pg.set_content(page(size, share))
            pg.screenshot(path=str(ROOT / name), clip={'x': 0, 'y': 0, 'width': size, 'height': size})
            pg.close()
            print(name)
        if '--og' in sys.argv[1:]:
            (ROOT / 'og.png').write_bytes(og(b)); print('og.png')
        b.close()
