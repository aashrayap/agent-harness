#!/usr/bin/env python3
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SKIP = ("docs/research/", "docs/artifacts/")

TERMS = {
    "Daily Driver": re.compile(r"\bDaily ?Driver\b|\bdaily[-_]driver\b", re.I),
    "Atlas": re.compile(r"\batlas\b", re.I),
    "T3": re.compile(r"\bT3\b"),
    "River": re.compile(r"\bRiver\b"),
    "Watch": re.compile(r"(?<!Apple )\bWatch\b"),
    "Chief": re.compile(r"\bChiefs?\b"),
    "Router": re.compile(r"\bRouter\b|\$router\b|skills/engineering/router\b"),
}

ALLOW = {
    ("docs/harness-runtime-reference.md", "Router"),
    ("scripts/forbidden-words.py", "*"),
    ("scripts/tests/test_lint_checks.py", "*"),
    ("scripts/fixtures/retired-runtime.json", "*"),
    ("scripts/tests/test_managed_runtime_retirement.py", "Daily Driver"),
    ("scripts/tests/test_managed_runtime_retirement.py", "Atlas"),
}


def allowed(path, term):
    return (path, "*") in ALLOW or (path, term) in ALLOW


def tracked(root):
    listed = subprocess.run(["git", "-C", str(root), "ls-files"],
                            capture_output=True, text=True, check=True).stdout.splitlines()
    return [path for path in listed if not path.startswith(SKIP)]


def findings(root=ROOT, paths=None):
    found = []
    for path in paths if paths is not None else tracked(root):
        try:
            text = (root / path).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for term, pattern in TERMS.items():
            if allowed(path, term):
                continue
            for match in pattern.finditer(text):
                line = text.count("\n", 0, match.start()) + 1
                found.append(f"{path}:{line}: retired or forbidden: {term}")
    return found


def main():
    found = findings()
    for finding in found:
        print(f"ERROR: {finding}")
    print("forbidden-words: " + ("FAIL" if found else "PASS"))
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
