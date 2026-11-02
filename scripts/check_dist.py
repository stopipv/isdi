#!/usr/bin/env python3
"""Check that built wheels and sdists contain only expected files.

Usage: python scripts/check_dist.py [dist-dir]   (default: dist)

Every non-Python file inside the `isdi` package must be listed in
[tool.setuptools.package-data] in pyproject.toml, and nothing may look like a
secret, a database or a screenshot. Exits non-zero and lists the offending
files otherwise. Requires Python 3.11+ (tomllib).
"""

import fnmatch
import sys
import tarfile
import tomllib
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

FORBIDDEN = ["*.key", "*.secret", "*.db", "*.sqlite", "*tmp*.png", "*.env"]

# Files allowed at the top of the sdist (besides src/ and PKG-INFO).
SDIST_TOP_LEVEL = {
    "LICENSE",
    "MANIFEST.in",
    "PKG-INFO",
    "README.md",
    "CHANGELOG.md",
    "pyproject.toml",
    "requirements.txt",
    "setup.cfg",
    "setup.py",
}


def allowed_package_data() -> set:
    with open(ROOT / "pyproject.toml", "rb") as f:
        pyproject = tomllib.load(f)
    return set(pyproject["tool"]["setuptools"]["package-data"]["isdi"])


def check_package_file(rel: str, allowed: set) -> str:
    """rel is a path inside the isdi package. Return an error or ""."""
    name = rel.rsplit("/", 1)[-1]
    if any(fnmatch.fnmatch(name, pat) for pat in FORBIDDEN):
        return "forbidden file type"
    if rel.endswith(".py") or rel.endswith("/"):
        return ""
    if rel not in allowed:
        return "not listed in pyproject.toml package-data"
    return ""


def check_wheel(path: Path, allowed: set) -> list:
    errors = []
    with zipfile.ZipFile(path) as zf:
        for name in zf.namelist():
            if name.split("/", 1)[0].endswith(".dist-info"):
                continue
            if not name.startswith("isdi/"):
                errors.append((name, "outside the isdi package"))
                continue
            err = check_package_file(name[len("isdi/"):], allowed)
            if err:
                errors.append((name, err))
    return errors


def check_sdist(path: Path, allowed: set) -> list:
    errors = []
    with tarfile.open(path) as tf:
        for member in tf.getmembers():
            if member.isdir():
                continue
            parts = member.name.split("/", 1)
            rel = parts[1] if len(parts) > 1 else ""
            if rel.startswith("src/isdi/"):
                err = check_package_file(rel[len("src/isdi/"):], allowed)
            elif rel.startswith("src/isdi_scanner.egg-info/"):
                err = ""
            elif rel.startswith("tests/") and rel.endswith(".py"):
                err = ""
            elif rel in SDIST_TOP_LEVEL:
                err = ""
            else:
                err = "unexpected file in sdist"
            if err:
                errors.append((member.name, err))
    return errors


def main() -> int:
    dist = Path(sys.argv[1] if len(sys.argv) > 1 else "dist")
    allowed = allowed_package_data()
    missing = [p for p in sorted(allowed) if not (ROOT / "src" / "isdi" / p).exists()]

    builds = sorted(dist.glob("*.whl")) + sorted(dist.glob("*.tar.gz"))
    if not builds:
        print(f"No wheel or sdist found in {dist}", file=sys.stderr)
        return 1

    failed = False
    for p in missing:
        print(f"src/isdi/{p}: listed in package-data but missing from the source tree")
        failed = True
    for build in builds:
        check = check_wheel if build.suffix == ".whl" else check_sdist
        errors = check(build, allowed)
        for name, err in errors:
            print(f"{build.name}: {name}: {err}")
        failed = failed or bool(errors)
        if not errors:
            print(f"{build.name}: OK")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
