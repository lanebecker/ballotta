"""Build learn.json: per-contest "learn more" data for the site.

Inputs
- answer_key.json                  contests and candidates (Travis County consolidated ballot)
- data/lwv_candidates.json         from parse_lwv.py: each candidate's page in the League of Women Voters
                                   of the Austin Area 2026 Voters Guide, the campaign website the guide
                                   lists, whether the candidate answered, and a link check (Oct 14, 2026)
- data/lwv_measures.json           first guide page for each proposition the guide covers

Rules (see the design page): every candidate in a race gets the same links; when something is missing
we say so; Ballotta never writes about candidates. Office notes describe the office, not the people.
"""
import json, re, pathlib
HERE = pathlib.Path(__file__).resolve().parent
key = json.load(open(HERE / 'answer_key.json', encoding='utf-8'))
lwv = json.load(open(HERE / 'data/lwv_candidates.json', encoding='utf-8'))
lwvm = json.load(open(HERE / 'data/lwv_measures.json', encoding='utf-8'))

LWV_URL = 'https://austinvotersguide.org/LWVAA-VG-EN.pdf'
TRIB = ('Texas Tribune 2026 election coverage', 'Nonpartisan news; doesn’t endorse', 'https://www.texastribune.org/2026-vote/')
AUS_CLERK = ('Official candidate list', 'Austin City Clerk', 'https://www.austintexas.gov/clerk/elections/Ballot-Applications-November-2026')
AUS_FORUM = ('Candidate forum videos', 'City of Austin voter information page', 'https://www.austintexas.gov/voterinfo')
AUS_BP = ('Ballotpedia', 'The races and candidates, with survey answers', 'https://ballotpedia.org/City_elections_in_Austin,_Texas_(2026)')
AISD = ('Board election page', 'Austin ISD', 'https://www.austinisd.org/board/elections')
# Campaign sites the link check reached only over http:// that load over https:// in a browser (checked Oct 15, 2026):
# linked over https:// (#36). The other http:// sites answered only on http://, so an https:// link would fail there.
HTTPS_OK = {'cuero4rrisd.com', 'juliefortexassenate.com', 'www.farrahabraham.com'}

# What each office does (duties only; no claims about any candidate).
OFFICES = [
    (r'^United States Senator', 'One of Texas’s two U.S. senators. The Senate writes federal laws, passes the budget, and confirms federal judges and cabinet members.'),
    (r'^United States Representative', 'Represents this district in the U.S. House, which writes federal laws and starts every bill that raises taxes.'),
    (r'^Governor', 'Texas’s chief executive. Signs or vetoes bills, can call special sessions of the Legislature, and appoints many state officials.'),
    (r'^Lieutenant Governor', 'Presides over the Texas Senate, which gives the office wide say over which bills move. Becomes governor if that office is vacant.'),
    (r'^Attorney General', 'The state’s lawyer. Represents Texas in court, gives legal opinions to state officials, and enforces child support and consumer protection laws.'),
    (r'^Comptroller', 'Texas’s chief tax collector and accountant. Estimates state revenue and certifies whether the state budget fits within it.'),
    (r'^Commissioner of the General Land Office', 'Manages state-owned land and mineral rights, much of whose income goes to public schools.'),
    (r'^Commissioner of Agriculture', 'Runs the Texas Department of Agriculture, which regulates pesticides, checks fuel pumps and store scales, and runs school meal programs.'),
    (r'^Railroad Commissioner', 'One of three commissioners who, despite the name, regulate Texas’s oil and gas industry, pipelines and coal mining. Not railroads.'),
    (r'Supreme Court', 'Texas’s highest court for civil cases, including family, business and juvenile cases.'),
    (r'Court of Criminal Appeals', 'Texas’s highest court for criminal cases, including every death penalty appeal.'),
    (r'State Board of Education', 'One of 15 members who set what Texas public schools teach, approve instructional materials, and oversee the Permanent School Fund.'),
    (r'^State Senator', 'One of 31 members of the Texas Senate, which writes state laws and the two-year state budget.'),
    (r'^State Representative', 'One of 150 members of the Texas House, which writes state laws and the two-year state budget.'),
    (r'15th Court of Appeals', 'A statewide appeals court, hearing cases since September 2024, for appeals involving the state government and its agencies.'),
    (r'3rd Court of Appeals', 'Hears appeals from trial courts in Travis and other Central Texas counties.'),
    (r'District Judge, (147th|299th|331st|403rd)', 'Presides over a Travis County criminal district court, which handles felony cases.'),
    (r'District Judge', 'Presides over a Travis County civil district court, which handles lawsuits and family cases such as divorce and custody.'),
    (r'County Court at Law', 'Presides over a Travis County court at law, which hears cases such as misdemeanors and smaller civil disputes.'),
    (r'Probate Court', 'Handles wills, estates, guardianships and mental health commitments.'),
    (r'^County Judge', 'Leads the Commissioners Court, Travis County’s governing body, and directs the county’s emergency response in disasters.'),
    (r'^District Clerk', 'Keeps the records of the district courts, manages jury service, and handles court filings and fees.'),
    (r'^County Clerk', 'Keeps county records such as property deeds and marriage licenses. In Travis County, the clerk also runs elections.'),
    (r'^County Treasurer', 'Receives, holds and pays out county money.'),
    (r'^County Commissioner', 'One of four commissioners who, with the county judge, set the county budget and tax rate and oversee county roads, parks and services.'),
    (r'^Justice of the Peace', 'Hears small civil claims, evictions, truancy and minor criminal cases such as traffic tickets.'),
    (r'Constable', 'Leads a county law enforcement office that serves court papers, carries out civil judgments and provides security for justice courts.'),
    (r'Appraisal District', 'Helps oversee the Travis Central Appraisal District, which values property for taxes. The board sets the district’s budget and hires the chief appraiser; it doesn’t set tax rates.'),
    (r'^City of Austin, City Council', 'One of 10 district council members who, with the mayor, pass city laws, adopt the city budget and appoint the city manager.'),
    (r'Village Mayor', 'Leads the village council, which passes local laws and adopts the village budget and tax rate.'),
    (r'Village Council', 'Serves on the village council, which passes local laws and adopts the village budget and tax rate.'),
    (r'Mayor', 'Leads the city council, which passes local laws and adopts the city budget and tax rate.'),
    (r'Council', 'Serves on the city council, which passes local laws and adopts the city budget and tax rate.'),
    (r'^ACC, Trustee', 'One of nine trustees who govern Austin Community College: its budget, tax rate and policies, and hiring its president.'),
    (r'ISD Board of Trustees', 'Serves on the school board, which sets the district’s budget and tax rate, adopts policies and hires the superintendent.'),
    (r'Library District', 'Governs the Wells Branch Community Library District, including its budget and tax rate.'),
    (r'(MUD|MMD|WCID)', 'Serves on the board of a local utility district, which provides services such as water, sewer and drainage and can levy property taxes and sell bonds.'),
]

LWV_ENT = {
    'City of Austin': 'CITY OF AUSTIN', 'City of Manor': 'CITY OF MANOR', 'City of Pflugerville': 'CITY OF PFLUGERVILLE',
    'City of Sunset Valley': 'CITY OF SUNSET VALLEY', 'Austin Community College': 'AUSTIN COMMUNITY COLLEGE (ACC)',
    'Leander ISD': 'LEANDER INDEPENDENT SCHOOL DISTRICT', 'Manor ISD': 'MANOR INDEPENDENT SCHOOL DISTRICT',
    'Round Rock ISD': 'ROUND ROCK INDEPENDENT SCHOOL DISTRICT',
}

AUS_ORD = 'https://votetravis.gov/wp-content/uploads/City-of-Austin-Orders.pdf'
AUS_BOND = ('City of Austin 2026 bond page', 'The City says its guide doesn’t support or oppose', 'https://www.speakupaustin.org/bond2026')
AUS_TAX = ('Tax estimate memo', 'City of Austin staff, May 15, 2026', 'https://services.austintexas.gov/edims/document.cfm?id=473808')
AUS_CHARTER = ('City of Austin charter election page', 'Each amendment explained by the City', 'https://publicinput.com/charter2026')
TAX_LINE = 'City staff estimate each $100 million of new debt adds about $14.34 a year to a typical Austin tax bill. The City hasn’t published a figure for each proposition.'
EXTRA = {
    'City of Austin Proposition A': {
        'plain': 'Lets the City borrow up to $260 million for parks, recreation centers, pools and new parkland, paid back with property taxes.',
        'for': 'the City may sell these bonds', 'against': 'the City may not sell these bonds',
        'money': [['Buildings', '$65.5M'], ['Parkland Improvements', '$65M'], ['Aquatics', '$65M'], ['Acquisition', '$35M'], ['Infrastructure', '$29.5M']],
        'moneyNote': 'Includes Gus Garcia Rec Center, Doris Miller Auditorium, and Garrison, Big Stacy, Walnut Creek and Civitan pools. Amounts from the City’s 2026 bond page.',
        'tax': TAX_LINE,
        'sources': [('Ordinance calling the election', 'No. 20260806-002 · full project list', AUS_ORD), AUS_BOND, AUS_TAX],
    },
    'City of Austin Proposition B': {
        'plain': 'Lets the City borrow up to $35 million for libraries, paid back with property taxes.',
        'for': 'the City may sell these bonds', 'against': 'the City may not sell these bonds',
        'money': [['Hampton Branch at Oak Hill', '$20M'], ['Future Colony Park branch', '$15M']],
        'moneyNote': 'Amounts from the City’s 2026 bond page.',
        'tax': TAX_LINE,
        'sources': [('Ordinance calling the election', 'No. 20260806-002', AUS_ORD), AUS_BOND, AUS_TAX],
    },
}
for L in 'CDEFGHIJ':
    EXTRA['City of Austin Proposition ' + L] = {
        'sources': [('Ordinance calling the election', 'No. 20260806-004 · full amendment text', AUS_ORD), AUS_CHARTER],
    }
EXTRA['City of Austin Proposition I']['note'] = 'This amendment was put on the ballot by a citizen petition.'

def link(t): return {'t': t[0], 's': t[1], 'u': t[2]}

out = {}
for c in key['contests']:
    cid, title = c['id'], c['title']
    d = {}
    if c['type'] == 'candidate':
        for pat, txt in OFFICES:
            if re.search(pat, title):
                d['office'] = txt; break
        cands = {}
        pages = []
        for ch in c['choices']:
            if ch == 'Write-in': continue
            name = re.sub(r'\s*\((REP|DEM|LIB|GRN)\)$', '', ch)
            v = lwv.get(ch, {})
            if not v.get('in_guide'):
                cands[name] = {'g': 0}; continue
            pages.append(v['page'])
            e = {'g': 1, 'p': v['page'], 'a': 1 if v['answered'] else 0}
            if v.get('unopposed'): e['u'] = 1  # listed as unopposed: the guide prints no questions for them
            if v.get('site'):
                # Only a definite "not found" counts as broken; 403/429/503/999 and timeouts here were bot walls
                # on hosts whose DNS resolves (checked Oct 14), and those pages load in a normal browser.
                ok = str(v.get('http', '')) not in ('404', '410')
                assert 'http' in v, ('site has no link check yet; run: python3 source/check_sites.py', ch, v['site'])
                url = v['url']
                if url.startswith('http://') and url[7:].split('/')[0].lower() in HTTPS_OK:
                    url = 'https://' + url[7:]
                e['s'] = url if ok else None
                if not ok: e['sx'] = 1  # listed, but didn't load when checked
            cands[name] = e
        d['cands'] = cands
        srcs = []
        if pages:
            lo, hi = min(pages), max(pages)
            allu = all(e.get('u') for e in cands.values() if e.get('g'))
            what = 'Lists this race as unopposed' if allu else 'Each candidate’s own answers'
            srcs.append({'t': 'League of Women Voters guide', 's': what + ' · ' + ('page %d' % lo if lo == hi else 'pages %d–%d' % (lo, hi)), 'u': LWV_URL + '#page=%d' % lo, 'lwv': 1})
        if c['level'] in ('Federal', 'State'): srcs.append(link(TRIB))
        if title.startswith('City of Austin, City Council'):
            srcs += [link(AUS_BP), link(AUS_FORUM), link(AUS_CLERK)]
        if title.startswith('Austin ISD'): srcs.append(link(AISD))
        d['src'] = srcs
        d['lwvRace'] = 1 if pages else 0
    else:
        m = re.search(r'Proposition ([A-Z])$', title)
        ent = LWV_ENT.get(c['entity'])
        pg = lwvm.get(ent + '|' + m.group(1)) if (ent and m) else None
        ex = EXTRA.get(title, {})
        d.update({k: v for k, v in ex.items() if k != 'sources'})
        srcs = [link(s) for s in ex.get('sources', [])]
        if pg: srcs.insert(0, {'t': 'League of Women Voters guide', 's': 'Background and explanation · page %d' % pg, 'u': LWV_URL + '#page=%d' % pg, 'lwv': 1})
        d['src'] = srcs
    out[cid] = d

(HERE / 'learn.json').write_text(json.dumps(out, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
nc = sum(1 for c in key['contests'] if c['type'] == 'candidate')
print('learn.json', len(out), 'contests;', sum(1 for v in out.values() if v.get('office')), 'of', nc, 'races with office notes;',
      sum(1 for v in out.values() if v.get('src')), 'with sources')
missing = [c['title'] for c in key['contests'] if c['type'] == 'candidate' and not out[c['id']].get('office')]
print('no office note:', missing)
