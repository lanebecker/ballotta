"""Parse Travis County's Nov 3, 2026 consolidated ballot (column-extracted text)
into a JSON answer key: sections (jurisdiction elections) -> contests -> choices.

Heuristic parser; output is reviewed by hand afterwards.

KEPT AS A RECORD; IT CAN'T BE RERUN FROM THIS REPO (#55). It read cols/p*_c*.txt, per-column text extracted by hand
from the Sep 30 ballot PDF and never committed. Its output, parsed.json, is a frozen snapshot: build_answer_key.py
applies the Oct 14 corrections to it, and tests/test_pipeline.py checks the finished key against the corrected PDF.
Replacing this step with a parser over pdf_lines.py is issue #97, after the election.
"""
import glob, json, re, sys

COLS = sorted(glob.glob("cols/p*_c*.txt"))

BOILER = re.compile(
    r"^(Travis County Joint Gen|Elecciones Generales y Espec|November 3, 2026|3 de noviembre de 2026|"
    r"neral and Special Elections|ciales Conjuntas del Condado|To view your sample|Para ver su boleta|"
    r"Page \d+|avis$|allot visit|estra visite|\d+ of 18|Contests continue|on next page|"
    r"Party Legend|Leyenda de Partidos|Republican = |Democrat = |Libertarian = |Green = |"
    r"Republicano = |Demócrata = |Libertario = |Verde = )"
)

SPANISH_START = re.compile(
    r"^(Senador|Representante|Gobernador|Procurador|Contralor|Comisionado|Juez|Miembro|Secretario|"
    r"Tesorero|Alguacil|Elecci[oó]n|Elecciones|Ciudad|Distrito|Pueblo|Oficinas|Municipal,|Lugar|"
    r"Posici[oó]n|Duraci[oó]n|N[uú]m|Condado|Candidatos|Escolar|Vote por|Vota por|Directores|"
    r"Permanentes|Mantenimiento|Bonos|Instalaciones|Reembolso|P[uú]blicos|Municipales|Sistema|"
    r"Confirmaci[oó]n|Junta|Consejo|Concejo|Mesa|Independiente|Enmienda|Constitucional|Tasa|"
    r"Impuestos|Votantes|Aprobaci[oó]n|Ratificaci[oó]n|del |de la |de |Tierras|Apelaciones|"
    r"Educaci[oó]n|Tasaci[oó]n|Facultades|Anexi[oó]n|Comit[eé]s|Deberes|Gesti[oó]n|Seguridad|"
    r"Servicios|Emergencia|Hospital|Desarrollo|Agua|Lugar Núm)"
)
SPANISH_ANY = re.compile(
    r"(Núm|Propuesta|Proposición|Consejo Escolar|Concejo|Mesa Directiva|Directores Permanentes|"
    r"Junta Directiva|Distrito Uninominal|Puesto \d|Lugar \d|Escaños|Alcalde|Elección|ninguno)"
)

SECTION_HINT = re.compile(r"(Election|Elections|Offices|Declared Elected|Unopposed)", re.I)

OFFICE_WORDS = re.compile(
    r"(Senator|Representative|Governor|Attorney General|Comptroller|Commissioner|Justice|Judge|"
    r"Member|Clerk|Treasurer|Constable|Sheriff|Trustee|Trustees|Director|Directors|Mayor|Council|"
    r"Board|Place \d|Position \d|Precinct|District \d|Court|Seats|Unexpired|Railroad|Education|"
    r"Appeals|Proposition|Land Office|Agriculture|Chief Justice|At-Large|Commission)"
)

def load_lines():
    out = []
    for f in COLS:
        for raw in open(f, encoding="utf-8"):
            s = raw.strip()
            if not s or BOILER.match(s):
                continue
            out.append((f, s))
    return out


def is_spanish(s):
    return bool(SPANISH_START.match(s) or SPANISH_ANY.search(s))


def main():
    lines = load_lines()
    sections, contests = [], []
    cur_section = None
    i = 0
    n = len(lines)
    while i < n:
        f, s = lines[i]
        # Measures: English line naming a Proposition
        m = re.search(r"Proposition\s+([A-Z0-9]+)\s*$", s)
        if m and not is_spanish(s):
            title = s
            if s.startswith("Proposition") or s.startswith("District Proposition"):
                title = lines[i - 1][1] + " " + s
            # collect English text until Spanish title line
            j = i + 1
            text = []
            while j < n and not re.search(r"(Propuesta|Proposición)", lines[j][1]):
                text.append(lines[j][1])
                j += 1
            # skip until AGAINST line
            while j < n and not lines[j][1].startswith("AGAINST"):
                j += 1
            contests.append({"section": cur_section, "title": title, "type": "measure",
                             "text": " ".join(text), "choices": ["FOR", "AGAINST"], "src": f})
            i = j + 1
            continue
        # English block followed by Spanish => section header or candidate contest title
        if not is_spanish(s) and OFFICE_WORDS.search(s) or SECTION_HINT.search(s) and not is_spanish(s):
            eng = [s]
            j = i + 1
            while j < n and not is_spanish(lines[j][1]) and not re.search(r"\((REP|DEM|LIB|GRN)\)", lines[j][1]) \
                    and len(eng) < 12 and (OFFICE_WORDS.search(lines[j][1]) or SECTION_HINT.search(lines[j][1])
                                           or lines[j][1][:1].islower() or len(lines[j][1].split()) <= 3 and
                                           eng[-1].endswith((",", "-", "Utility", "Municipal", "School", "Independent",
                                                             "Community", "Appraisal", "Judicial", "of", "Court of",
                                                             "the", "Management", "Board of", "Council", "City",
                                                             "Two City", "Village", "Regular", "General")) ):
                eng.append(lines[j][1])
                j += 1
            title = " ".join(eng).replace(" - ", " – ")
            # skip Spanish block
            while j < n and is_spanish(lines[j][1]):
                j += 1
            if SECTION_HINT.search(title) and not re.search(r"(Member|Trustee|Director|Judge|Justice|Senator|Representative|Governor|Mayor)\b", title.split(" Election")[0][-40:]) and ("Election" in title or "Offices" in title or "Elected" in title):
                cur_section = title
                sections.append(title)
                i = j
                continue
            # candidate contest: collect choice lines
            choices = []
            while j < n:
                t = lines[j][1]
                if t.startswith("Write-in"):
                    choices.append("Write-in"); j += 1; continue
                if is_spanish(t) and not re.search(r"\((REP|DEM|LIB|GRN)\)", t):
                    j += 1; continue
                if re.search(r"Proposition\s+[A-Z0-9]+\s*$", t):
                    break
                if OFFICE_WORDS.search(t) and not re.search(r"\((REP|DEM|LIB|GRN)\)", t):
                    break
                if SECTION_HINT.search(t):
                    break
                if t.startswith(("Vote for", "Vota por")):
                    j += 1; continue
                choices.append(t)
                j += 1
            contests.append({"section": cur_section, "title": title, "type": "candidate",
                             "choices": choices, "src": f})
            i = j
            continue
        i += 1

    json.dump({"sections": sections, "contests": contests}, open("parsed.json", "w"), ensure_ascii=False, indent=1)
    for c in contests:
        print(f"[{c['src'][5:12]}] {c['type'][:4]} | {c['title']} | {', '.join(c['choices'])[:120]}")
    print(len(contests), "contests;", len(sections), "sections", file=sys.stderr)


if __name__ == "__main__":
    main()
