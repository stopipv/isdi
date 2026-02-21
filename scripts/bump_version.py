#!/usr/bin/env python3
import os
import re
import sys
from pathlib import Path

PARTS = {"patch", "minor", "major"}


def bump(ver: str, part: str) -> str:
    major, minor, patch = [int(v) for v in ver.split(".")]
    if part == "major":
        return f"{major + 1}.0.0"
    if part == "minor":
        return f"{major}.{minor + 1}.0"
    return f"{major}.{minor}.{patch + 1}"


def main() -> int:
    part = os.environ.get("VERSION_PART", "patch").lower()
    if part not in PARTS:
        print(f"Unsupported VERSION_PART: {part}. Use patch, minor, or major.")
        return 1

    targets = [
        (Path("pyproject.toml"), r'(?m)^(version\s*=\s*\")(?P<ver>\d+\.\d+\.\d+)(\")'),
        (Path("src/isdi/__init__.py"), r'(?m)^(__version__\s*=\s*\")(?P<ver>\d+\.\d+\.\d+)(\")'),
    ]

    new_version = None
    for path, pattern in targets:
        text = path.read_text(encoding="utf-8")
        match = re.search(pattern, text)
        if not match:
            print(f"Version not found in {path}")
            return 1
        current = match.group("ver")
        if new_version is None:
            new_version = bump(current, part)
        updated = re.sub(
            pattern,
            lambda m: f"{m.group(1)}{new_version}{m.group(3)}",
            text,
            count=1,
        )
        path.write_text(updated, encoding="utf-8")

    print(f"Bumped version to {new_version}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
