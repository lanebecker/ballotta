"""A push that changes what the site publishes must bump VERSION (round-2 audit #19, #117).

    python3 source/check_bumped.py        # exits non-zero, naming the files, if the published site changed since v<VERSION>

Since 1.1.6 a page left open (a Home Screen app, a laptop tab) learns of a newer release only from a higher VERSION in
version.json, so a fix pushed without a bump would never reach the phones already using Ballotta, and version.json
would name a release that isn't what's live. Once the Release tag workflow has tagged v<VERSION>, any difference
between that tag and HEAD in the files the site publishes (build_site.site_files()) is refused. A release push itself
passes: its VERSION is new, so its tag doesn't exist yet. Docs, tests and sources that aren't published pass.

The Pages workflow runs this before it deploys, and the Release check workflow on every push. Both check out the full
history and tags. Stdlib and git only.
"""
import pathlib, subprocess, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'source'))


def changed_since_tag(root=ROOT):
    """The published files that differ from tag v<VERSION>, or [] when that tag doesn't exist yet. Stops when VERSION is
    lower than a release already tagged (a bare `git revert` of a release: pages left open would never hear of it), or
    when it can't see the history and tags it compares with (a shallow or tag-less clone would pass anything) (Pass 1)."""
    import build_site, check_release
    v = check_release.version(root); tag = 'v' + v
    git = lambda *a: subprocess.run(['git', *a], cwd=str(root), capture_output=True, text=True)
    shallow = git('rev-parse', '--is-shallow-repository')
    if shallow.returncode != 0 or shallow.stdout.strip() != 'false':
        sys.exit('bump check: needs the full git history and tags (actions/checkout with fetch-depth: 0)')
    tags = [t[1:] for t in git('tag', '-l', 'v*').stdout.split() if check_release.SEMVER.fullmatch(t[1:])]
    if not tags:
        sys.exit('bump check: no release tags (v*) here: fetch them (actions/checkout with fetch-depth: 0)')
    higher = [t for t in tags if check_release.key(t) > check_release.key(v)]
    if higher:
        sys.exit(f'bump check: VERSION {v} is lower than the release already tagged v{max(higher, key=check_release.key)}. '
                 'A rollback is a forward release: see docs/RUNBOOK.md.')
    if git('rev-parse', '-q', '--verify', 'refs/tags/' + tag).returncode != 0:
        return tag, []
    r = git('diff', '--name-only', tag, 'HEAD', '--', *[str(f) for f in build_site.site_files()])
    if r.returncode != 0:
        sys.exit(f'bump check: could not compare with {tag}: {r.stderr.strip()}')
    return tag, r.stdout.split()


if __name__ == '__main__':
    tag, changed = changed_since_tag()
    if changed:
        sys.exit(f'bump check: the published site changed since {tag} ({", ".join(changed)}), but VERSION is still '
                 f'{tag[1:]}. Pages left open only hear of a higher version: bump VERSION and add its CHANGELOG section.')
    print(f'bump check: nothing published differs from {tag}, or {tag} is a new release not tagged yet')
