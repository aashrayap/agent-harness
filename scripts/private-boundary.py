#!/usr/bin/env python3
from pathlib import Path
import os
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
PRIVATE_NAME = re.compile(r"(^|/)(\.env(\..*)?|.*\.private\..*|.*\.(pem|p12|key))$")
BINARY = re.compile(r"\.(pdf|jpe?g|png|heic|tiff?|gif|webp|docx)$", re.IGNORECASE)
HOME_PATH = re.compile(r"/Users/(?!x/)[A-Za-z0-9._-]+/")
A_NUMBER = re.compile(r"(?<![\w-])A[-–# ]?(?:\d{8,9}|\d{3}([-– ])\d{3}\1\d{3}|\d{2}([-– ])\d{3}\2\d{3})(?![\w-])(?!\.\d)(?! \d)")
SSN = re.compile(r"(?<![\w.-])(?<!\d )(?!000|666|9\d\d)\d{3}([- ])(?!00)\d{2}\1(?!0000)\d{4}(?![\w-])(?!\.\d)(?! \d)")
ALLOW = "scripts/private-boundary.allow"
FIXTURES = ("tests/",)


def tracked(root):
    listed = subprocess.run(["git", "-C", str(root), "ls-files", "-z"], capture_output=True,
                            text=True, check=True).stdout
    return [path for path in listed.split("\0") if path]


def marker_file(root):
    common = subprocess.run(["git", "rev-parse", "--git-common-dir"], cwd=root,
                            capture_output=True, text=True, check=True).stdout.strip()
    return Path(root) / common / "info" / "private-markers"


def markers(root):
    path = marker_file(root)
    if not path.is_file():
        return []
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()]


def allowed(root):
    path, paths, found = Path(root) / ALLOW, set(), []
    if not path.is_file():
        return paths, found
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip() or line.startswith("#"):
            continue
        relative, _, reason = line.partition("\t")
        if not reason.strip():
            found.append(f"{ALLOW}:{number}: give a reason after a tab")
        paths.add(relative.strip())
    return paths, found


def in_ci():
    return os.environ.get("CI", "").lower() == "true"


def problems(root=ROOT, paths=None):
    root = Path(root)
    words, (allow, found) = markers(root), allowed(root)
    for relative in paths if paths is not None else tracked(root):
        if PRIVATE_NAME.search(relative):
            found.append(f"{relative}: private file name is tracked")
            continue
        if BINARY.search(relative):
            if relative not in allow:
                found.append(f"{relative}: tracked document or image is not inspected; "
                             f"remove it or list it in {ALLOW} with a reason")
            continue
        try:
            text = (root / relative).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for number, line in enumerate(text.splitlines(), 1):
            if not relative.startswith(FIXTURES) and HOME_PATH.search(line):
                found.append(f"{relative}:{number}: absolute home path; use ~ or an env var")
            if A_NUMBER.search(line):
                found.append(f"{relative}:{number}: looks like an A-number")
            if SSN.search(line):
                found.append(f"{relative}:{number}: looks like an SSN")
            found.extend(f"{relative}:{number}: private marker" for word in words if word in line)
    return found


def main():
    found = problems()
    for problem in found:
        print(f"ERROR: {problem}")
    if not markers(ROOT):
        print("private-boundary: names scan skipped in CI: no private list" if in_ci() else
              f"WARNING: no private names list: create {marker_file(ROOT).resolve()} with one "
              "private name per line (never committed) so the names scan can run")
    print("private-boundary: " + ("FAIL" if found else "PASS"))
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
