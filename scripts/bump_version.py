#!/usr/bin/env python3
"""Bump the version, commit, tag, and (after confirmation) push the release.

    make bump-version                  # patch: 1.0.10 -> 1.0.11
    make bump-version PART=minor       # or VERSION_PART=minor; also: major

Before changing anything it checks that you are on main, with a clean working
tree that matches origin/main, and that the new tag does not exist yet. It then
updates pyproject.toml and src/isdi/__init__.py, turns the CHANGELOG's
"## Unreleased" heading into "## X.Y.Z (date)", commits "Release vX.Y.Z" and
creates the annotated tag vX.Y.Z. Only after you confirm does it push main and the
tag together. Pushing the tag starts .github/workflows/publish.yml, which
publishes to PyPI.

Set NO_GIT=1 to only rewrite the version files (the old behaviour).
"""

import datetime
import os
import re
import subprocess
import sys
from pathlib import Path

PARTS = {"patch", "minor", "major"}
BRANCH = "main"
REMOTE = "origin"
TARGETS = [
    (Path("pyproject.toml"), r'(?m)^(version\s*=\s*\")(?P<ver>\d+\.\d+\.\d+)(\")'),
    (Path("src/isdi/__init__.py"), r'(?m)^(__version__\s*=\s*\")(?P<ver>\d+\.\d+\.\d+)(\")'),
]
CHANGELOG = Path("CHANGELOG.md")


class ReleaseError(Exception):
    pass


def bump(ver: str, part: str) -> str:
    major, minor, patch = [int(v) for v in ver.split(".")]
    if part == "major":
        return f"{major + 1}.0.0"
    if part == "minor":
        return f"{major}.{minor + 1}.0"
    return f"{major}.{minor}.{patch + 1}"


def git(*args: str, check: bool = True) -> str:
    p = subprocess.run(["git", *args], capture_output=True, text=True)
    if check and p.returncode != 0:
        raise ReleaseError(f"git {' '.join(args)} failed: {(p.stderr or p.stdout).strip()}")
    return p.stdout.strip()


def current_version() -> str:
    versions = set()
    for path, pattern in TARGETS:
        match = re.search(pattern, path.read_text(encoding="utf-8"))
        if not match:
            raise ReleaseError(f"Version not found in {path}")
        versions.add(match.group("ver"))
    if len(versions) != 1:
        raise ReleaseError(f"Version files disagree: {', '.join(sorted(versions))}")
    return versions.pop()


def write_version(new_version: str) -> None:
    for path, pattern in TARGETS:
        text = path.read_text(encoding="utf-8")
        path.write_text(re.sub(pattern, lambda m: f"{m.group(1)}{new_version}{m.group(3)}", text, count=1),
                        encoding="utf-8")


def roll_changelog(new_version: str, today: str) -> bool:
    """'## Unreleased' -> '## X.Y.Z (date)'. Returns whether the CHANGELOG changed."""
    if not CHANGELOG.exists():
        return False
    text = CHANGELOG.read_text(encoding="utf-8")
    updated = re.sub(r"(?m)^## Unreleased\s*$", f"## {new_version} ({today})", text, count=1)
    if updated == text:
        return False
    CHANGELOG.write_text(updated, encoding="utf-8")
    return True


def preflight(tag: str) -> None:
    branch = git("rev-parse", "--abbrev-ref", "HEAD")
    if branch != BRANCH:
        raise ReleaseError(f"Releases are made from {BRANCH}; you are on {branch}.")
    if git("status", "--porcelain"):
        raise ReleaseError("The working tree has uncommitted changes. Commit or stash them first.")
    git("fetch", "--quiet", REMOTE, BRANCH, "--tags")
    behind, ahead = git("rev-list", "--left-right", "--count", f"{REMOTE}/{BRANCH}...HEAD").split()
    if behind != "0" or ahead != "0":
        raise ReleaseError(f"Local {BRANCH} differs from {REMOTE}/{BRANCH} ({ahead} ahead, {behind} behind). "
                           "Pull/push first so the release is what is on GitHub.")
    if git("tag", "--list", tag):
        raise ReleaseError(f"Tag {tag} already exists.")
    if git("ls-remote", "--tags", REMOTE, f"refs/tags/{tag}"):
        raise ReleaseError(f"Tag {tag} already exists on {REMOTE}.")


def confirm(prompt: str) -> bool:
    if not sys.stdin.isatty() and os.environ.get("RELEASE_CONFIRM") is None:
        return False   # never push without someone saying yes
    answer = os.environ.get("RELEASE_CONFIRM") or input(prompt)
    return answer.strip().lower() in {"y", "yes"}


def main() -> int:
    part = os.environ.get("VERSION_PART", "patch").lower()
    if part not in PARTS:
        print(f"Unsupported VERSION_PART: {part}. Use patch, minor, or major.")
        return 1
    try:
        old = current_version()
        new = bump(old, part)
        tag = f"v{new}"
        if os.environ.get("NO_GIT"):
            write_version(new)
            print(f"Bumped version to {new} (files only)")
            return 0

        preflight(tag)
        write_version(new)
        changed = [str(p) for p, _ in TARGETS]
        if roll_changelog(new, datetime.date.today().isoformat()):
            changed.append(str(CHANGELOG))
        try:
            git("add", *changed)
            git("commit", "--quiet", "-m", f"Release {tag}")
        except ReleaseError:
            git("reset", "--quiet", "--", *changed, check=False)
            git("checkout", "--", *changed, check=False)    # leave the tree as it was
            raise
        try:
            git("tag", "-a", tag, "-m", f"Release {tag}")
        except ReleaseError:
            git("reset", "--quiet", "--hard", "HEAD~1", check=False)
            raise
        print(f"Bumped {old} -> {new}; committed 'Release {tag}' and tagged {tag} locally.")
        print(f"Files: {', '.join(changed)}")

        if confirm(f"Push {BRANCH} and {tag} to {REMOTE}? This publishes {new} to PyPI. [y/N] "):
            try:
                git("push", "--atomic", REMOTE, BRANCH, tag)
            except ReleaseError as exc:
                print(f"Push failed; the release commit and tag {tag} are still local. {exc}")
                print(f"Retry with:  git push --atomic {REMOTE} {BRANCH} {tag}")
                return 1
            print(f"Pushed. The 'Publish to PyPI' workflow is now releasing {tag}.")
        else:
            print("Not pushed. To publish later:")
            print(f"    git push --atomic {REMOTE} {BRANCH} {tag}")
            print("To undo:")
            print(f"    git tag -d {tag} && git reset --hard HEAD~1")
        return 0
    except ReleaseError as exc:
        print(f"Release aborted: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
