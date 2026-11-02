"""scripts/bump_version.py: bump, commit, tag, and push only after confirmation."""

import os
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "bump_version.py"


def git(cwd, *args):
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=True).stdout.strip()


@pytest.fixture
def repo(tmp_path):
    """A checkout of a tiny project on main, with a bare repo as 'origin'."""
    origin = tmp_path / "origin.git"
    work = tmp_path / "work"
    subprocess.run(["git", "init", "--quiet", "--bare", "-b", "main", str(origin)], check=True)
    subprocess.run(["git", "init", "--quiet", "-b", "main", str(work)], check=True)
    git(work, "config", "user.name", "Test")
    git(work, "config", "user.email", "test@example.com")
    git(work, "config", "tag.gpgSign", "false")
    git(work, "config", "commit.gpgSign", "false")
    (work / "src" / "isdi").mkdir(parents=True)
    (work / "pyproject.toml").write_text('[project]\nname = "isdi-scanner"\nversion = "1.0.10"\n')
    (work / "src" / "isdi" / "__init__.py").write_text('__version__ = "1.0.10"\n')
    (work / "CHANGELOG.md").write_text("# Changelog\n\n## Unreleased\n\n- New thing\n\n## 1.0.10\n")
    git(work, "add", ".")
    git(work, "commit", "--quiet", "-m", "init")
    git(work, "remote", "add", "origin", str(origin))
    git(work, "push", "--quiet", "-u", "origin", "main")
    return work, origin


def run(work, answer=None, part="patch", stdin=subprocess.DEVNULL, **env):
    environment = {**os.environ, "VERSION_PART": part, **env}
    environment.pop("RELEASE_CONFIRM", None)
    if answer is not None:
        environment["RELEASE_CONFIRM"] = answer
    return subprocess.run([sys.executable, str(SCRIPT)], cwd=work, env=environment,
                          capture_output=True, text=True, stdin=stdin)


def remote_tags(origin):
    return git(origin, "tag", "--list")


def test_bump_parts():
    sys.path.insert(0, str(SCRIPT.parent))
    try:
        import bump_version
    finally:
        sys.path.pop(0)
    assert bump_version.bump("1.0.10", "patch") == "1.0.11"
    assert bump_version.bump("1.0.10", "minor") == "1.1.0"
    assert bump_version.bump("1.9.10", "major") == "2.0.0"


def test_confirmed_release_is_committed_tagged_and_pushed(repo):
    work, origin = repo
    r = run(work, answer="y")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "1.0.10 -> 1.0.11" in r.stdout and "Pushed" in r.stdout
    assert remote_tags(origin) == "v1.0.11"
    assert git(origin, "log", "-1", "--format=%s", "main") == "Release v1.0.11"
    assert git(work, "cat-file", "-t", "v1.0.11") == "tag"              # annotated
    assert 'version = "1.0.11"' in (work / "pyproject.toml").read_text()
    assert '__version__ = "1.0.11"' in (work / "src/isdi/__init__.py").read_text()
    changelog = (work / "CHANGELOG.md").read_text()
    assert "## Unreleased" not in changelog and "## 1.0.11 (" in changelog
    assert git(work, "status", "--porcelain") == ""


def test_declined_release_stays_local(repo):
    work, origin = repo
    r = run(work, answer="n", part="minor")
    assert r.returncode == 0
    assert "Not pushed" in r.stdout and "git push --atomic origin main v1.1.0" in r.stdout
    assert git(work, "tag", "--list") == "v1.1.0"
    assert remote_tags(origin) == ""
    assert git(origin, "log", "-1", "--format=%s", "main") == "init"


def test_no_terminal_means_no_push(repo):
    work, origin = repo
    r = run(work)                       # stdin is not a terminal and no RELEASE_CONFIRM
    assert r.returncode == 0 and "Not pushed" in r.stdout
    assert remote_tags(origin) == ""


@pytest.mark.parametrize("setup,message", [
    (lambda w: (w / "stray.txt").write_text("x"), "uncommitted changes"),
    (lambda w: git(w, "checkout", "--quiet", "-b", "feature"), "you are on feature"),
    (lambda w: (git(w, "commit", "--quiet", "--allow-empty", "-m", "local only")), "1 ahead"),
    (lambda w: git(w, "tag", "v1.0.11"), "already exists"),
])
def test_refuses_unsafe_states(repo, setup, message):
    work, origin = repo
    setup(work)
    before = (work / "pyproject.toml").read_text()
    r = run(work, answer="y")
    assert r.returncode == 1 and message in r.stdout, r.stdout
    assert (work / "pyproject.toml").read_text() == before       # nothing changed
    assert remote_tags(origin) == ""


def test_failed_commit_restores_files(repo):
    work, origin = repo
    hook = work / ".git" / "hooks" / "pre-commit"
    hook.write_text("#!/bin/sh\necho 'hook says no' >&2\nexit 1\n")
    hook.chmod(0o755)
    r = run(work, answer="y")
    assert r.returncode == 1 and "Release aborted" in r.stdout and "hook says no" in r.stdout
    assert git(work, "status", "--porcelain") == ""
    assert 'version = "1.0.10"' in (work / "pyproject.toml").read_text()
    assert git(work, "tag", "--list") == ""


def test_no_git_mode_only_rewrites_files(repo):
    work, origin = repo
    r = run(work, NO_GIT="1")
    assert r.returncode == 0 and "files only" in r.stdout
    assert 'version = "1.0.11"' in (work / "pyproject.toml").read_text()
    assert git(work, "tag", "--list") == ""
