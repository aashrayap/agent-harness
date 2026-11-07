#!/usr/bin/env python3
from collections import defaultdict
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SKIP = ("docs/research/", "docs/artifacts/", ".claude/skills/")
LEGAL = ("LICENSE-MIT.md", "UPSTREAM.md")
MIN_WORDS = 8


def sentences(text):
    text = re.sub(r"\A---\n.*?\n---\n", "", text, flags=re.S)
    text = re.sub(r"```.*?```|<!--.*?-->", "", text, flags=re.S)
    for part in re.split(r"(?<=[.!?:;])\s+|\|", " ".join(text.split())):
        words = re.sub(r"[^a-z0-9 ]", "", part.lower()).split()
        if len(words) >= MIN_WORDS:
            yield " ".join(words)


def tracked(root):
    listed = subprocess.run(["git", "-C", str(root), "ls-files", "*.md"],
                            capture_output=True, text=True, check=True).stdout.splitlines()
    return [path for path in listed
            if not path.startswith(SKIP) and not path.endswith(LEGAL)]


def duplicates(root=ROOT, paths=None):
    homes = defaultdict(set)
    for path in paths if paths is not None else tracked(root):
        for sentence in sentences((root / path).read_text(encoding="utf-8")):
            homes[sentence].add(path)
    return sorted((sorted(files), sentence) for sentence, files in homes.items()
                  if len(files) > 1)


def main():
    found = duplicates()
    for files, sentence in found:
        print(f"ERROR: {', '.join(files)}: {sentence!r}")
    print("one-home-check: " + ("FAIL: keep one owner and link from the others" if found else "PASS"))
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
