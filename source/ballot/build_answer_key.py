"""Turn parsed.json into the reviewed answer key for the Nov 3, 2026 Travis County ballot (source/answer_key.json).

    python3 source/ballot/build_answer_key.py [--out PATH]      # from any folder; tests/test_pipeline.py checks that
                                                                 # this reproduces the committed key byte for byte
Every correction lives here, not in the JSON (cold audit, Oct 17, #3): the Oct 14 corrected ballot's changes, the
choice order of the "vote for up to N" contests (#1), and the measure texts, which come straight from the ballot PDF's
English text (#2: a parsed text could carry the start of the Spanish caption).

parsed.json is a FROZEN SNAPSHOT (#55): parse_ballot.py made it from the Sep 30 PDF using a hand-made column extraction
that was never committed, so it can't be regenerated. What guards it is tests/test_pipeline.py, which checks the key this
script writes against the corrected Oct 14 PDF (choice order, measure texts line by line, party labels, count of
measures). Building the key straight from the PDF instead is issue #97, after the election."""
import hashlib, json, pathlib, re, sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import pdf_lines

OUT = pathlib.Path(sys.argv[sys.argv.index("--out") + 1]) if "--out" in sys.argv else HERE.parent / "answer_key.json"
src = json.load(open(HERE / "parsed.json", encoding="utf-8"))
contests = src["contests"]

DROP = {
    "District, School Board Trustee Election",
    "School District, School Board Trustee Election",
    "District School Board Trustee, Special Election: Rhonda Suzanne",
    "Manor ISD Board of Trustees, Place 1: Stephanie Rodriguez Manor ISD Board of Trustees, Place 2: LaKesha Small Manor ISD Board of Trustees, Place 3: Ana Cortez Manor ISD Board of Trustees, Place 4: Fabian Martinez",
    "Directors",  # handled by explicit additions below
    "Eastwood MUD Directores",
    "Permanent Directors Kennedy Hill MUD Directores",
    "Northtown MUD Directors",
    "Northtown MUD Directores",
    "Permanent Directors",
    "Board of Directors, Three Places",
    "Services District 4 Expansion of the District Territory",
    "Library District Board of Trustees",
    "District Board of Trustees",
    "Travis County, Board of Directors",  # Hidden Lakes MUD board, re-added below
    "Council Member Seats",
    "Village of Volente, Village Council",
}
RENAME = {
    "Travis County, Board of Directors, Place 1": "Travis Central Appraisal District, Board of Directors, Place 1",
    "Travis County, Board of Directors, Place 2": "Travis Central Appraisal District, Board of Directors, Place 2",
    "Travis County, Board of Directors, Place 3": "Travis Central Appraisal District, Board of Directors, Place 3",
    "Judge, Court of Criminal Appeals Place 3": "Judge, Court of Criminal Appeals, Place 3",
    "Judge, Court of Criminal Appeals Place 4": "Judge, Court of Criminal Appeals, Place 4",
    "Judge, Court of Criminal Appeals Place 9": "Judge, Court of Criminal Appeals, Place 9",
    "County Constable, Precinct 4 – Unexpired Term": "County Constable, Precinct 4 (Unexpired Term)",
    "Justice, Supreme Court, Place 2 – Unexpired Term": "Justice, Supreme Court, Place 2 (Unexpired Term)",
}
FIX_CHOICES = {
    "State Representative, District 50": ["Howard Olsen (REP)", "Samantha Lopez-Resendez (DEM)"],
    "Judge, County Court at Law No. 1": ["Todd Wong (DEM)"],
    "County Judge": ["Andy Brown (DEM)"],
    "City of Sunset Valley, Mayor": ["Marc Bruner"],
    "District Judge, 331st Judicial District": ["Chantal Melissa Eldridge (DEM)"],  # the Oct 14 corrected ballot adds the party
}
# Contests the parser could not read. Choices in the order the ballot prints them, top to bottom (Oct 17, #1: the ten
# "vote for up to N" lists were first typed in a column extraction's order, which split each list in two).
ADD = [
    ("City of Sunset Valley, Two City Council Member Seats (vote for up to 2)", "candidate", ["Sarah Ponder", "Robert Johnson", "Charles Young"], "City of Sunset Valley, Mayor"),
    ("Village of Volente, Village Council (vote for up to 2)", "candidate", ["Eric Peeters", "Tony Ruff"], "Village of Volente, Village Mayor"),
    ("Eastwood MUD Permanent Directors (vote for up to 5)", "candidate", ["Grant Ballew", "John Berry", "Carrington Saathoff", "Ryan Sullivan", "William Waller"], "Eastwood MUD Proposition G"),
    ("Hidden Lakes MUD No. 1 of Travis County, Board of Directors (vote for up to 5)", "candidate", ["Jeff Markey", "Mariano Ravelo", "Nicodemus Abowd", "Denis Fletcher", "Barry Marotz"], "Hidden Lakes MUD No. 1 Proposition J"),
    ("Kennedy Hill MUD Permanent Directors (vote for up to 5)", "candidate", ["Jacob Clark", "Ross Hamilton", "Daniel McElrath", "Chase Nixon", "Dane Rymer"], "Kennedy Hill MUD Proposition G"),
    ("Northtown MUD Directors (vote for up to 3)", "candidate", ["R. Lee Hill", "Chris Capers", "Scott Moser", "Brenda Vrabel"], "North Austin MUD No. 1 Director, Place 4"),
    ("Travis County MMD No. 1 Permanent Directors (vote for up to 5)", "candidate", ["Mickey Jamail", "Daniel Kavelman", "Felicity Maxwell", "Casey Paulson", "Ryan Puzycki"], "Travis County MMD No. 1 Proposition F"),
    ("Travis County MUD No. 41 Permanent Directors (vote for up to 5)", "candidate", ["Ashtyn Bogue", "Lyndsey Mylius", "Jason Nobbe", "Kelly Schill", "Jared Williams"], "Travis County MUD No. 41 Proposition F"),
    ("Williamson-Travis Counties MUD No. 1 Directors (vote for up to 3)", "candidate", ["Hanoi Avila", "David Flores", "Beth Jones", "Stephen Bodnarchuk Jr.", "Kimberly Massaro", "Linda Fabre", "Thomas Vacek"], "Vista MUD of Travis County Proposition B"),
    ("Cypress Ranch WCID No. 1, Board of Directors (vote for up to 3)", "candidate", ["Rick Shute", "Jason Blair", "Richard Kenyon", "Travis Wright"], "Williamson-Travis Counties MUD No. 1 Directors (vote for up to 3)"),
    ("Travis County WCID No. 17 Directors (vote for up to 3)", "candidate", ["Phil Han", "Sonja DeLaFuente", "Elicia Michaud", "Larry Harlan", "Ryan Carretta"], "Cypress Ranch WCID No. 1, Board of Directors (vote for up to 3)"),
    ("Wells Branch Community Library District Board of Trustees (vote for up to 3)", "candidate", ["Philip Waters", "Abigail Joffrain", "Rudolf J. Valenti", "Paul Wadehra", "Elizabeth Martin"], None),
]

JUNK = re.compile(
    r"^(\d+|Travis Central Appraisal.*|District, Travis County,|City of [A-Za-z ]+|Austin Community College|"
    r".*Independent( School)?,?|District Voter.*|School District Voter.*|Hero Way West Municipal|"
    r"Kennedy Hill M.*|North Austin Municip.*|Northtown Municipal.*|Travis Coun.*|Cypress Ranc.*|"
    r"or five|o cinco|four or five|cuatro o cinco|Municipal,?|Austin, Elecciones.*|Del Valle, Elecciones.*|"
    r"Two City|City of Sunset Valley Special|Dunlop Coupland Independent)$"
)

def level_of(title):
    t = title
    if t.startswith("United States"):
        return "Federal"
    if re.search(r"Proposition", t):
        return "Measure"
    if re.match(r"(Governor|Lieutenant Governor|Attorney General|Comptroller|Commissioner of|Railroad|Chief Justice, Supreme|Justice, Supreme|Judge, Court of Criminal|Member, State Board|State Senator|State Representative|Chief Justice, 15th|Justice, 15th|Chief Justice, 3rd)", t):
        return "State"
    if t.startswith("District Judge"):
        return "Courts"
    if re.match(r"(County|Judge, County Court|Judge, Probate|District Clerk|Justice of the Peace|Travis Central Appraisal)", t):
        return "County"
    if re.match(r"(City of|Village of)", t):
        return "City"
    if re.search(r"(ISD|ACC|Community College)", t):
        return "School"
    return "Special district"

def entity_of(title, level):
    if level in ("Federal", "State", "Courts"):
        return level
    if level == "County":
        return "Travis Central Appraisal District" if "Appraisal" in title else "Travis County"
    m = re.match(r"(City of [A-Za-z ]+?|Village of [A-Za-z]+)(,| Proposition)", title)
    if m:
        return m.group(1)
    if title.startswith("ACC") or "Community College" in title:
        return "Austin Community College"
    m = re.match(r"(Austin ISD|Del Valle ISD|Leander ISD|Manor ISD|Pflugerville ISD|Round Rock ISD|Coupland ISD)", title)
    if m:
        return m.group(1)
    if title.startswith("Round Rock Independent School District"):
        return "Round Rock ISD"
    m = re.match(r"(.+?(MUD|MMD|WCID|ESD)( No\.\s?\d+)?( of Travis County)?)\b", title)
    if m:
        return m.group(1).replace("No.41", "No. 41")
    if "Wells Branch" in title:
        return "Wells Branch Community Library District"
    return title

final = []
for c in contests:
    t = c["title"]
    if t in DROP:
        continue
    t = RENAME.get(t, t)
    if t == "Round Rock Independent School District Proposition A":
        t = "Round Rock ISD Proposition A"
    if c["type"] == "candidate":
        for x in c["choices"]:
            if JUNK.match(x) and t not in FIX_CHOICES:
                print(f"dropped from {t!r}: {x!r}", file=sys.stderr)  # never silently (#5)
        ch = FIX_CHOICES.get(t) or [x for x in c["choices"] if not JUNK.match(x)]
        ch = [x for x in ch if x != "Write-in"] + (["Write-in"] if "Write-in" in c["choices"] else [])
    else:
        ch = ["FOR", "AGAINST"]
    item = {"title": t, "type": c["type"], "choices": ch}
    if c["type"] == "measure":
        item["text"] = c.get("text", "")
    final.append(item)

# Disambiguate the duplicate ESD 9 / ESD 10 elections (two voter groups each)
seen = {}
for it in final:
    if it["title"] in seen:
        seen[it["title"]] += 1
        if "ESD No. 9" in it["title"]:
            it["title"] += " (territory to be annexed)"
        elif "ESD No. 10" in it["title"]:
            it["title"] += " (second ballot version)"
    else:
        seen[it["title"]] = 1
for it in final:
    if "ESD No. 9" in it["title"] and seen.get(it["title"]) == 2 and "territory" not in it["title"]:
        it["title"] += " (current district)"

# Insert additions after their anchor
for title, typ, ch, after in ADD:
    item = {"title": title, "type": typ, "choices": ch}
    idx = len(final)
    if after:
        for k, it in enumerate(final):
            if it["title"] == after:
                idx = k + 1
    final.insert(idx, item)

for k, it in enumerate(final):
    it["id"] = f"c{k+1:03d}"
    it["level"] = level_of(it["title"]) if it["type"] == "candidate" else "Measure"
    it["entity"] = entity_of(it["title"], level_of(it["title"]) if it["type"] == "candidate" else
                             ("County" if "Appraisal" in it["title"] else "x"))
    if it["type"] == "measure":
        it["entity"] = entity_of(it["title"], "x")

for it in final:
    it["entity"] = it["entity"].replace("Hidden Lakes MUD No. 1 of Travis County", "Hidden Lakes MUD No. 1")

# Measure entity cleanup
for it in final:
    if it["type"] == "measure":
        e = it["title"].split(" Proposition")[0]
        e = e.replace("Austin Community College District", "Austin Community College")
        it["entity"] = e
        lvl = "City" if e.startswith(("City of", "Village of")) else (
              "School" if ("ISD" in e or "Community College" in e) else "Special district")
        it["level"] = lvl
        it["kind"] = "measure"

# Measure texts exactly as the ballot prints them in English, from the PDF in this folder (the Oct 14 corrected ballot):
# the measures appear in the same order in both, and each pair's "Proposition X" must agree.
pdf_measures = pdf_lines.measures()
key_measures = [it for it in final if it["type"] == "measure"]
assert len(pdf_measures) == len(key_measures), (len(pdf_measures), len(key_measures))
for (ptitle, ptext), it in zip(pdf_measures, key_measures):
    letter = lambda t: re.search(r"Proposition\s+([A-Z0-9]+)", t).group(1)
    assert letter(ptitle) == letter(it["title"]), (ptitle, it["title"])
    assert ptext, it["title"]
    if pdf_lines.norm(it["text"]) != ptext:
        print(f"{it['id']} text from the PDF (parsed: …{pdf_lines.norm(it['text'])[-40:]!r})", file=sys.stderr)
    it["text"] = ptext

key = {
    "election": "Travis County Joint General and Special Elections, November 3, 2026",
    # The county's corrected bedsheet ballot (Oct 14), as kept in this repo: the URL it was first noted under no longer
    # answers (404, Oct 17), so the record is the file itself and its fingerprint (wave 1 audit).
    "source": "source/ballot/bedsheet.pdf (Travis County Clerk, votetravis.gov: consolidated ballot, corrected Oct 14, 2026)",
    "source_sha256": hashlib.sha256(pdf_lines.PDF.read_bytes()).hexdigest(),
    "source_corrected": "2026-10-14",
    "source_note": "Consolidated ('bedsheet') ballot listing every contest in the county. No single voter sees all of these; each ballot is a subset by precinct.",
    "unopposed_not_on_ballot": [
        "Coupland ISD trustees (declared elected unopposed)",
        "Manor ISD Board of Trustees, Places 1-4 (declared elected unopposed)",
    ],
    "contests": final,
}
json.dump(key, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
from collections import Counter
print(len(final), "contests")
print(Counter((it["level"], it["type"]) for it in final))
for it in final:
    print(it["id"], it["level"][:8], "|", it["entity"], "|", it["title"], "|", ", ".join(it["choices"])[:90])
