# Ballotta cold audit, Oct 17, 2026

**Status, Oct 22 (#128):** every finding was filed as GitHub issues #55–#98, and each issue's state is its status;
the release that closed it names it in `CHANGELOG.md`. Still open: #56 (the Tax Office's district codes), #86 (the old
page still built under both layouts: after Nov 3, Lane, Oct 22), #87 (markers: the two-pair lines are gone and a
pipeline test keeps them out, 1.5.2; removing the PHONE markers waits until no rollback is wanted), #88, #89, #90
(efficiency and tidiness), #97 (after the election).

Scope: the whole repo at commit 7a45db0 (origin/main as of 13:10 CT, Oct 17), read by four independent auditors with no inherited context (the shared page code; the laptop and phone layers and the offline copy; the Python pipeline and its data; the tests, mutation runners and security posture), then argued down against the code and, where it mattered, against the county's ballot PDF and map server. Findings that did not survive are listed at the end, struck through, so they are not re-found next round.

Line numbers are in `source/template-travis.html` (T), `source/build_site.py` (B), `tests/test_site.py` (S) and `tests/mutate_desk.py` (M) at 7a45db0.

What was already filed and is folded into the waves below rather than re-listed: #50 (title/tag pass through the counting firewall), #51 (26px candidate links), #52 ("Precinct  · change" with no precinct), #53 (laptop "Next undecided" goes nowhere when the open contest is the only undecided one).

Counts (computed from the files, not typed): 100 tests (30 laptop tests, 27 run only on the phone preview, 31 run only on the old phone page, 19 in none of those sets; 7 laptop tests are also old-phone-page-only, so the sets overlap); 282 laptop mutants, 129 phone mutants; 214 contests (93 measures, 121 candidate contests); 45 early + 201 Election Day vote centers. The committed `index.html`, `census.html`, `next/index.html`, `next/manifest.webmanifest` and `next/sw.js` are byte-identical to what `build_site.py` produces from the committed sources.

Filing: each numbered heading is the issue title; the bullets are the body. #38 and #47 are grab-bags and file as one issue per bullet (13 and 14 small issues, or two "small items" issues with checklists, Lane's call). Suggested labels: `P0`–`P3`, plus `data`, `page`, `phone`, `tests`, `process`, `cleanup` as marked by section.

Priorities: **P0** wrong for a voter, fix before early voting (Oct 19) if at all possible · **P1** a real bug or a gap in a promise the README makes, fix before Nov 3 · **P2** robustness, test integrity, process · **P3** architecture, efficiency, cleanup (mostly after promotion or after Nov 3).

---

## P0 — the ballot data

### 1. Ten "vote for up to N" contests list candidates in a different order from the printed ballot
- Where: `source/ballot/build_answer_key.py` 42–55 (the hand-typed `ADD` table), upstream `source/ballot/parsed.json`; ids c154, c168, c176, c179, c192, c199, c202, c203, c204, c214.
- What: the choice lists copy the line order of a text extraction that misordered those columns. Verified against the PDF by word coordinates: Eastwood MUD (p. 10) prints Ballew, Berry, Saathoff, Sullivan, Waller; Ballotta shows Saathoff, Sullivan, Ballew, Berry, Waller. Northtown MUD (p. 13) prints Hill, Capers, Moser, Vrabel; Ballotta shows Moser, Vrabel, Hill, Capers. All ten follow the pattern; all 111 single-seat contests, and the two 2-seat council contests (Sunset Valley c113, Volente c116), match the PDF.
- Why it matters: ballot order is drawn by lot and voters find candidates by it; a page that says "exactly what's on your ballot" and shows a different order is wrong, and the crib sheet inherits the wrong order.
- Fix: regenerate those ten lists from y-sorted word positions (pdfplumber) or re-type from the PDF; add a pipeline test that compares every contest's choice order with the PDF column order.

### 2. 37 measures end their "exactly as printed" text with a stray Spanish caption
- Where: `source/ballot/parse_ballot.py` 74 (collects English lines until a line matching `Propuesta|Proposición`); shipped in `source/answer_key.json`, rendered by `c.text`; ids c114, c120, c126, c146, c158–c167, c186–c191, c193–c198, c200, c201, c205–c213.
- What: where the Spanish entity caption sits on its own line before "Propuesta X", it is swallowed into the English text. Verified: c120 ends "…per $100 valuation of taxable property. Distrito de Austin Community"; c146 ends "…an additional $12,313,099. Distrito Escolar Independiente de"; c158 reads "Confirmation of the District Hidden Lakes MUD Núm. 1".
- Fix: stop the text loop at the line immediately before the next "Propuesta/Proposición" (the entity caption), not only at the first `is_spanish()` line: three of the 37 tails ("Coupland ISD" on c126, "Vista MUD del Condado de Travis" on c200/c201) do not match `is_spanish()`. Regenerate; add a check that every measure text ends in English (no tail matching the Spanish patterns and no tail equal to the entity caption).

### 3. `answer_key.json` is hand-edited and the pipeline cannot reproduce it
- Where: `source/ballot/build_answer_key.py` 172 (`source` still names the pre-correction PDF), `source/ballot/parsed.json` (produced from the earlier PDF), `source/answer_key.json`.
- What: rerunning `build_answer_key.py` on the committed `parsed.json` differs from the committed key in four places: c038 loses "(DEM)" on Chantal Melissa Eldridge, c174/c190/c197 revert "waste water" to "wastewater", and the `source` URL and `source_corrected: "2026-10-14"` disappear. The Oct 14 corrections were applied to the JSON by hand. Anyone who reruns the script (including a fix for #1 or #2) silently undoes them.
- Also: `parse_ballot.py` reads `cols/p*_c*.txt`, a hand-made column extraction that is not in the repo and has no script (`parse_ballot.py` 8); both ballot scripts use cwd-relative paths. A fresh clone cannot rebuild the key.
- Fix: a `source/ballot/extract_cols.py` (pdfplumber crops at the column x-boundaries), regenerate `parsed.json` from the corrected PDF, move the Eldridge party and the "waste water" spellings into `FIX_CHOICES`, put the URL and `source_corrected` in the script, and add a test that regeneration equals the committed key. Do this before #1 and #2 so their fixes land in the script, not the JSON.

### 4. Seven contests are routed to nobody, and four MUD elections hang on one or two address rows
- Where: `source/build_rules.py` 69–79; counts from `source/data/combos_temp.json`.
- What: Travis County MUD No. 41 (7 contests, c193–c199) has no rule that matches any address, so no visitor ever sees it; the page's data note says only that the district "can't be placed on a map yet". Lead: `combos_temp.json` has `MUD = M41` on two rows covering 1,217 addresses (precinct 142; the county server confirms the code in those rows' `CodeCat`), which `build_rules.py` labels "No county code found": M41 is the obvious candidate and belongs on the Tax Office list. Hero Way West MUD (3 measures), Kennedy Hill MUD (8 contests) and Sunfield MUD No. 2 (6 measures) each route to one address-combination row with a single address; Eastwood MUD (8) to one row with three addresses; Travis County MMD No. 1 (7, medium) routes via `Temp = M125` while one row carries `MUD = M119` and one row (two addresses) carries `Temp = M128`, which the rule's note does not mention. Also: a precinct absent from `tlc_precincts.json` makes the US Rep, State Rep and State Senator contests vanish silently (`enrich()` returns nothing to join), and `build_rules.py` 132 checks for one CD and one HD per precinct but never SD. These are plausible for new-district confirmation elections, but one wrong Temp code shows a whole MUD election to the wrong household, or to nobody.
- Fix: confirm M41, M118/M123/M126/M93 and the M125/M119/M128 question with the Tax Office (the 8 questions already emailed are the right channel); print "unrouted" contests at build time and fail the build unless each is listed in an explicit allow-list with a reason; check SD alongside CD/HD; fall back to the county's own Congressional/Legislative/Senate fields when a precinct is missing from the TLC join and flag the ballot medium when neither source has a district; consider a "Not shown for any address" note in the README's data section.

### 5. Build-time filters drop lines silently
- Where: `source/ballot/build_answer_key.py` 57–63 (`JUNK`: `Travis Coun.*`, `.*Independent( School)?,?`, `City of [A-Za-z ]+`, `\d+`, …); `source/ballot/parse_ballot.py` 29 (`SPANISH_START`) and the `len(eng) < 12` cap.
- What: a future candidate line such as "Travis Counts" or a ballot label "(Independent)" would vanish with no log. Today the partisan line count matches the PDF (104 = 104), but nothing asserts it.
- Fix: print every dropped line; assert the partisan-line and FOR/AGAINST counts from the PDF equal the key's (the PDF's party tokens need a whitespace-tolerant regex: it prints "( REP)" and "(R EP)" in two places and carries an 8-entry party legend; 104 = 104 only with those handled).

---

## P1 — bugs and broken promises on the page

### 6. The unit-suffix strip eats real street names ("STECK AVE", "UNITY DR", "STEVENS RD")
- Where: T:1093 `cand.address.split(',')[0].toUpperCase().replace(/\s+(UNIT|APT|STE|#).*$/, '')`.
- What: no word boundary, so any token *starting with* UNIT/APT/STE is treated as a unit marker. Verified: "2505 STECK AVE" → "2505", "555 UNITY DR" → "555", "123 STEVENS RD" → "123", "4 STEINER RANCH BLVD" → "4". The county's own vote-center list has two Steck Ave addresses. The `Address = '2505'` query returns nothing, so an exactly matched voter is sent down the `nearby()` path (120 m radius), gets the "nearby" banner, and if the block is mixed, "Double-check" flags they should not have.
- Fix: `/\s+(?:UNIT|APT|STE)\s+\S.*$|\s+#.*$/` (marker must be a whole word followed by something); a test with a Steck Ave address.

### 7. Two lookups can run at once and the later *response* wins
- Where: T:1075–1077 (Enter handlers and `#go` call `lookup()` with no re-entry guard).
- What: Enter twice, or Enter then click, or a ZIP correction pressed quickly, starts two county round-trips; each renders on return, so a corrected address can be overwritten by the first one's late answer, `ballotta.ballot` is written twice and `lookup_started`/`ballot_found`/`address_changed` double-count.
- Fix: a `lookupSeq` counter like `incSeq` (T:2581) and ignore stale returns; disable `#go` while awaiting.

### 8. A Census timeout is reported as "address not found"
- Where: T:1115–1134 (`censusPoint`: the 8-second timer resolves `null`), T:1090–1091 (`null` → "We couldn't find that address", `lookup_failed: not_found`).
- What: a slow or unreachable Census geocoder (or a browser that blocks the sandboxed frame; or the Census dropping JSONP, which gives a 200 with a JSON body, so `s.onerror` never fires) tells the voter their address is wrong and counts it as a bad address.
- Fix: resolve a distinct value on timeout, show "couldn't reach the Census geocoder, try again", count `lookup_failed: census_unreachable` (add it to `EVENTS` and the README).

### 9. Between Oct 31 and Nov 2 the wait-times link points at a dashboard that does not exist yet
- Where: T:1338 (`defaultPeriod` flips to `eday` after Oct 30), T:1354 (`waitsURL` → "Election Day Voting Dashboard"), T:1372 (`waitsNote` caveats only before Oct 19).
- What: for three days the page's default period is Election Day and "Check live wait times" goes to ElectionLink's Election Day page, which today is a 200 with the page skeleton and no wait-time data. The laptop's `whenLine` says "Election Day is Tue Nov 3" but the link is unqualified.
- Fix: in `waitsNote()`, when `period === 'eday'` and today is before Nov 3, say "fills in on Election Day"; same in the laptop's where-to-vote view.

### 10. Dates use the visitor's clock, not Central Time
- Where: T:1337–1338 (`today()`, `defaultPeriod`), T:1372, the laptop `whenLine`.
- What: a Travis County voter travelling, or a phone with a wrong zone, sees the early/Election Day switch and the "fills in" notes shift by up to a day either side of Oct 19, Oct 30 and Nov 3.
- Fix: compute "today in America/Chicago" once with `Intl.DateTimeFormat('en-US', { timeZone: 'America/Chicago', … }).formatToParts` and use it everywhere `today()` is used.

### 11. A restored ballot loses the specific caveat a live lookup showed
- Where: T:1192–1194 (`listFromStored` rebuilds notes from the sign of the stored id only).
- What: a live lookup shows the rule's note ("Austin limited-purpose residents…", "Two possible county codes…"); after a reload, a Keep link or a new day, every medium contest says the generic "Not confirmed for your address. Check your official ballot." The voter who comes back has less to go on than the first time.
- Fix: for `n < 0`, use `DATA.rules[id].note || generic`. Store nothing extra.

### 12. Precinct and point in a Keep link or stored ballot are not validated
- Where: T:1589 (`pr: String(o.pr || '').slice(0, 6)`), T:1196 (`here = Array.isArray(st.pt) ? st.pt : null`).
- What: a crafted Keep link puts any six characters (including RTL/zero-width) into the "Precinct ___" line, the laptop header, and the body of the feedback e-mail to the maintainer (URL-encoded, so not an injection, but attacker text in the user's outgoing mail). A tampered `pt` of `["x","y"]` or `[1e9,1e9]` gives `NaN mi` and an implementation-defined sort of vote centers.
- Fix: `pr` must match `/^\d{1,4}$/`; `pt` must be two finite numbers inside the Texas box `censusPoint` already uses (T:1125).

### 13. The counting firewall still passes free text, and the page's URL path (extends #50)
- Where: T:1017 (`TOP` copies `title`, `tag`, `hostname`, `screen`, `language` as any string; `url` keeps its path).
- What: #50 covers `title`/`tag`. Also: Umami wraps `pushState`/`replaceState` and sends a page view for a new path, so a future `history.pushState(null, '', '/' + precinct)` would leak through the hook unchanged; the real-tracker test (S:1034) greps the payload only for `Guadalupe|78701|Precinct|Qadri`, so a bare "300" or "/300" would pass. Not exploitable today (nothing sets `document.title`, no `data-tag`, the only `replaceState` calls strip the fragment).
- Fix: in the hook, send `title` as a constant, drop `tag`, and allow `url` only when its path is `/` or `/next/` (otherwise null); extend `privacy_firewall_drops_anything_unlisted` with a `pushState` and a `document.title` probe.

### 14. The pinned tracker has no recorded hash and nothing pins it
- Where: `umami.js`; README's "pinned copy (fetched 2026-10-14)"; S:326 checks only the tag's `src`.
- What: the README's "can't change underneath the page" rests on git alone. sha256 today: `91a876d767646fd5b7701b6fabf97f8a99ae53b94e7e5b58d465bad1e5d763e0`.
- Fix: assert the hash in a test, record it in the README, and add `integrity="sha256-…"` to the tag (same-origin, so it works on Pages).

### 15. The fail-closed analytics stub depends on `defer`, and the test that pins it is skipped on the preview
- Where: B:242–248 (the stub is a synchronous head script; the real hook is defined in the body-end script; the tracker is `defer`); S:1066 checks the stub precedes the tag; S:326 (`audit_a14_a15_tracker_and_targets`) pins `defer`, but that test is in `OLD_PHONE_TESTS`, so the preview run (and the live page after promotion, until the ports in #29) never checks it.
- Fix: assert `defer` and the stub-before-tag order in `privacy_firewall_drops_anything_unlisted`, which runs on both pages. One line.

### 16. The page is frameable by any origin
- Where: B:76–77 (`PAGE_CSP`); GitHub Pages sends no `X-Frame-Options`, and a meta CSP cannot carry `frame-ancestors` (verified: no such headers from ballotta.org).
- What: impact is low (no accounts; a framer cannot read storage; "Clear everything" is behind `confirm()`), but an overlay could trick a visitor into copying their Keep link into the framer's page.
- Fix: `if (top !== self) document.documentElement.hidden = true;` inside the hashed main script (the CSP already stops injected scripts from undoing it); a sentence in the README's lock-down paragraph saying `frame-ancestors` is not available on Pages.

### 17. Two "real tracker" tests always test `index.html`, even on the preview run
- Where: S:1065 (`tag = (ROOT / 'index.html').read_text(…)`), S:1093–1097 (replaces the live `data-domains` and navigates to `/index.html`).
- What: with `BALLOTTA_PAGE=next/index.html` both tests pass while exercising the other page; neither is in `OLD_PHONE_TESTS`, so the skip accounting hides it. The gap is before promotion: the phone layout's counting path has no real-tracker test until the day `index.html` becomes the phone page.
- Fix: parameterise on `PAGE`; rewrite the preview's `data-domains="preview.invalid"` for the test the same way.

### 18. Two tests start failing on Oct 31
- Where: S:102–115 (`where_to_vote_sorted_by_distance` expects early-voting sites, "Open till 10pm Oct 29–30", then 45), S:642–655 (`desk_where_to_vote_list_and_private_map` expects 45 after `#dk-all`).
- What: `defaultPeriod()` returns `eday` from Oct 31, so the first list is the 201 Election Day centers. `counts_progress_sources_and_clearing` already clicks `#t-early` to dodge this; these two do not. From Oct 31 the suite is red on two tests for a reason unrelated to any change, and the mutation runners' baseline aborts.
- Fix: `pg.clock.install(time=…)` a fixed date in both, or click the early chip first.

### 19. The "Slow connection" bar never clears on its own
- Where: T:2552 (hidden only on the `online` event); README's phone section says "it goes when the network comes back".
- What: in the `slow` case the device was never offline, so `online` never fires; the bar stays until "Try again".
- Fix: on `slow`, re-probe (`fetch(location.href, { method: 'HEAD', cache: 'no-store' })` on `visibilitychange` and a timer) and hide on success; or change the README and the bar's copy.

### 20. The offline copy shows a server error instead of the kept page
- Where: B:145 (`if (typeof first !== 'string') return first;` returns any Response, whatever its status).
- What: a 404/500/503 that arrives inside 4 seconds (GitHub Pages mid-deploy, a captive portal's 200 for the wrong body, a proxy 502) is shown even when a good copy is kept; only a thrown fetch or 4 seconds of silence fall back.
- Fix: treat `!res.ok && res.type === 'basic'` (and `type === 'error'`) like `'offline'` when a kept copy exists; keep passing `opaqueredirect` through. One test in `phone_offline_copy_after_one_visit`'s family with a 503 route.

### 21. Promotion is a manual step the build does not perform
- Where: B:176–179 (`outputs(False)` with `PHONE_LIVE = True` writes `sw.js`, `manifest.webmanifest` and the self-removing `next/sw.js`, but never the `next/index.html` redirect); B:268 (`--preview` refuses to run); the phone plan says to put the redirect back by hand.
- What: the day `PHONE_LIVE` flips, the committed `next/index.html` is still the full preview page, with its own `<link rel="manifest">` and `sw.register('sw.js')`: it re-registers the worker that `next/sw.js` is meant to remove, and `next/manifest.webmanifest` stays installable.
- Also: a phone that installed the preview only gets the self-removing worker when the browser checks for updates under `/next/`, which needs a navigation there; a visitor who only opens `ballotta.org/` afterwards keeps the preview worker and its cache for good.
- Fix: have `outputs(False)` emit the redirect page as `next/index.html` (with `navigator.serviceWorker.getRegistration('./').then(g => g && g.scope === new URL('./', location.href).href && g.update())`, the scope check the plan already notes) and remove or neutralise `next/manifest.webmanifest`; a test that builds with `PHONE_LIVE = True` in memory and checks all three.

### 22. Both Home Screen apps are called "Ballotta" on an iPhone
- Where: T:14 (`apple-mobile-web-app-title`), B:100 (`short_name`).
- What: only the manifest's `name` says "(preview)"; iOS labels the icon from the apple title or `short_name`, so a tester with both installed cannot tell them apart.
- Fix: vary both in the preview build.

### 23. `said()` can silently stop marking offline pages
- Where: B:148–154 (`t.replace('<html lang="en">', …)` on any kept `text/html` navigation, including `census.html`).
- What: if the template's `<html>` tag ever gains a class or attribute, the replace is a no-op and the saved-copy bar disappears with nothing in the worker to say so (the page test would catch it, but only on the preview run).
- Fix: a build assert that the template's opening tag equals the string `sw.js` looks for; match `/^<!doctype html>\s*<html\b/i` instead of a literal.

### 24. Non-Latin reasons can make a Keep link the page itself refuses
- Where: T:1432 (`unpackFrag` rejects bodies over 40,000 chars), `keepURL()` never warns.
- What: measured on the largest routable ballot (72 contests): 600-character English reasons everywhere give a ~10 KB link; the same in Han text gives ~126 KB, which the page reports as "looks damaged"; emoji reasons ~47 KB, same. iOS Messages and `mailto:` truncate well below that.
- Fix: after `packFrag`, if the URL exceeds ~8,000 characters, say so in the Keep sheet and offer "without reasons"; a test with long non-Latin reasons.

### 25. Reloading before answering "Load your saved picks?" silently drops the Keep link
- Where: T:2590 (`if (inc[0] === 'k') { SS.del('ballotta.incoming'); if (fresh) openRestore(o); }`).
- What: README says opening a Keep link "asks before replacing anything"; a reload with the dialog unanswered deletes the stored fragment and shows nothing.
- Fix: show the dialog again from `sessionStorage` on a non-fresh load, or at least `notify()` that the link was set aside.

---

## P2 — tests, mutation runners, process

### 26. Mutants inside the page's `<script>` are "killed" by a CSP hash mismatch, not by the test they name
- Where: M:12 (`put()` rewrites `index.html` text directly, never rebuilds, so the CSP meta still carries the old hash); tests that run with `csp=True`: S:1569, 1597, 1616, 2227, 2301, 2394.
- What: a PREV mutant under a `csp=True` test makes Chromium refuse the whole main script, so every assertion fails for that reason alone. The entire Census-sandbox set (laptop B5–B8, B12) and phone P32, P89–P94, P107, P110, P114, P115 prove nothing about the logic they describe.
- Fix: for PREV mutants whose targets use `csp=True`, mutate the template and rebuild in memory (or recompute `csp_meta` on the mutated page before writing).

### 27. A Playwright timeout counts as a kill
- Where: M:334 (`except Exception as e: killed.append(…)`); the restored re-run (M:338–341) guards only the inverse case.
- What: a mutant run that times out on a slow county lookup is KILLED, then the restored run passes a few seconds later: a false kill, and nothing in the result line says the kill was a timeout rather than an assertion.
- Fix: record the exception type (already captured) and treat `TimeoutError` as a retry, not a kill; require an `AssertionError` for KILLED.

### 28. The mutation lists are regression pins, not coverage of the security-critical code
- Where: M (282 entries), `tests/mutate_phone.py` (129).
- What: no mutant touches the fragment-stripping first script (T:16–28), the `hashchange` handler (T:2595–2601), `packFrag`/`unpackFrag`/`handleIncoming`, `applies()`/`enrich()` (ballot routing), `esc()`, `census_page()`'s CSP, or `csp_meta()`'s hash computation (B1/B2 only drop or weaken it).
- Fix: a dozen mutants over those regions; or say in the README that the runners pin fixes rather than measure coverage.

### 29. Thirty-one tests run only on the old phone page and have no port
- Where: S:407–418 (`OLD_PHONE_TESTS`), S:2667–2669.
- What: on the preview they are skipped (page lock-down, drop-off counts, Keep round trip, share/compare, backup nudge, persistent storage, crib print, "laptop failures never break the phone flow", …), with `phone_whole_visit_counts_only_listed_events` and `phone_runs_under_the_page_lock` as the only stand-ins. Promotion makes `HAS_PHONE` true on `index.html`, so those 31 would be skipped on the *live* page until the ports in "Task 13" exist, and that plan is unwritten.
- Fix: write the ports before promotion; make the runner exit non-zero if a named test is skipped on both pages.

### 30. `LIVE_SHA` is re-pinned in the same commit as every change, so it guards nothing the byte-equality check does not
- Where: S:19, S:466–478. Four commits today re-pinned it for ordinary UI changes.
- What: the test's purpose ("the phone layout must not change the live page") is already enforced by `'PHONE' not in live` and `'id="ph-bar"' not in live` on the same lines. The hash makes every template change a two-step dance.
- Fix: drop the hash, keep the on-disk-equals-build assertion and the leak checks.

### 31. No county stub: the suite and both runners are unrunnable when `taxmaps` is down or slow
- Where: S:49–52 and S:425–428 (the lookup helpers, 30-second waits), called from ~74 tests. The Census path is stubbed; the county path is not.
- Fix: a `BALLOTTA_STUB_COUNTY=1` mode that routes the two county endpoints to recorded responses for the courthouse address (and one mixed-unit address); keep one live test as the canary.

### 32. Two runners on one clone can corrupt each other; a hard kill leaves a mutant and a `.mutate-tmp` behind
- Where: M:19–25 (mutates `index.html`, the template, `build_site.py` and the README in place), `.gitignore` (only `__pycache__/`). The port is configurable (`BALLOTTA_PORT`, S:12) and the phone plan documents running the two *test suites* side by side on different ports; nothing stops someone from doing the same with the two *mutation runners*, which share the template and `build_site.py`.
- Fix: a lock file; refuse to start if a `.mutate-tmp` or another runner's lock exists; add `*.mutate-tmp` to `.gitignore`.

### 33. Target lists are not checked: a PREV mutant can name a test that rebuilds from the template
- Where: M:85 (L9 lists `desk_phone_layout_matches_live_page`, which builds in memory from the template and can never see an `index.html` mutant).
- Fix: assert in `main()` that a PREV mutant's targets do not call `build_module()`.

### 34. No CI: push to `main` is deploy, and nothing checks the committed build
- Where: no `.github/` directory.
- Fix: a workflow that runs `build_site.py` (both builds) in memory and diffs against the committed outputs, runs the pipeline regeneration checks from #3, and lints the template's marker pairs: no Playwright, no county server, under a minute. It catches build drift and a left-behind mutant before Pages serves it.

### 35. No `requirements.txt`, no install line
- What: the tests need Playwright ≥ 1.45 (`pg.clock`) with Chromium and `pypdf` (the crib-print test, S:666), `parse_lwv.py` needs PyMuPDF, `make_icons.py` needs Playwright, `build_site.py` needs Python ≥ 3.9; the ballot step reads pre-extracted text and needs whatever made it (#3 proposes pdfplumber). None is pinned anywhere (the README now names PyMuPDF and Playwright; `pypdf` and the pins belong in a file).
- Fix: `requirements.txt` with pins; one install line in the README.

### 36. The whole repo is served at ballotta.org
- What: `tests/`, `docs/plans/` (verbatim quotes from Lane, Claude session URLs, audit internals), `source/ballot/bedsheet.pdf` (1 MB), `source/data/combos_temp.json` all answer 200. No secrets anywhere (grepped), but it is more than the site.
- Fix: publish from a `site/` folder (Pages "source folder") or a `gh-pages` branch holding only the built files; `build_site.py` writes there.

### 37. No `LICENSE`, no `SECURITY.md`, no OFL text with the fonts
- What: the code and docs are all-rights-reserved by default while publicly served; the README credits Zilla Slab and Public Sans under OFL 1.1, which asks for the licence to travel with the font files.
- Fix: add `fonts/OFL.txt`, a licence for the code (Lane's call), and a short `SECURITY.md` pointing at the feedback address.

### 38. Small repo-hygiene items
- `UMAMI_DOMAINS` (B:17) lists `lanebecker.github.io`, which 301s to ballotta.org, so the entry is dead.
- `source/data/combos_temp.json` is a required input to `build_rules.py` (378 KB, 1,317 district-code combinations with counts; no addresses) with a "temp" name and no record of the query that produced it.
- `og.png` has no generating source; the icons do (`make_icons.py`).
- `.impeccable/config.json` suppresses "cramped-padding" for the whole template with a wildcard and no expiry; scope it to the measured selectors.
- `source/vote_sites.json` is a hand-built array of 7-element rows (`name, room, street, city, flags, lon, lat`) decoded only in the template; its hours and dates live in the template (T:1350, 1365). Three typos: "Confrence Room" (Millennium Youth Entertainment Complex), "1201 E Runberg Ln" in the early list (the Election Day list has "Rundberg"), "McNeil Dr" vs "Mcneil Dr" between the two lists; those three rows are why only 42 of the 45 early sites match an Election Day row byte for byte (all 45 are Election Day sites too).
- `check_sites.py` treats `000` (no answer on https or http) as a working link (`build_learn.py` 130 excludes only 404/410): Okey Anyiam's site is linked with `http: "000"`; from here `https://` fails the TLS handshake (curl exit 35) and `http://` redirects into the same failure, so a DNS-only rule would not catch it. Record curl's exit code and treat 6 (could not resolve) and 35 (TLS failure) as broken, keeping 403/429/503 as bot walls. Its recorded `url` is the requested one, not the final one after `-L`; HTTP codes are nondeterministic (bot walls), so every rerun produces diff noise and can flip a link. The crediting heuristic in `parse_lwv.py` 117 compares the first 14 characters of a squashed host, so every facebook.com link collides.
- `lwv_measures.json` carries Georgetown/Hutto/Taylor (Williamson County) entries that nothing reads.
- The in-page JSON guard (B:221) escapes only `</`; `<!--` and U+2028/2029 are not escaped. None occur in today's data; a candidate name or site string containing them would alter the page. Escape them too, or `ensure_ascii=True` for the script payload.
- `ext()`/`candLinks()` trust the campaign-site scheme from `DATA` (all 97 are http/https today); assert `^https?://` for every `s` and `src.u` in `build_site.py`.
- The page-side Census check (T:1124) verifies `e.source` but not `e.origin === 'null'`; add it.

---

## P3 — architecture, efficiency, cleanup

### 39. The old phone page is still fully rendered under the laptop app, and will be under the new phone layout too
- Where: T:1199–1214 (`showBallot` builds the whole accordion, `raceHTML` × up to 72, into `#groups`; `renderVote()`, `renderCrib()`), T:1297 (`renderCompare()` runs on every `refresh()` while invisible), `.wrap{display:none}` under the app at both widths once PHONE is live.
- What: every pick updates a hidden page; the laptop `desk.render()` runs on today's phones where it is invisible. Once PHONE is promoted, the following are dead at every width: `#a-vote`, `#a-keep`, `#a-share`, `#reset`, `#reset-all`, `#reset-all-foot`, `#allsites`, `#t-early`/`#t-eday`, `#nudge`, `#compare`/`showCompare`/`renderCompare`/`#f-cmp`, `wantCompare`, and the 31 `OLD_PHONE_TESTS`.
- Fix (after promotion): remove the legacy accordion and its tests; `pick()` and `refresh()` then update only the model and the live view. This is the single biggest simplification available.

### 40. Three-layer markers after both layers are live
- Where: T:1929 (`/*PHONE*/(true || /*/PHONE*/WIDE.matches/*PHONE*/)/*/PHONE*/`: two inline pairs on one line), T:2224 (`/*PHONE*/false && /*/PHONE*/…`), ~20 one-line insertions, `strip_marked()`.
- What: every pair was verified to strip into valid, correct code in all three builds, but the two "constant" edits read as puzzles and a touched half breaks only one build.
- Fix: now: `const COMPARE_ANY_WIDTH = /*PHONE*/true || /*/PHONE*/false;` and the same for 2224. After promotion: delete the PHONE markers (keep `DESK` only as long as a rollback is wanted; then delete those too) and shrink `strip_marked()` accordingly.

### 41. 54 identical CSS declarations in the DESK and PHONE media blocks
- Where: T:204–402 vs T:439–680 (`.dk-link`, `.dk-lines`, `.dk-oval`, `.dk-why textarea`, `.dk-map*`, `.dk-page .*`, `.dk-kv*`, `.dk-tbl small*`, `.dk-site*`, `.dk-num*`, `.dk-rbar*`, `.dk-info*`, `.dk-notes h3/p`, `body.dk-friend …`, …). Verified by line diff.
- Fix: hoist them above both media queries (they depend only on `.dk-*` classes present at both widths).

### 42. Shipped data: ~40 KB raw of the 196 KB could go, and 11 KB of comments ship to the browser
- Where: B:220 (`json.dumps` defaults); `learn.json` `src` objects (138 League-guide entries, 22 KB, of 49 distinct shapes that differ only by page number and caption; the Texas Tribune entry 32 times; the Austin ordinance link 8 times); `rules.note` strings repeated 7–10×; `tlc` (15 KB) duplicates the county's own Congressional/Legislative/Senate fields, which agree with it for all 1,316 address combinations; every early site repeats in the Election Day list (42 byte-identical, 3 differing by typos); the 7 unrouted MUD 41 contests (#4) ship though nothing can match them.
- What: the page is 371 KB raw / 85 KB gzipped, one request; nothing shipped is unused, so this is a trim, not a fix. Full-line `//` comments in the built page's scripts are 8.7 KB (about 17 KB with trailing ones).
- Fix: intern repeated `src` objects and notes; drop `tlc` and rule on the county's fields (the missing-precinct guard is in #4, wave 1); strip `//` comments from the built page.

### 43. State that is kept in several places
- `ballot`, `ballotta.ballot.b`, `lastLookup`, `progressSeen.sig`, and the laptop `ui.cur` all describe the current ballot (#11 is one symptom).
- `b64e` (T:1412) and `bytesB64` (T:1419) are the same function; `b64d` (T:1444) duplicates `unpackFrag`'s decode loop.
- Fix: one `ballotState` object with the ids, confs and note keys; one base64url pair.

### 44. Per-keystroke work
- Where: T:2009–2015 (the laptop reason box: `renderCrib(); rail();` rebuilds all rail rows and the crib on every character), T:1211 (the old phone box: `renderCrib()` only, leaving the rail's "Reasons N" stale until the next render), `LS.set('ballotta.whys', …)` per keystroke (a `storage` event to every other tab each time).
- Fix: debounce the save and the redraws (~150 ms); update only the affected rail row.

### 45. Two tabs do not stay in step
- Where: T:1825 (the `storage` listener reloads only when `ballotta.ballot` changes in another tab).
- What: two tabs on the same ballot each write `ballotta.picks`/`ballotta.whys`; the last writer wins silently.
- Fix: on `storage` for picks/whys, re-read and `refresh()`.

### 46. Share names: the sender is never told, and the homoglyph table has gaps
- Where: T:1624 (`.slice(0, 30)` can cut a surrogate pair), T:1700 (`safeName` runs on the receiving side only), T:1721–1730 ("Your friend" with a `?` avatar).
- What: a sender who types "Travis GOP" gets no feedback and the friend sees "Your friend". Verified gaps that pass: "Ɍepublican", "Łwv", "Ɠop", "Ɗems", "Ðems", "Ƿarty", "LANEGOP" (all-caps glued); false positives that are blocked: "Elections Lane", "Campaigner", "Village Ofelia", "Lane, Republican". The README calls the block best-effort (and #43's closing comment lists accepted trade-offs), so this is tuning.
- Fix: run `safeName` on input and say "that name can't be used"; slice by code points (`[...s].slice(0, 30).join('')`); fold stroke/hook letters (Ɍ Ł Ɠ Ɗ Ð Ƿ Ꝑ) to their base in `FOLD`.

### 47. Small layout items (phone preview unless noted)
- The map fold re-closes on every redraw (T:2393, 2539): remember its open state.
- The five numbered map markers drop out of frame for an outlying address while the SVG's `aria-label` still promises them (T:2070–2082, fixed ±0.06° window): scale so the fifth-closest fits, or say "N of the 5 closest are off this map". Laptop too.
- `menuItems()` (T:2403) is built once at load, so after an Android install the tab's menu still offers "Add to your Home Screen".
- A measure with no sources opens to an empty fold (T:2304–2310; `.dk-keysec` hidden narrow): hide the fold when the notes have nothing visible.
- A tablet loaded in landscape (≥ 1024px) never registers the offline copy if rotated later (T:2556, decided once).
- `next()` from a non-Decide view does not count `view_opened: decide` while `back()` does (T:2330–2339).
- The cache key is the pathname, so `/index.html` and `/` keep separate copies (B:137): normalise.
- `openFriend` on a link with zero readable picks still counts `share_opened` and bumps `ballotta.gen` (T:1739–1747).
- A `#s…` link arriving by `hashchange` while another friend is shown leaves the Compare card on the old friend until the next `renderCompare()` (T:1737, 1750): reset at the top of `openFriend`.
- A share link's payload stays in `sessionStorage` (`ballotta.incoming`) for the tab's life; only `hideFriend` deletes it. By design, but the README's "a link being opened" reads as transient.
- `cleanPicks` (T:947) keeps keys not in `BYID` and values not in `optionsOf(c)`; every path that prints them escapes, and `pick()` on an unknown id is reachable only by DOM tampering, so harmless, but one filter would close the class.
- Duplicate `<meta name="viewport">` in the preview page (T:5 and T:9).
- Reason text is unbounded in the glance table and crib (links slice to 600 at T:1454): a pasted essay makes the printout long.
- The 4-second window applies to every same-origin request, not only navigations, and a page that arrives at 4.1 s is shown stale with the gold bar while the fresh copy lands only for the next load. Working as designed (Lane's B4); worth a longer window for `mode === 'navigate'` only, or a "newer copy ready" prompt.

---

## Waves

Each wave is one milestone and one branch of work: test-first, a remediation-audit pass on the diff, one push. Issue numbers are assigned when filed; the map below is by audit number.

**Wave 1 — "What's on the ballot is the ballot" (before Oct 19 if possible).** #3 (reproducible key, in this order), #1, #2, #5, #4 (the Tax Office questions can run in parallel; the unrouted-contest guard lands now, the code confirmations when the answers come). Deliverables: a regenerated `answer_key.json` with a test that regeneration equals the commit, the two voter-facing fixes, and a `tests/test_pipeline.py` that cross-checks the key against the PDF (choice order, partisan count, FOR/AGAINST count, no Spanish tails). The live page changes, so `LIVE_SHA` is re-pinned once (or #30 lands first and it goes away).

**Wave 2 — "Look-ups and dates" (before Oct 31).** #6, #7, #8, #9, #10, #11, #12, #18, #24, #25. Shared-page code plus the two date-bound tests (#18); one round of mutants over `lookup()`/`censusPoint()`/`nearby()`/`listFromStored`/`openRestore`; #18 first because the suite goes red on Oct 31 without it.

**Wave 3 — "The privacy promise, verified" (with wave 2 or right after).** #50 + #13, #14, #15, #16, #17, and from #38: the `e.origin` check, the `^https?://` assert, the `<!--`/U+2028 escape, `UMAMI_DOMAINS`. Plus the mutation-runner fixes that make the firewall's own mutants honest: #26, #27, #28. This is the wave to run the remediation audit twice.

**Wave 4 — "Promotion readiness" (the phone layout, before Task 13).** #19, #20, #21, #22, #23, #29, #51, #52, #53, and the layout items in #47 (map fold, menu rebuild, empty fold, rotate-to-register, `view_opened` consistency, cache key, friend reset). Ends with the cold audit's second pass (Task 12) and then Task 13.

**Wave 5 — "Process and posture" (start #34 and #31 now, in parallel with wave 1; the rest any time; mostly no page change).** #30, #31, #32, #33, #34, #35, #36, #37 and the rest of #38 (`combos_temp.json` provenance, `og.png`, `.impeccable` scope, `vote_sites.json` schema and typo, `check_sites.py` exit codes and idempotence, `lwv_measures.json` trim). #34 (CI) and #31 (county stub) first: they make every later wave cheaper.

**Wave 6 — "Consolidation" (after promotion, mostly after Nov 3).** #39, #40, #41, #42, #43, #44, #45, #46 and the remaining #47 items. Order: #39 (remove the legacy page and its 31 tests) → #40 (drop the PHONE markers, then DESK) → #41 → #42–#45 → #46. Each step shrinks the template and the test file, so later steps are smaller.

Dependencies worth respecting: #3 before #1/#2; #30 or a `LIVE_SHA` re-pin in any wave that touches the live page; #29 before Task 13; #39 only after Task 13; #34 and #31 first because every later wave runs faster and safer with them.

---

## Filed (Oct 17, evening)

Finding → GitHub issue, one milestone per wave (Waves 1–6) and labels P0–P3 plus data/page/phone/tests/process/cleanup: #3 → issue #55, #4 → issue #56, #6 → issue #57, #7 → issue #58, #8 → issue #59, #9 → issue #60, #10 → issue #61, #11 → issue #62, #12 → issue #63, #13 → issue #67, #14 → issue #68, #16 → issue #69, #18 → issue #64, #19 → issue #73, #20 → issue #74, #23 → issue #75, #24 → issue #65, #25 → issue #66, #26 → issue #70, #27 → issue #71, #28 → issue #72, #30 → issue #77, #31 → issue #78, #32 → issue #79, #33 → issue #80, #34 → issue #81, #35 → issue #82, #36 → issue #83, #37 → issue #84, #38 → issue #85, #39 → issue #86, #40 → issue #87, #41 → issue #88, #42 → issue #89, #43 → issue #90, #44 → issue #91, #45 → issue #92, #46 → issue #93, #47 → issue #76. #38 and #47 are filed as one checklist issue each. The earlier #50 went to wave 3; #51–#53 and #54 (offline-copy test gaps from the promotion audit) to wave 4.

Done before filing, so not filed: #1, #2, #5 (wave 1, commits 663feec–9c1a30f); #3 and #4 except their remainders (issues #55, #56); #21 and #29 (promotion prep, f02b029 onward); #15 (the tracker's `defer` is pinned again by the ported `phone_tracker_tag_and_link_targets`, which runs on the live page); #17 (moot since promotion: the suite tests only index.html); #22 (moot: the preview app is gone); and #47's duplicate viewport item (preview only).

## Argued down (not filed)

Kept here so the next round does not re-find them.

- ~~Unit picker keys on `CodeCat|Temp`, which may not be the full district set (T:1072).~~ Checked against the county server: `CodeCat` is the concatenation of every district code for the row (precinct, commissioner, congressional, JP, legislative, senate, SBOE, city, council SMD, ISD, ISD SMD, college, ESD, MUD, library, …), e.g. `150P01G11J02L46N14B05C04S13M03E02ALL`. It is exactly a ballot-style fingerprint; the picker and the nearby "mixed" test are right. Worth a one-line comment at T:1072 saying so.
- ~~Early-voting hours "7am–7pm every day, weekends included" may be wrong for Sundays.~~ The county's flyer for this election says 7am–7pm daily including weekends (project notes, verified Oct 14).
- ~~Milestones re-fire for a returning voter.~~ Withdrawn by the auditor on re-reading: the quiet pass records the crossed milestones before returning.
- ~~A mixed-neighbour ballot marks both sides' contests medium with nothing to decide with.~~ A UX observation, not a bug: the copy says "may or may not be on your ballot" and points at the official sample ballot. Could become a wave-6 item if Lane wants to show neighbour counts per side.
- ~~`style-src 'unsafe-inline'` and `img-src data:`.~~ Needed by the template's `style=""` attributes and the phone's inline SVG icons; `esc()` escapes quotes, no inline handlers or `javascript:` URLs exist. Tightening is possible but is a refactor, not a hole.
- ~~`rel="noopener"` without `noreferrer`.~~ The page-wide `<meta name="referrer" content="no-referrer">` covers every outbound link in current browsers.
- ~~Prototype pollution through storage or the fragment.~~ Verified not to occur: `Object.entries`/`fromEntries` copy `__proto__` as an own key; `unpackPicks` ignores non-numeric keys; `clean()` uses own-property checks.
- ~~A leaking analytics payload.~~ Two auditors tried to construct one and could not; the only residue is #13 (free-text fields and the URL path).
- ~~The hashchange path could let Umami see a fragment.~~ Umami excludes the hash and the hook strips `?#`; verified sound.
- ~~`faq_seen` is never counted on a tall window.~~ The code's own comment says so; informational.

## Documentation

Fixed in this pass (in-flow, per the audit skill): README's "`next/` redirects to the main page" (it is the phone preview); "Measures show the ballot text verbatim" qualified until #2 lands; the custom-domain section written as a future task (done Oct 14); the overstated `parse_lwv.py` claim ("stops the build if a listed site can't be credited": it prints); "measures show official sources" (59 of 93 have none); the tool dependencies and the hand-made state of `answer_key.json`; how to run the suite against the preview; the offline copy surviving "Clear everything". The phone plan's execution log gained round J (today's four commits) and this audit. The project note "Ballotta: where things live" is updated separately.

Still owed, by wave: the README's events list once #8 adds `census_unreachable`; the tracker hash (#14); the `frame-ancestors` sentence (#16); `requirements.txt` (#35); licences (#37); after wave 6, the "How it works" paragraph that still describes the old phone page's buttons.

## Verification pass on this document (Oct 17)

An independent no-context agent recomputed every count and spot-checked every P0/P1 finding against the code and the PDF. What it caught, now corrected above (kept here struck through so the next round knows):

- ~~"12 common" tests~~ → 19; the laptop and old-phone sets overlap by 7.
- ~~"all 121 single-seat contests match"~~ → 111 single-seat plus two 2-seat council contests; 121 is the candidate-contest total.
- ~~#2's fix "stop at the first `is_spanish()` line"~~ would leave 3 of the 37 tails (c126, c200, c201) in place; the fix now stops at the entity caption.
- ~~#4 "no warning anywhere"~~ (the page's data note mentions MUD No. 41) and an unfilled `c?-ids` placeholder (c193–c199); row counts restated as rows × addresses; the `MUD = M41` lead added; the TLC-fallback gap moved here from #42.
- ~~#15 "no test says so"~~: S:326 pins `defer` but is skipped on the preview; the wrong cite S:1022 → S:1066.
- ~~#17 "after promotion … no real-tracker test"~~ was backwards: the gap is before promotion.
- ~~#27 "the phone plan's log records such a transient timeout"~~: the log records an INCONCLUSIVE (the inverse case); claim dropped.
- ~~#32 "fixed port 8765" and "both runners were run side by side"~~: the port is configurable; the plan documents the test suites side by side, not the runners.
- ~~#35 "the ballot step needs pdfplumber/pypdf"~~: nothing in `source/ballot/` imports either; `pypdf` is a test dependency.
- ~~#38 "including NXDOMAIN … treat exit 6 as broken"~~: Anyiam's `000` is a TLS failure (exit 35), so the rule now names both.
- ~~#38 "the README overstates `UMAMI_DOMAINS`"~~: it does not.
- ~~#42 "138 identical LWV-shaped entries"~~ → 49 distinct shapes; ~~"42 of 45 early sites repeat"~~ → all 45 repeat, 3 differ only by typos (now listed).
- ~~#9 "empty or 404"~~ → a 200 with no data.
- Cites: #29 S:407–437 → 407–418; #31's non-lookup line cites removed; #6 gained "STEINER".
- #5's proposed count test needs a whitespace-tolerant party regex (noted).

Confirmed correct by the pass: every other count in the opening paragraph; #1's ten ids and both PDF orderings; #2's 37 ids (complete: no unlisted measure has a Spanish tail); #3's four regeneration differences; #6–#8, #10–#14, #16, #18–#26, #28, #30, #33, #34, #36, #37, #39–#41, #43–#47 against their cited lines; the CodeCat dismissal against the county server; the README and plan edits as present on disk.
