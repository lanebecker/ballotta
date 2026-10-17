"""Travis County's consolidated ("bedsheet") ballot PDF as one stream of lines, in reading order: page by page, and on
each page its four columns left to right, top to bottom. Each word is marked Spanish (the ballot sets Spanish in
italic) or English (upright), and bold or not. The ballot is the source of truth for what Ballotta shows: the answer
key's measure texts come from here, and tests/test_pipeline.py checks every contest's choice order against it.

    python3 source/ballot/pdf_lines.py 10 3      # print page 10, column 4 (0-based), with e/B/s tags per word
"""
import pathlib, re

import pdfplumber

PDF = pathlib.Path(__file__).resolve().parent / 'bedsheet.pdf'
COLS = (0, 200, 395, 590, 10_000)  # x0 boundaries of the four columns (the page is 792pt wide, columns ~190pt)


def lines(path=PDF):
    out = []
    with pdfplumber.open(path) as pdf:
        for pn, page in enumerate(pdf.pages, 1):
            words = page.extract_words(extra_attrs=['fontname'])
            for ci in range(4):
                ws = sorted((w for w in words if COLS[ci] <= w['x0'] < COLS[ci + 1]), key=lambda w: (round(w['top']), w['x0']))
                cur, top = [], None
                for w in ws:
                    if cur and abs(w['top'] - top) > 2.5:   # a new line
                        out.append(_line(pn, ci, cur)); cur = []
                    if not cur: top = w['top']
                    cur.append(w)
                if cur: out.append(_line(pn, ci, cur))
    return out


def _line(pn, ci, ws):
    ws = sorted(ws, key=lambda w: w['x0'])
    return {'page': pn, 'col': ci, 'top': round(ws[0]['top'], 1), 'text': ' '.join(w['text'] for w in ws),
            'words': [(w['text'], 'Italic' in w['fontname'], 'Bold' in w['fontname']) for w in ws]}


def english(l): return all(not it for _, it, _ in l['words'])
def bold(l): return all(b for _, it, b in l['words'] if not it)
def norm(s): return re.sub(r'\s+', ' ', s).strip()


def measures(L=None):
    """Every measure on the ballot, in ballot order: (bold English title line ending "Proposition X", its English
    text). The text is every upright, non-bold line after the title, up to the first line with Spanish in it (the
    Spanish caption that starts the translation)."""
    L = L if L is not None else lines()
    out = []
    for i, l in enumerate(L):
        if english(l) and bold(l) and re.search(r'Proposition\s+[A-Z0-9]+$', l['text']):
            j, block = i + 1, []
            while j < len(L) and english(L[j]) and not bold(L[j]):
                block.append(L[j]['text']); j += 1
            out.append((l['text'], norm(' '.join(block))))
    return out


if __name__ == '__main__':
    import sys
    for l in lines():
        if l['page'] == int(sys.argv[1]) and l['col'] == int(sys.argv[2]):
            print(l['top'], ''.join('s' if it else ('B' if b else 'e') for _, it, b in l['words'])[:10].ljust(10), l['text'])
