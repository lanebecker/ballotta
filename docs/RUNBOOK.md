# Runbook: taking back a bad release

For the weeks of voting (Oct 19 – Nov 3, 2026). A release turned out wrong (a page that breaks, a wrong contest, a
wrong vote center) and the last good release has to go back up now. Written for round-2 audit #5; rehearsed with
1.1.5, which went out by these steps.

**A rollback is a forward release.** Never reset or force-push `main`, and never ship a bare `git revert` of a release
commit: it also takes away that release's CHANGELOG section and puts the old VERSION and `version.json` back, so pages
already open (which only hear of a higher version) would never learn of it, and `ballotta.org/version.json` would name a
release that isn't the one live. The bump check (`source/check_bumped.py`) refuses a VERSION lower than a release
already tagged. Revert the change, then release it as the next PATCH.

Each step says what "done" looks like. Don't go on until it does.

## 1. Revert the bad change

```
cd ~/path/to/ballotta && git pull --ff-only
git log --oneline -8                       # find the bad commit(s)
git revert --no-commit <bad-sha> [<another-sha> …]
```

Done: `git status` lists the reverted files. If the revert conflicts with a later commit, stop and fix by hand: this is
now an ordinary change.

## 2. CHANGELOG and VERSION

The revert also brought back the CHANGELOG and VERSION as they were before the bad release. Put them forward again:

```
git restore --source=HEAD --staged --worktree CHANGELOG.md VERSION version.json
```

Then in `CHANGELOG.md`, add a section for the next PATCH below `## [Unreleased]` and its `_Nothing yet._` (if 1.1.6
was bad, this is 1.1.7):

```
## [Unreleased]

_Nothing yet._

## [1.1.7] — 2026-10-21

### Fixed
- **1.1.6 taken back.** <one line: what voters saw wrong>. The page is 1.1.5's again.
```

The heading needs the em dash (—) and an ISO date; a hyphen or "Oct 21" is refused. Set `VERSION` to `1.1.7`.

Done: `CHANGELOG.md` opens with `[Unreleased]`, then the new section; `VERSION` says `1.1.7`. (The build in step 3
checks both and writes `version.json` to match.)

## 3. Build

```
ls -a | grep mutate-lock                   # a stale .mutate-lock (git ignores it, so git status won't show it)
python3 source/build_site.py
```

If `.mutate-lock` is there and no mutation run is going, a run was killed: compare the whole tree with git (`git diff`)
and put back anything that isn't the revert, then delete the lock. The build refuses to run while it is there.

Done: the build prints the files it wrote, `version.json` among them.

## 4. Check

```
python3 source/build_site.py --check && python3 tests/test_pipeline.py
```

Both must pass (the pipeline tests need the PDF libraries in `requirements.txt`). If time allows, also run the browser
suite with the county's recorded answers: `BALLOTTA_STUB_COUNTY=1 python3 tests/test_site.py` (about 20 minutes).

Done: `--check` is silent and the pipeline prints `N/N passed (pipeline)`.

## 5. One commit

```
git add -A && git status                   # only the reverted files, CHANGELOG.md, VERSION and the built files
git commit -m "1.1.7: take back 1.1.6 (<why>)"
```

## 6. Push

```
git push origin main
```

If the push is refused because `main` moved, `git pull --rebase origin main`, run step 4 again, and push.

## 7. Watch it deploy

```
gh run list --branch main --limit 4        # Pages, Build check, Release check, Release tag for this commit
gh run watch <Pages run id> --exit-status
```

The Pages workflow runs the pipeline tests (job `pipeline`), then, in job `deploy`, the bump check (a published file changed since tag `v<VERSION>` without a new VERSION, or a VERSION lower than a tagged release, is refused), then builds the site folder and deploys (job `deploy`).
**Red means nothing was deployed and the bad page is still live**: read the failed step (`gh run view <id>
--log-failed`), fix, and go back to step 3. Release tag makes the `v1.1.7` tag; Build check and Release check should
be green too.

If the `pipeline` job failed only because it couldn't install its two PDF libraries (PyPI down), and step 4 passed on
your machine, run the deploy by hand without it:

```
gh workflow run pages.yml --ref main -f skip_pipeline_tests=true
```

The deploy job's own build check (`--site`) still runs.

If GitHub Actions itself is down, nothing can deploy: publishing from a branch builds through Actions too. The live
page stays as it is until Actions is back (https://www.githubstatus.com); then push, or re-run the workflow.

## 8. Verify what voters get

```
curl -s "https://ballotta.org/version.json?$(date +%s)"
curl -s "https://ballotta.org/?$(date +%s)" | shasum -a 256
shasum -a 256 index.html
```

The query string skips the CDN's 10-minute cache. Done: `version.json` says `1.1.7`, and the two hashes match. Then open
ballotta.org on a phone and look at what was wrong.

Phones need nothing more: the offline copy is network-first, so an online phone takes the new page on its next load. A
page left open in a tab or a Home Screen app keeps the old one until it is reloaded.

# Runbook: results days (Nov 3, 2026 – Jan 2027)

How election results reach voters' ballots: the plan is `docs/plans/2026-10-20-results.md`; the inputs are explained
in `source/results/README.md`. Everything happens on the branch `results/next`, through one pull request ("Results
updates"). Nothing here needs a release: `results.json` is exempt from the bump check.

## Before: by Oct 30

1. Settings → Actions → General → **Allow GitHub Actions to create and approve pull requests**: on. Done: the box is
   ticked. (Without it, the Results workflow can't open its pull request.)
2. Run the Results workflow once by hand (Actions → Results → Run workflow). Done: it fetched the SOS feed (the build
   job's log says `sos: filed …`), and a "Results updates" pull request exists or the log says nothing changed.

3. The locked demo at **ballotta.org/demo/** (made-up names and results, for trying the results pages before they're
   real). To turn it on: Settings → Secrets and variables → Actions → New repository secret, name `DEMO_PASSWORD`,
   value a long password (four or five random words); then Actions → Pages → Run workflow. Every deploy after that
   rebuilds it from the results branch (`results-build`, or `main` once that's gone). After 1.4.0, `results-build`
   carries Phase 4 (the runoff), so the demo previews it; delete the branch once Phase 4 is merged. To change the password, update
   the secret and run Pages again. To take the demo down, delete the secret and run Pages: the next deploy has no
   /demo/. Nothing about it is committed, and if it fails, the site deploys without it. Its scenes: Nov 4 (the morning
   after), Nov 13 (local canvasses done), Dec 8 (state canvass done). It keeps everything under `demo:ballotta.*` keys,
   so nothing done in the demo (Clear everything included) touches the real page's picks on the same browser.
   **Once nothing more is coming on `results-build`**, delete that branch (or the demo keeps building from it and goes
   stale, showing "A newer Ballotta is available").

## Election night, Nov 3 (after 7 pm)

3. **The SOS time zone** (Task 1 finding 10): open the SOS results page and note the first "Last updated" time.
   `Nov 03 … 19:xx` or later that evening means Central; `Nov 04 … 01:xx` means UTC. If UTC, set
   `meta.sos_time_zone` to `"UTC"` in `source/results_map.json`. Done: posted times on the PR read as Austin evening.
4. **Where the counties post:** put Williamson's Nov 3 results page address in `meta.fetch.williamson` and Hays's
   cumulative PDF addresses in `meta.fetch.hays` (both unofficial and, later, official). Done: the next run's log says
   `williamson: filed …` and `hays: filed …`. Where to look (prepared Oct 21 from past elections; confirm each that
   night, since the names can change):
   - **Hays** posts PDFs under one folder per election. Nov 4, 2025's were
     `https://www.egovlink.com/public_documents300/hayscounty/published_documents/departments/elections/results/2025/1104%20General/Cumulative%20Results%20Unofficial.pdf`
     and, after its canvass, `…/Cumulative%20Results%2020251104%20Official.pdf`. So expect
     `…/results/2026/1103%20General/Cumulative%20Results%20Unofficial.pdf` now and
     `…/Cumulative%20Results%2020261103%20Official.pdf` later. Its May 2026 runoff used a different name
     (`Cumulative%20Results%20-%2020260526%20Dem%20unofficial.pdf`), so check the folder's listing on hayscountytx.gov's
     Elections page if the expected one 404s.
   - **Williamson** posts one results page on livevoterturnout.com, linked from wilcotx.gov → Elections → Election
     Results on the night. Its address includes an election number that isn't known until then; copy it from that link.

## Nov 4 morning: the first day

5. Download Travis's and Bastrop's **Detail XML** (Clarity results page → Reports → Detail XML; `detailxml.zip`).
6. **Map the county contests** (they get their keys only once the county posts): run
   `python3 source/build_results.py suggest detailxml.zip` (or ask Claude to). It prints each Ballotta contest with
   the county contests whose choices fit, best first (`17 = CITY OF AUSTIN PROPOSITION A`). Confirm each and copy
   that whole `17 = …` into the contest's `keys` in `source/results_map.json`: the name is checked against every later
   file, so a renumbered contest is held, not misread. "No fit" means none of the county's voters vote in it: confirm
   from the county's ballot and set the key to `"absent"`. A contest with no key is shown as *partial* (that county
   missing), never as zero. A file from another election (last year's, or the Dec 12 runoff's) is set aside in
   `source/results/rejected/` with the reason, and the PR lists it.
7. Then go on with the daily steps.

## Every day, Nov 4 → each canvass

8. **By 8:30 am**, download Travis's and Bastrop's Detail XML and upload each into its own folder on `results/next`
   (GitHub: `source/results/inbox/travis/` → Add file → Upload files; or attach them in a Claude chat). Done: the
   upload's commit is on `results/next`. Williamson, Hays and the SOS come by themselves (7:15 am and 5:15 pm).
9. The workflow runs on the upload and updates the "Results updates" pull request with a plain-words change list.
   - **"Numbers only"**: it merged itself and posted the list on the pinned "Results updates" issue. Nothing to do.
   - **"A state or verdict changed"**: read the list and **merge by 9 am**, every day at the same time. Hold a merge only
     for an error in the data, and say why in the pull request. Use **Create a merge commit** (never squash or rebase),
     and don't click **Delete branch** afterward (if it happens, the Results workflow recreates `results/next` from
     main). Done: Pages deployed (Actions → Pages, green).
   - **The build stopped** (red, `results build stopped: …`): it names what it couldn't decide. An unmapped choice or
     key → fix the map. A bad file → step 11. Nothing is published until it's fixed; what's live stays as it was.

## When a body canvasses

10. Add its line to `source/results/official.json` on `results/next`, with the date and a link to the canvass:
    `"city-of-austin": {"canvassed": "2026-11-12", "link": "https://…"}`. Before the meeting, `"expected": "2026-11-12"`
    shows voters when it will be official. A recount: `"recount": {"link": "https://…"}`. A runoff date:
    `"runoffs": {"c069": "2026-12-12"}`. The state canvass (Nov 21 – Dec 7) is the line `"state"`; the Legislature's
    (after Jan 12, 2027, Governor and Lt. Governor) is `"legislature"`. Done: the PR lists those contests as official.
    A canvass date outside its legal window is refused.
    After a canvass, download that county's file once more: until the files are from on or after the canvass, the
    contest says "numbers are the last unofficial count". If a county's last file is final but posted before the
    canvass, say so instead: `"final": {"travis": "2026-11-14"}` (the date of that final file).
    A county that posts no file Ballotta reads (ACC's Caldwell and Lee): type its canvassed counts from the canvass
    record, `"counted": {"c147": {"lee": {"FOR": 10, "AGAINST": 5}}}`. Until those are in, the contest is held at
    its last state and the PR says which county is missing. A county with none of the contest's voters: set its key
    in `source/results_map.json` to `"absent"`.

## When something is wrong

11. **A bad file** (a county posted a mistake, or the wrong file was uploaded): add it to
    `source/results/excluded.json` with a reason, today's date and the contests it affects. The next run ignores it;
    any verdict it changes is marked "Corrected" for voters. Never delete or edit a file in `raw/`.
12. **Anything shown is wrong and the cause isn't clear: the kill switch.** Set `"withdrawn": true` in
    `source/results/official.json` on `results/next` and merge the pull request it opens (a kill switch is never
    numbers-only, so it waits for you: merge at once). Every result disappears from every ballot with "Results are
    paused…" (W52). Set it back to `false` to restore. For a fault in the page's results code, not the data, roll back
    with `RESULTS_LIVE = False` in `source/build_site.py`: a release (the steps above).

## After

13. The schedule stops on Dec 10. Governor and Lt. Governor stay "becomes official when the Legislature canvasses" until
    January: add the `"legislature"` line then.
