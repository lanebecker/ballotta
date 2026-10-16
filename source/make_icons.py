"""Draw the Home Screen icons from the Ballotta logo (favicon.svg's shapes), with Chromium. Run from the repo root:
    python3 source/make_icons.py
Writes icon-192.png, icon-512.png (logo at 62% of the height) and icon-maskable-512.png (logo inside the middle 70%,
so a phone's round or squircle mask never clips it): a plum square, the gold sun, the porch-light bowl."""
import pathlib
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


with sync_playwright() as p:
    b = p.chromium.launch()
    for name, size, share in (('icon-192.png', 192, .62), ('icon-512.png', 512, .62), ('icon-maskable-512.png', 512, .5)):
        pg = b.new_page(viewport={'width': size, 'height': size})
        pg.set_content(page(size, share))
        pg.screenshot(path=str(ROOT / name), clip={'x': 0, 'y': 0, 'width': size, 'height': size})
        pg.close()
        print(name)
    b.close()
