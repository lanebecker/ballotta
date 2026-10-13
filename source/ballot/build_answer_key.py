"""Turn parsed.json into a reviewed answer key for the Nov 3, 2026 Travis County ballot."""
import json, re

src = json.load(open("parsed.json", encoding="utf-8"))
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
}
ADD = [
    ("City of Sunset Valley, Two City Council Member Seats (vote for up to 2)", "candidate", ["Sarah Ponder", "Robert Johnson", "Charles Young"], "City of Sunset Valley, Mayor"),
    ("Village of Volente, Village Council (vote for up to 2)", "candidate", ["Eric Peeters", "Tony Ruff"], "Village of Volente, Village Mayor"),
    ("Eastwood MUD Permanent Directors (vote for up to 5)", "candidate", ["Carrington Saathoff", "Ryan Sullivan", "Grant Ballew", "John Berry", "William Waller"], "Eastwood MUD Proposition G"),
    ("Hidden Lakes MUD No. 1 of Travis County, Board of Directors (vote for up to 5)", "candidate", ["Nicodemus Abowd", "Denis Fletcher", "Jeff Markey", "Mariano Ravelo", "Barry Marotz"], "Hidden Lakes MUD No. 1 Proposition J"),
    ("Kennedy Hill MUD Permanent Directors (vote for up to 5)", "candidate", ["Daniel McElrath", "Chase Nixon", "Jacob Clark", "Ross Hamilton", "Dane Rymer"], "Kennedy Hill MUD Proposition G"),
    ("Northtown MUD Directors (vote for up to 3)", "candidate", ["Scott Moser", "Brenda Vrabel", "R. Lee Hill", "Chris Capers"], "North Austin MUD No. 1 Director, Place 4"),
    ("Travis County MMD No. 1 Permanent Directors (vote for up to 5)", "candidate", ["Felicity Maxwell", "Casey Paulson", "Mickey Jamail", "Daniel Kavelman", "Ryan Puzycki"], "Travis County MMD No. 1 Proposition F"),
    ("Travis County MUD No. 41 Permanent Directors (vote for up to 5)", "candidate", ["Jason Nobbe", "Kelly Schill", "Ashtyn Bogue", "Lyndsey Mylius", "Jared Williams"], "Travis County MUD No. 41 Proposition F"),
    ("Williamson-Travis Counties MUD No. 1 Directors (vote for up to 3)", "candidate", ["Beth Jones", "Stephen Bodnarchuk Jr.", "Hanoi Avila", "David Flores", "Kimberly Massaro", "Linda Fabre", "Thomas Vacek"], "Vista MUD of Travis County Proposition B"),
    ("Cypress Ranch WCID No. 1, Board of Directors (vote for up to 3)", "candidate", ["Richard Kenyon", "Travis Wright", "Rick Shute", "Jason Blair"], "Williamson-Travis Counties MUD No. 1 Directors (vote for up to 3)"),
    ("Travis County WCID No. 17 Directors (vote for up to 3)", "candidate", ["Elicia Michaud", "Larry Harlan", "Phil Han", "Sonja DeLaFuente", "Ryan Carretta"], "Cypress Ranch WCID No. 1, Board of Directors (vote for up to 3)"),
    ("Wells Branch Community Library District Board of Trustees (vote for up to 3)", "candidate", ["Rudolf J. Valenti", "Paul Wadehra", "Philip Waters", "Abigail Joffrain", "Elizabeth Martin"], None),
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

key = {
    "election": "Travis County Joint General and Special Elections, November 3, 2026",
    "source": "https://votetravis.gov/wp-content/uploads/G26-Bedsheet-Ballot-Final-FINAL.pdf",
    "source_note": "Consolidated ('bedsheet') ballot listing every contest in the county. No single voter sees all of these; each ballot is a subset by precinct.",
    "unopposed_not_on_ballot": [
        "Coupland ISD trustees (declared elected unopposed)",
        "Manor ISD Board of Trustees, Places 1-4 (declared elected unopposed)",
    ],
    "contests": final,
}
json.dump(key, open("../answer_key.json", "w"), ensure_ascii=False, indent=1)
from collections import Counter
print(len(final), "contests")
print(Counter((it["level"], it["type"]) for it in final))
for it in final:
    print(it["id"], it["level"][:8], "|", it["entity"], "|", it["title"], "|", ", ".join(it["choices"])[:90])
