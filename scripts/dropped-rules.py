#!/usr/bin/env python3
from difflib import SequenceMatcher
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
INSTRUCTIONS = re.compile(r"^(AGENTS\.md|skills/(?!.*/upstream/).+/SKILL\.md)$")
KEPT = 0.6
MIN_WORDS = 5


def git(*args):
    return subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True, check=True).stdout


def sentences(text, words=MIN_WORDS):
    text = re.sub(r"^#+\s+(.*)$", r"\1.", text, flags=re.M)
    text = re.sub(r"^\s*(?:[-*]|\d+\.)\s+", "", text, flags=re.M)
    flat = " ".join(text.split())
    return [s for s in re.split(r"(?<=[.;!?:])\s+", flat) if len(s.split()) >= words]


def close(sentence, other):
    matcher = SequenceMatcher(None, sentence, other, autojunk=False)
    return matcher.real_quick_ratio() >= KEPT and matcher.quick_ratio() >= KEPT and matcher.ratio() >= KEPT


def dropped(before, corpus):
    pieces = sentences(corpus, 1)
    after = [" ".join(pieces[i:i + size]) for size in (1, 2, 3, 4) for i in range(len(pieces))]
    flat = " ".join(corpus.split())
    found = []
    for sentence in sentences(before):
        if sentence in flat:
            continue
        if any(close(sentence, other) for other in after):
            continue
        found.append(sentence)
    return found


def main():
    base = sys.argv[1] if len(sys.argv) > 1 else "origin/main"
    try:
        merge_base = git("merge-base", base, "HEAD").strip()
        changed = [line.split("\t")[1] for line in
                   git("diff", "--name-status", "-M", "--diff-filter=MDR", merge_base, "HEAD").splitlines()
                   if INSTRUCTIONS.match(line.split("\t")[1])]
    except subprocess.CalledProcessError as error:
        print(f"dropped-rules: cannot diff against {base}: {error.stderr.strip()}")
        return 1
    corpus = "\n".join((ROOT / path).read_text(encoding="utf-8", errors="replace")
                       for path in git("ls-files", "*.md").splitlines() if (ROOT / path).is_file())
    found = []
    for path in changed:
        for sentence in dropped(git("show", f"{merge_base}:{path}"), corpus):
            found.append(f"{path}: dropped with no new home: {sentence}")
    for line in found:
        print(f"ERROR: {line}")
    if found:
        print("Move each rule to another tracked file, or quote it under 'Dropped:' in the RELEASES.md entry.")
    print("dropped-rules: " + ("FAIL" if found else "PASS"))
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
