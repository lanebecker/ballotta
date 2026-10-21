# Ballotta results back end: deep cold audit (Oct 21, 2026)

Scope: `source/{fetch_results,build_results,results_rules,results_parse,check_results}.py`, `results_map.json`,
`source/results/`, `check_bumped.py`/`build_site.py` (results.json), `.github/workflows/*`, `docs/RUNBOOK.md`
(results days), `docs/plans/2026-10-20-results.md`, `tests/test_results.py`, `tests/test_pipeline.py`,
`tests/mutate_backend.py`. Branch `results-build` @ 63606f2. Both suites pass (42/42 results, 26/26 pipeline).

How I checked: I read the code. I ran probe scripts that import the repo's modules and build in temp dirs
(`scratchpad/deep-backend/probe1.py`, `probe2.py`, `probe3.py`; nothing in the repo was written). I read GitHub state
through the REST API: main's `results.json`, PR #133 and the workflow runs. I fetched the live SOS feed twice, and
read Election Code ch. 65 and ch. 67 (the TLC PDFs) and §2.002 (Justia).

Severity: **H** = voters see something wrong, or nothing publishes; **M** = a real operational or security risk;
**L** = cleanup.

---

## High

### 1. From Nov 4 at midnight until Lane's first merge, voters see "No votes reported yet" on all 31 state races (H)
- **Where:** `results.json` on main (seq 2, from commit 32af8df "Results: seq 1" plus 4e89cae). The page renders it
  at `source/template-travis.html:2374`. The plan (L207–208, L502) says a placeholder with `"contests": {}`.
- **What's wrong:** the published file has 42 SOS contests: 31 are `counting`/`none` and 11 are `unopposed`, all
  "Texas Secretary of State, posted 2026-10-16T16:12". The page shows results from 00:00 Nov 4, Austin time. The first
  scheduled run is at 13:15 UTC (7:15 am), and moving from counting to unofficial is a state change, so it waits for
  Lane's merge (about 9 am).
- **Scenario:** a voter checks at 6 am on Nov 4, the busiest time. The US Senate and every other statewide race says
  "No votes reported yet", posted Oct 16, and the All Travis County results sheet says the same. The real count is
  already on the SOS feed.
- **How I confirmed:** `gh api repos/lanebecker/ballotta/contents/results.json?ref=main` gives seq 2 with 42
  contests, counted by state and verdict.
- **Fix:** before Nov 3, publish an empty-contests file (seq 3) on main. Or have the build (or the page) leave out
  `counting` entries whose newest source was posted before Election Day. Also consider an extra scheduled fetch around
  05:15 UTC on Nov 4 so the morning PR is ready when Lane wakes up.

### 2. The runbook's fix for a bad file (`excluded.json`) stops the build when the file excluded is a source's newest (H)
- **Where:** `source/build_results.py:242-260` and `source/check_results.py:229-236`. Runbook step 11.
- **What's wrong:** once the newest Travis (or Williamson, Hays) file is excluded, every contest that used it shows an
  earlier posted time. `check_against` refuses that unless the entry has `corrected` set. The build sets `corrected`
  only for contests that are both listed in the entry's `contests` **and** whose verdict changed. Travis feeds about
  170 contests, so in practice the build always stops with "the built file fails the check: … posted time went
  backwards".
- **Scenario:** Travis posts a botched update at 10 am on Nov 6. Lane excludes it as the runbook says. Every run then
  fails until Travis posts a newer file. Meanwhile the bad numbers stay live, because they were already merged.
- **How I confirmed:** `probe1.py: probe_exclude_latest_no_verdict_change` gives `Problem … Travis County's posted
  time went backwards (2026-11-06T09:00 → 2026-11-05T09:00)`. The existing ledger test passes only because it also
  removes a canvass, which flips the verdict.
- **Fix:** when an exclusion rolls a source back, work out the affected contests from the excluded file itself (every
  contest keyed to that source). Then either set `corrected` on all of them, or tell `check_against` which labels were
  rolled back on purpose. Add a test: exclude the newest file with no verdict change.

### 3. An old correction gets pinned on a later, ordinary change, and voters are told "An earlier version on Ballotta was wrong" (H)
- **Where:** `source/build_results.py:242-245` and `259-260`. The page shows it at `template-travis.html:2473`, `2499`
  and `2525`.
- **What's wrong:** each `excluded.json` date stays "pending" for its contests until a build happens to change their
  verdict. If the exclusion didn't change the verdict when it was added (for example, an older file or a duplicate),
  the next ordinary change gets marked `corrected`. That might be Passing → Passed at the canvass, or Leading → Too
  close.
- **How I confirmed:** `probe1.py: probe_late_correction_mislabel`. An exclusion dated Nov 6 with no verdict change,
  then the canvass on Nov 10: c148 comes out Passed with `corrected = "2026-11-06"`.
- **Fix:** apply a correction only in the first build after the exclusion is added. Record it, for example as an
  `applied_seq` on the entry, or keep the list of exclusions already applied in `results.json`. The plan's own rule
  (L205–206, Task 6) is "ordinary movement never called a correction"; no test or mutant checks it with an exclusion
  present.

### 4. One bad input stops all 214 contests; the plan promises "that county waits; the rest goes on" (H)
- **Where:** every `raise Problem` in `build_results.py`: L63-65 (inbox), L87 and L93-94 (`latest`), L108, L116, L119
  and L123 (`slice_of`), L178, L182, L191 and L201 (`entry`), L280-282 (the check). The plan says otherwise at L508-509
  and L536-538.
- **What's wrong:** any one of these aborts the whole build, SOS included:
  - an unmapped or misspelled choice;
  - a key the file doesn't have;
  - two files posted in the same minute;
  - a canvass entered while a county is missing;
  - an "unsure" rule that disagrees at the canvass (c131 has 3 candidates; six refunding-bond measures);
  - a canvass date outside the window;
  - a bad inbox file.
- **Scenario:** on Nov 4 Lane must set about 280 keys by hand by 9 am: about 172 Travis, 52 Williamson, 24 Hays,
  4 Bastrop and 25 SOS-to-Travis. One typo means nothing publishes. The 5:15 pm SOS update is lost too.
- **How I confirmed:** I read the code. `probe2.py` shows the "unsure" measure at the canvass and the ACC canvass
  (finding 6) each stopping the whole build.
- **Fix:** catch `Problem` per contest in `build()`. Keep the previous published entry, or leave the contest out. List
  it in the PR as "held: <reason>" and force `verdict_changed` so Lane sees it. In `latest()`, fall back to that
  source's previous good file and flag it.

### 5. A bad file in the inbox blocks every later run, and `excluded.json` can't name it (H)
- **Where:** `build_results.py:48-72` (`file_inbox` never reads `excluded.json`; it raises before `unlink`).
  `results.yml` step "File Lane's downloads". Runbook steps 9 and 11.
- **Scenario:** Lane uploads Clarity's rate-limit HTML page, a Bastrop file whose `<Region>` isn't "Bastrop", or a
  file from the wrong election. Every later run fails at the first step, including the scheduled SOS fetches. The
  runbook says to add it to `excluded.json`, but that only covers paths under `raw/`.
- **How I confirmed:** `probe1.py: probe_bad_inbox_file_blocks_everything` fails even with an `excluded.json` entry
  for the inbox path.
- **Fix:** move an inbox file that won't parse to `raw/<county>/rejected/…` with the reason, print it in the PR body,
  and carry on. The runbook should also say how to clear the inbox.

### 6. ACC (c117–c119): Lee and Caldwell never have a file, so entering ACC's canvass stops the whole build, and until then the ACC races can't be called (H)
- **Where:** the `results_map.json` entries for c117–c119: `electorate` includes caldwell and lee, and
  `registered: {caldwell: 28491, lee: 12262}`. `build_results.py:155-163` and `177-178`.
- **What's wrong, part 1:** the slack is about 40,753 votes, using whole-county registration, so any ACC race with a
  margin under about 41k votes stays "Too close to call". With only Travis loaded, a 60k–30k race and a 240k–200k race
  (54.5%) both come out `partial / too_close`.
- **What's wrong, part 2:** once Lane enters ACC's canvass line, the build stops: "canvassed … but ['Caldwell County',
  'Lee County'] aren't loaded". The plan's "ACC's own canvass for official numbers" has no input or parser.
- **How I confirmed:** `probe2.py: probe_acc_canvass`.
- **Fix:**
  - Add a way to enter ACC's canvass totals by hand, in `official.json` or in a small canvass file, and use them once
    ACC has canvassed.
  - Use the registration of ACC's *taxing district* inside Caldwell and Lee, not whole-county registration.
    Elgin ISD's and Hays CISD's slices are probably small; this needs checking.

### 7. Austin council districts (c066–c070) and the other 58 multi-county contests stay "No call yet" if any one county is missing (H)
- **Where:** `results_map.json`. None of the 59 multi-county contests has a `registered` value for a non-Travis
  county, except ACC. c066–c070 have `possible: [williamson, hays]` with keys `null`. The rules are at
  `build_results.py:156-163`. The runbook (steps 6 and 10) never mentions `"absent"`, which only appears in a
  `build_results_map.py:173` comment.
- **What's wrong, part 1:** a missing key or file with unknown registration means slack = None, so no verdict. Unless
  Lane sets `"absent"` for counties with no voters in a district, the five council races (majority races, the ones that
  feed the Dec 12 runoff feature) say "No call yet" until the canvass. At the canvass the build then stops (finding 4).
- **What's wrong, part 2:** a Hays fetch failure blanks the verdict on every Austin contest, though Hays's Austin slice
  had 565 registered voters (Task 1).
- **Fix:**
  - Document `"absent"` in runbook step 6.
  - Have `suggest()` say "no such contest in this county's file → absent?".
  - Put the known small registrations in the map's tables, for example Hays 565 for City of Austin contests.

### 8. "Official · numbers are the last unofficial count" never goes away for local contests (H)
- **Where:** `build_results.py:169-170` (`if done and rep["posted"][:10] < done: official_numbers = False`). Runbook
  step 10 ("download that county's file once more").
- **What's wrong:** counties post their final files *before* the entity canvasses from them. The repo's own data
  shows this:
  - Travis's final Detail XML is stamped Nov 12, 2025 at 3:00 PM;
  - Hays's official PDF Run Date is Nov 10, 2025;
  - the City's canvass backup for Prop Q is dated Nov 17, 2025.

  Downloading again doesn't help, because Travis doesn't post a new version after the city's canvass. So every
  City/ISD/MUD contest keeps the W11 caveat after it turns Official, even with exactly the canvassed numbers.
- **How I confirmed:** the fixture timestamps (`test_results.py:199`, `:263`) and the plan's L352-355. The test
  `official_only_through_its_own_canvasser` asserts this behaviour.
- **Fix:** base it on each *county's* final file rather than the entity's canvass date. For example, Lane enters
  `"counties": {"travis": "2026-11-1x"}` in `official.json` when Travis canvasses or posts its final count, and Hays's
  PDF says "Official Results" (`parse_hays` already returns `official`, but nothing uses it). Optionally check the sum
  against the entity's canvass totals.

### 9. County Clerk (c053) will say "Unopposed", or stop the build (H)
- **Where:** the `results_map.json` entry for c053 has `write_ins: []`, but the ballot (answer key) has a Write-in
  line, so a declared write-in exists. Rules: `results_rules.py:39-41` and `59-61`.
- **What's wrong:**
  - If Travis prints only a generic "Write-in" line, it is dropped (`GENERIC_WRITE_IN`) and `is_unopposed` comes out
    true, so voters see "Unopposed", then "Elected". The plan (V12, L224-226) says this contest must not be unopposed.
  - If Travis prints the write-in candidate's name, `slice_of` raises and the whole build stops on Nov 4 morning.
- **How I confirmed:** the map and answer key (c053 is the only contest with a Write-in line and no declared names).
  The map test only checks the reverse direction (`test_results.py:596`).
- **Fix:** get the declared write-in's name from Travis County Elections before Nov 3. Add a rule and a map test:
  a ballot with a Write-in line but no declared name is never "unopposed". Add the reverse map assertion.

### 10. Measure keys can be wrong without any error, and no parser checks which election a file is from (H)
- **Where:** `build_results.py:102-124` (`slice_of`), `:325-339` (`suggest`); `results_parse.py:76-119`, `221-250`,
  `260-305`, `133-159`.
- **What's wrong, part 1:** all 93 measures are FOR/AGAINST, so any measure key "fits". `suggest` on Travis's 2025
  file offers "State of Texas Proposition 1; City of Austin Proposition Q" for every measure from c071 to c091 and
  beyond. A wrong key shows another proposition's numbers, with no error.
- **What's wrong, part 2:** no parser checks the election. Clarity has `<ElectionDate>`, the SOS `Home` has
  `ElecDate: "11032026"`, and the Hays header and the Williamson title name the election, but none is read. A Nov 2025
  file (still on Clarity), a Dec 12 runoff file, or last year's Hays URL is accepted. Clarity keys are small integers
  ("0004") and Hays keys are titles, so measures match silently.
- **How I confirmed:** I ran `build_results.suggest` on the fixture (`suggest.out`), and `probe_wrong_election`
  parsed a Nov 2025 file as Travis's.
- **Fix:**
  - Store each county's contest name in the map next to its key, and refuse a key whose normalized name doesn't match
    (entity and proposition letter).
  - Rank `suggest` by title.
  - Make every parser refuse a file whose election date isn't 2026-11-03.

---

## Medium

### 11. Two different files posted in the same minute stop the whole build; the Williamson page will likely do this (M)
- **Where:** `build_results.py:92-94` (the behaviour has a test). Fetching: `fetch_results.py:34-42`.
- **What's wrong:** Williamson's "posted" time is the vendor's "Website Updated". The fixture for the Nov 2025
  election is stamped 9/30/2026, so the vendor re-stamps old pages. A server-rendered 6.9 MB page that changes any byte
  between fetches without a new stamp gives a "both posted at …: exclude one" `Problem`. That stops everything, every
  run, until Lane excludes a file, and excluding the newer one then trips finding 2. Each changed copy also adds about
  6.9 MB to git.
- **How I confirmed:** `probe_same_minute_different_bytes`. The SOS feed is stable: I fetched it twice and got
  byte-identical copies, hash `0f20843c…`, the same as the file already filed.
- **Fix:** in `keep()`, `file_inbox()` and `latest()`, compare the parsed contests rather than bytes. Same contents:
  keep one, and don't file a duplicate. Different contents in the same minute: hold that source only.

### 12. The self-merge isn't tied to the commit that was checked, and a merge during a run reuses a seq (M)
- **Where:** `results.yml:98-113` and `138`.
- **What's wrong, part 1:** `gh pr merge "$N" --merge` merges whatever `results/next` holds at that moment, even a
  commit pushed after the build job checked it.
- **What's wrong, part 2:** the publish job never checks that `origin/main:results.json` is still the copy the build
  used as `prev`. If Lane merges the PR while a run is building (upload → PR updated → Lane merges → a second upload's
  run is still going), the second run publishes a *different* file with the *same* seq. The page compares
  `seen.seq < R.seq` (`template-travis.html:2496`), so "Since you last looked" never reports that second change.
- **Fix:**
  - Add `--match-head-commit "$(git rev-parse HEAD)"` to the merge.
  - Put the prev blob SHA in the artifact. In the publish job, stop (or re-run) if main's `results.json` blob differs.
  - The non-fast-forward reset push at L142 can fail after the merge and before the digest. Do the digest first, or
    make the reset tolerate a newer upload.

### 13. The publish job (with write access) trusts the read-only job's output completely (M)
- **Where:** `results.yml:54` (pip install with no hashes; pdfplumber's Pillow and pypdfium2 and pdfminer's
  cryptography and charset-normalizer are unpinned), `:105` (`git apply` of any paths), `:124` and `:131`
  (`verdict_changed` read from the artifact).
- **What's wrong:** the build job installs packages from PyPI and parses third-party PDFs and HTML. If any of that is
  compromised, it can write a `results.patch` that changes `index.html`, `sw.js`, `VERSION` and `CHANGELOG` (anything
  except workflow files) and a `changes.json` saying "numbers only". The publish job applies it, self-merges into main
  and starts Pages. `check_bumped` passes, since VERSION is new. The two-job split is meant to stop exactly this, and
  it doesn't.
- **Fix:** in the publish job:
  - use `git apply --include='source/results/*' --include=results.json`, and refuse if
    `git diff --cached --name-only` lists anything else;
  - recompute `verdict_changed` with stdlib code (compare `state`/`verdict`/`leaders`/`runoff`/`note`/`withdrawn`
    against main's file), and run `check_results.py --prev` there too.

  Pin the transitive dependencies with `--require-hashes`.

### 14. Pages: code on the unreviewed `results-build` branch can overwrite any file on ballotta.org (M)
- **Where:** `pages.yml:58-73` (the demo job runs `results-build`'s `build_demo.py` and `demo_lock.mjs`, with
  `DEMO_PASSWORD`) and `:105-110` (`download-artifact … path: _site`, *after* `build_site.py --site _site` ran its
  checks).
- **What's wrong:** whatever the branch's scripts put under `locked/` replaces the published files: `index.html`,
  `sw.js`, `results.json`. That gets past `check_bumped`, `build_site --check` and every review on main. The demo
  rebuilds from that branch on every deploy, including the twice-daily self-merge deploys.
- **Fix:** download the demo into a temp folder. Check it holds only `demo/index.html`, and copy just that file into
  `_site/demo/`.

### 15. The kill switch can be held up by unrelated failures, and turning it off erases the correction record (M)
- **Where:** `build_results.py:233-236`. The reports are parsed before `withdrawn` is read.
- **What's wrong, part 1:** a bad raw file or a same-minute duplicate stops the withdrawal build. So do a bad inbox
  file, a failed pip install or the tests.
- **What's wrong, part 2:** after a pause and restore, every contest has `corrected` reset to null and `changed`
  reset. The posted-time check can't fire either, because the previous file has no contests.
- **How I confirmed:** `probe3.py`.
- **Fix:**
  - Read `withdrawn` before parsing anything.
  - Add a manual fallback to the runbook: commit a hand-written withdrawn `results.json` on `results/next`. It passes
    the deploy job's check.
  - Say how long it takes: about 15–25 minutes, including the CDN.
  - While paused, keep a small ledger per contest (`corrected`, `changed`, last verdict).

### 16. Numbers-only updates almost never merge themselves (M)
- **Where:** `results.yml:106-133`. The plan claims otherwise at L83-85 and L544.
- **What's wrong:** the one PR compares everything with main. Any verdict change still waiting for Lane holds every
  numbers-only update behind it. From Nov 4 to Nov 17 verdicts move almost every day, so "Lane is busy: numbers-only
  updates still go live" mostly won't happen.
- **Fix:** when there are verdict changes, also build an "auto" `results.json` in which every contest whose verdict
  changed keeps its last published entry. Self-merge that one, and leave the full version in Lane's PR.

### 17. Fetching: no retries, failures only in the log, and "every fetch failed" also stops Lane's upload (M)
- **Where:** `fetch_results.py:26-31` and `80-81`. The workflow step at `results.yml:57-58`.
- **What's wrong:** one timeout means no data from that source until the next run, possibly 10 hours later. If every
  fetch fails (the SOS is down, Williamson isn't set yet, Hays's URL returns 404 after deletion), the job fails before
  building, so Lane's Travis and Bastrop uploads in that run aren't published either. Errors appear only in logs nobody
  reads.
- **Fix:** retry 3 times with backoff. Never fail the job because a fetch failed. Put the fetch errors, and each
  source's age, in the PR body and digest.

### 18. The SOS time zone isn't checked (M)
- **Where:** `results_parse.py:141-145`. Plan L388-390 says "Until then the workflow records both readings"; that
  isn't implemented. Runbook step 3.
- **What's wrong:** if the zone is set wrong, SOS posted times are 5–6 hours off. A "7:30 pm" update can even show a
  time later than the fetch.
- **Fix:** record the response's `Date` header (the server sends one). Refuse, or pick automatically, the reading that
  would be after the fetch time. Also check `ElecDate`.

### 19. Hand edits to the map make the build job's tests fail, so nothing publishes (M)
- **Where:** `build_results_map.py:227-239` and `250-252`; `test_results.py:580-583`, which runs in the Results build
  job. Runbook step 6 and the `Problem` messages tell Lane to edit `results_map.json` by hand.
- **What's wrong:** the check compares exact text. Each of these makes `test_results` fail, with "change the tables,
  then rerun it":
  - a `spell` added next to `keys`;
  - an editor reformat;
  - a hand-set `registered`, which isn't preserved at all.
- **How I confirmed:** I wrote a scratch script for these cases; it returns `False` for each.
- **Fix:** have the workflow normalize the map (run `build_results_map.py`) before the tests, or compare parsed JSON.
  Keep `registered` and `"absent"` overrides. Document both in the runbook.

### 20. Parsers too tied to one file format; some formats never rehearsed (M)
- **Hays:** `results_parse.py:254-255`. `HAYS_ROW` and `HAYS_CAST` require exactly three vote-type columns. A general
  election report with a Provisional column (or any fourth column) gives BadFile, so Hays never loads: 24 contests stay
  partial, with no call because the registration is unknown. Fix: accept one or more pairs and take the last as the
  total.
- **Williamson:** `:239-249`. A contest with no choices parsed is accepted when the pie chart is also missing. It then
  stops the whole build in `slice_of`. My probe confirmed it (`probe_williamson_no_pies`). Fix: refuse contests with no
  choices.
- **Bastrop:** `CLARITY_COUNTIES` assumes `<Region>Bastrop</Region>`. It was never rehearsed and has no fixture. If it
  differs, finding 5 applies.
- **SOS canvass PDF:** the parser has only been tested on a primary runoff report (no party column, no write-ins). A
  failure is handled safely, falling back to "numbers are the last unofficial count".
- **Fix overall:** fixtures from a Nov 2024 general election (Bastrop Clarity, Hays cumulative, SOS canvass).

### 21. Feed and canvass report share one label, so the state canvass can stop the build (M)
- **Where:** `results_parse.py:19-20` (both labelled "Texas Secretary of State"); `check_results.py:233-236`.
- **What's wrong:** when Lane enters the state canvass, a contest's source becomes the canvass PDF, posted at the time
  printed at its foot. If that is earlier than the feed's latest `LastUpdatedTime`, the check sees the time "go
  backwards" and stops.
- **Fix:** use a separate label, or skip the check when the source changes kind.

### 22. The Dec 12 runoff is not built on the back end (M)
- **Results have no place to go:** `check()` requires `choices` to equal the full ballot (`check_results.py:132-134`),
  so a two-candidate runoff result can't be stored. It needs its own entries or contest ids.
- **The canvass window check refuses it:** `check_results.py:192-193` allows local canvasses only Nov 6–17, and
  runoff canvasses fall around Dec 15–23.
- **The cron stops on Dec 10:** `results.yml:24-25`. The SOS canvass report may also appear after Dec 10; nothing
  fetches it then.
- **Sources aren't kept apart by election:** `raw/<source>/` and the single `meta.fetch.williamson` URL. A runoff
  Clarity, Williamson or Hays file becomes "latest" for the Nov 3 contests, so their keys go missing and the whole
  build stops. Uploading the runoff file early therefore breaks Nov 3 results.
- **The runbook has no runoff steps.** The runoff plan's step 6 is "later".
- **Fix:** namespace raw files and keys by election date, give runoff results their own entry shape, extend the cron
  to about Dec 20, and add runbook steps.

---

## Low, and efficiency

### 23. Runbook and plan disagree with the code (L)
- **Step 11:** exclusion cannot fix an inbox file (finding 5) or a newest file (finding 2).
- **Step 6:** nothing on `"absent"`, `spell`, write-ins or normalizing the map (findings 7 and 19).
- **Step 10:** "download once more" won't clear W11 (finding 8).
- **Step 9:** "The build stopped … what's live stays" is right, but the plan's Risks say "that county waits"
  (finding 4).
- **Plan Risks L534-535:** say official state numbers stay Unofficial until a hand download. The code shows them
  Official with the last unofficial numbers instead (Lane's later answer).
- **`source/results/README.md`:** says "provisionals: Nov 16", but `late_until` is 2026-11-17.
- **Step 13:** no scheduled fetch after Dec 10, though the SOS canvass report can come later.
- **"Results updates" PR #133:** shows a failed "Release check" and "Build check" with zero jobs (runs 39505082893
  and 39505082894, triggered by github-actions[bot]). Lane may read that as failing checks. Note it in the runbook.

### 24. Tests and mutants miss key behaviours (L/M)
- **Exclusions:** no test excludes a newest file without a verdict change (finding 2). No test checks that a later
  ordinary change isn't marked corrected once an exclusion exists (finding 3). By inspection, the mutants "drop
  `old["verdict"] != e["verdict"]`" and "drop `corrections[cid] > old.corrected`" would survive.
- **No mutants on:** `check_results.py` itself, the `missing and done` stop, the SOS official-numbers fallback,
  `travis_only`, `notes()` depends_on, the canvass windows, or `fetch_results.keep` (parse before filing).
- **The workflow isn't tested:** self-merge, reset and races were only "rehearsed locally".
- **Fixtures:** the Williamson fixture is one contest, 4 KB (the real page is 6.9 MB). Hays has only an official PDF.
  Bastrop has none.
- **Test coupling:** `test_results.py:580-583` (the map must be byte-identical) blocks publishing data, though it's a
  code check.
- **Mutation runner:** `mutate_backend.py` takes no `.mutate-lock`, so a killed run can leave a mutant in
  `source/results_*.py` that nothing local notices. The tests in CI would catch it.

### 25. Efficiency and refactors (L)
- **`latest()` re-parses every file every run:** `build_results.py:75-95` parses every raw file of every source. Over
  37 days that's every SOS feed (1.6 MB each), every Williamson page (6.9 MB) and every Hays PDF (about 1.7 s each).
  Sort by the directory name, which already holds the posted time, and parse newest first.
- **Repo growth:** binary raw files grow the repo, and every `fetch-depth: 0` checkout in Pages, Release check and
  Results gets slower. Store files only when their parsed content changes (finding 11), and consider gzip.
- **Test copies `raw/`:** `test_pipeline.py:611` copies the whole repo, including `raw/`, on every Pages and Results
  run. Add `raw` to the ignore patterns.
- **`changed` is unused:** it's written to every entry but the page never reads it; the page keeps its own snapshot
  (`template-travis.html:2485-2501`). Drop it or use it.
- **No seats cross-check:** `seats()` comes from the title regex, and nothing compares it with Clarity's `voteFor` or
  Williamson's "VOTE FOR N". Checking it in `slice_of` would catch an answer-key error.
- **Canvass window too loose:** the local window check allows Nov 6. By §67.003(b) a canvass can't come before the
  provisional count (by Nov 16 under §65.051(a-1)) or the overseas-ballot count. Harmless, but the lower bound is loose.

---

## Legal claims checked
- **§67.003(b)–(c) with §65.051(a-1):** for an election on the general-election date, provisional ballots must be
  counted by the 13th day (Nov 16) and the local canvass held by the 14th (Nov 17). Matches `LOCAL_BY`.
- **§67.012(a)(2):** the state canvass falls between the 18th and 33rd days, Nov 21 to Dec 6. Dec 6 is a Sunday, so
  §1.006 makes it Dec 7. Matches.
- **§67.010 and §67.011:** the Governor canvasses statewide and district offices; the Legislature canvasses Governor
  and Lt. Governor. Matches.
- **§2.002(h):** the tie procedure doesn't apply to executive-department offices under art. IV §1 (Governor, Lt.
  Governor, Comptroller, Land Commissioner, AG), so c006–c010 go to the Legislature. Matches.
- **§2.023 (ties for second):** not verified; the page fetch was refused.
- **Unchecked:** Manor's charter majority rule, Pflugerville's (inferred) and TCAD's are flagged in the map itself as
  UNVERIFIED or INFERRED.

## Probe files
`/tmp/claude-0/-home-claude/83046943-1852-502f-a4b7-3e94315f60c5/scratchpad/deep-backend/probe1.py`, `probe2.py`,
`probe3.py`, `suggest.out`, `sosdl/` (the live SOS feed, two identical copies).
