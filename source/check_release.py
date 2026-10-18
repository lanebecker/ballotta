"""Ballotta's release bookkeeping, checked (the model is TraxWax's: VERSION is the one source of truth).

    python3 source/check_release.py        # exits non-zero, saying why, if any rule below is broken

1. VERSION holds a plain semantic version (MAJOR.MINOR.PATCH, optionally -prerelease).
2. CHANGELOG.md opens with "## [Unreleased]", and its newest versioned heading, "## [x.y.z] — YYYY-MM-DD", is VERSION.
   (Merely having a heading somewhere would pass a stale or rolled-back VERSION.)
3. Every versioned heading carries a date, and the versions only go down the file (newest first, no repeats).
4. version.json, which build_site.py writes next to the page so anyone can ask the live site what it runs, is
   {"version": VERSION}.

The main build (build_site.py, not --preview) runs these before it writes anything, the test suite runs them
(tests/test_pipeline.py), and the "Release check" workflow runs them on every push to main and every pull request.
Stdlib only.
"""
import json, pathlib, re, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SEMVER = re.compile(r'[0-9]+\.[0-9]+\.[0-9]+(-[0-9A-Za-z.]+)?')
HEADING = re.compile(r'^## \[([^\]]+)\](.*)$', re.M)


def key(v):
    """Sort key for a version: 1.2.10 after 1.2.9; a pre-release (1.2.0-rc1) before its release."""
    core, _, pre = v.partition('-')
    return tuple(int(x) for x in core.split('.')) + ((0, pre) if pre else (1, ''))


def version(root=ROOT):
    return (root / 'VERSION').read_text(encoding='utf-8').strip()


def problems(root=ROOT, check_json=True):
    out = []
    try:
        v = version(root)
    except OSError:
        return ['VERSION is missing']
    if not SEMVER.fullmatch(v):
        out.append(f'VERSION {v!r} is not a semantic version such as 1.4.2')
    try:
        log = (root / 'CHANGELOG.md').read_text(encoding='utf-8')
    except OSError:
        return out + ['CHANGELOG.md is missing']
    heads = HEADING.findall(log)
    if not heads or heads[0][0] != 'Unreleased':
        out.append('CHANGELOG.md must open with a "## [Unreleased]" section, above every release')
    rel = [(h, rest) for h, rest in heads if h != 'Unreleased']
    if not rel:
        out.append('CHANGELOG.md has no versioned "## [x.y.z]" heading')
    elif rel[0][0] != v:
        out.append(f'CHANGELOG.md\'s newest release is [{rel[0][0]}] but VERSION is {v}: add a "## [{v}] — YYYY-MM-DD" section '
                   'directly under [Unreleased] (or bump VERSION)')
    bad = [h for h, _ in rel if not SEMVER.fullmatch(h)]
    if bad:
        out.append(f'CHANGELOG.md headings that are not versions: {bad}')
    undated = [h for h, rest in rel if not re.match(r'\s+—\s+\d{4}-\d{2}-\d{2}\s*$', rest)]
    if undated:
        out.append(f'CHANGELOG.md releases without a "— YYYY-MM-DD" date: {undated}')
    good = [h for h, _ in rel if SEMVER.fullmatch(h)]
    if any(key(a) <= key(b) for a, b in zip(good, good[1:])):
        out.append('CHANGELOG.md releases must run newest first, with no version twice')
    if check_json:
        try:
            got = json.loads((root / 'version.json').read_text(encoding='utf-8'))
        except (OSError, ValueError):
            got = None
        if got != {'version': v}:
            out.append(f'version.json is {got!r}, not {{"version": "{v}"}}: run python3 source/build_site.py')
    return out


if __name__ == '__main__':
    p = problems()
    for x in p:
        print('release check:', x, file=sys.stderr)
    if p:
        sys.exit(1)
    print(f'release check: VERSION {version()} has its CHANGELOG section, and version.json says so')
