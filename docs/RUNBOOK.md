# Runbook: taking back a bad release

For the weeks of voting (Oct 19 – Nov 3, 2026). A release turned out wrong (a page that breaks, a wrong contest, a
wrong vote center) and the last good release has to go back up now. Written for round-2 audit #5; rehearsed with
1.1.5, which went out by these steps.

**A rollback is a forward release.** Never reset or force-push `main`, and never ship a bare `git revert` of a release
commit: it also takes away that release's CHANGELOG section and puts the old `version.json` back, so the release check
refuses it and `ballotta.org/version.json` would name a release that isn't the one live. Revert the change, then release
it as the next PATCH.

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

The Pages workflow runs the pipeline tests (job `pipeline`), then builds the site folder and deploys (job `deploy`).
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
