#!/usr/bin/env python3
from __future__ import annotations

import argparse
import difflib
import hashlib
import re
import sys
from pathlib import Path

SKILL = Path("skills/engineering/owner-mode")
START = "<!-- upstream-files:start -->"
END = "<!-- upstream-files:end -->"
ROW = re.compile(r"^\| `([^`]+)` \| `([^`]+)` \| `([^`]+)` \| `([0-9a-f]{40})` \| `([0-9a-f]{64})` \|$")
PSTACK = "cursor/plugins"
TRACKED = re.compile(
    r"^(LICENSE|skills/poteto-mode/SKILL\.md|skills/poteto-mode/(playbooks|references)/[^/]+\.md"
    r"|skills/principle-[^/]+/SKILL\.md)$")
USAGE = """Check owner-mode's upstream manifest, or compare it with a pstack checkout.

--check        every playbook and principle has a row, every row's file exists, no nested SKILL.md
--compare DIR  DIR is laid out like pstack/; list each recorded file as unchanged, changed or new
"""


def rows(root: Path) -> list[tuple[str, str, str, str, str]]:
    text = (root / SKILL / "UPSTREAM.md").read_text(encoding="utf-8")
    if START not in text or END not in text:
        sys.exit("owner-mode-upstream: UPSTREAM.md has no file table")
    block = text.split(START, 1)[1].split(END, 1)[0]
    return [m.groups() for line in block.splitlines() if (m := ROW.match(line))]


def check(root: Path) -> int:
    skill = root / SKILL
    table = rows(root)
    errors = [] if table else ["no rows in the file table"]
    recorded = {local for local, *_ in table}
    for local in sorted(recorded):
        if not (skill / local).is_file():
            errors.append(f"missing: {local}")
    for folder in ("playbooks", "principles"):
        for path in sorted((skill / folder).glob("*.md")):
            if f"{folder}/{path.name}" not in recorded:
                errors.append(f"unrecorded: {folder}/{path.name}")
    for nested in sorted(skill.rglob("SKILL.md")):
        if nested != skill / "SKILL.md":
            errors.append(f"nested skill: {nested.relative_to(skill)}")
    for error in errors:
        print(f"owner-mode-upstream: {error}")
    if errors:
        return 1
    print(f"owner-mode-upstream: {len(table)} rows cover {len(recorded)} files")
    return 0


def compare(root: Path, other: Path) -> int:
    skill = root / SKILL
    seen = set()
    for local, repo, remote, _, digest in rows(root):
        if repo != PSTACK:
            continue
        rel = remote.removeprefix("pstack/")
        seen.add(rel)
        there = other / rel
        if not there.is_file():
            print(f"gone there: {rel} (ours: {local})")
            continue
        data = there.read_bytes()
        if hashlib.sha256(data).hexdigest() == digest:
            print(f"unchanged: {rel}")
            continue
        print(f"changed: {rel} (ours: {local})")
        ours = (skill / local).read_text(encoding="utf-8").splitlines()
        theirs = data.decode("utf-8", errors="replace").splitlines()
        sys.stdout.writelines(
            line + "\n" for line in difflib.unified_diff(ours, theirs, f"ours/{local}", f"there/{rel}", lineterm=""))
    for path in sorted(other.rglob("*")):
        rel = path.relative_to(other).as_posix()
        if path.is_file() and TRACKED.match(rel) and rel not in seen:
            print(f"new there: {rel}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=USAGE, formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--compare", type=Path)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    if args.check:
        return check(args.root)
    return compare(args.root, args.compare.resolve())


if __name__ == "__main__":
    raise SystemExit(main())
