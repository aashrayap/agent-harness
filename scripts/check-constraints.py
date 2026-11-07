#!/usr/bin/env python3
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
FILE = "CONSTRAINTS.tsv"
COLUMNS = ["id", "rule", "level", "enforcer", "proof", "notes"]
LEVELS = ("impossible", "check", "test", "hook", "prose", "memory")
NEEDS_PROOF = ("impossible", "check", "test", "hook")
REQUIRED = 4
ID = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
TEST_NAME = re.compile(r"\btest_\w+")


def normalize(text):
    return " ".join(text.split())


def defines(text, name, python):
    if python:
        pattern = rf"^\s*(?:def|class)\s+{re.escape(name)}\b|^{re.escape(name)}\s*="
        return re.search(pattern, text, re.M) is not None
    return re.search(rf"(?<![\w-]){re.escape(name)}(?![\w-])", text) is not None


def test_names(root):
    names = set()
    for path in root.rglob("test_*.py"):
        if ".git" not in path.parts:
            names.update(re.findall(r"^\s*def (test_\w+)", path.read_text(encoding="utf-8"), re.M))
    return names


def rows(root=ROOT):
    lines = (root / FILE).read_text(encoding="utf-8").splitlines()
    return lines[0].split("\t") if lines else [], list(enumerate(lines[1:], 2))


def problems(root=ROOT):
    header, body = rows(root)
    if header != COLUMNS:
        return [f"{FILE}:1: header must be {' | '.join(COLUMNS)}"]
    found, seen, known = [], {}, test_names(root)
    for number, line in body:
        where = f"{FILE}:{number}"
        fields = line.split("\t")
        if not REQUIRED <= len(fields) <= len(COLUMNS):
            found.append(f"{where}: needs {REQUIRED} to {len(COLUMNS)} tab-separated fields"
                         f" (proof and notes may be left off), has {len(fields)}")
            continue
        fields += [""] * (len(COLUMNS) - len(fields))
        row = dict(zip(COLUMNS, (field.strip() for field in fields)))
        if not ID.fullmatch(row["id"]):
            found.append(f"{where}: id {row['id']!r} must be lowercase-kebab")
        elif row["id"] in seen:
            found.append(f"{where}: duplicate id {row['id']!r} (first on line {seen[row['id']]})")
        else:
            seen[row["id"]] = number
        if not row["rule"]:
            found.append(f"{where}: rule is empty")
        if row["level"] not in LEVELS:
            found.append(f"{where}: level {row['level']!r} must be one of {', '.join(LEVELS)}")
            continue
        if row["level"] in NEEDS_PROOF and not row["proof"]:
            found.append(f"{where}: a {row['level']} row needs proof: the past mistake or test "
                         "that shows the enforcer fails without the fix")
        for name in TEST_NAME.findall(row["proof"]):
            if name not in known:
                found.append(f"{where}: proof names {name}, which no test file defines")
        if row["level"] == "memory":
            if not row["enforcer"]:
                found.append(f"{where}: memory row names no memory file")
            continue
        relative, _, name = row["enforcer"].partition("::")
        path = root / relative
        if not relative or Path(relative).is_absolute() or ".." in Path(relative).parts \
                or not path.is_file():
            found.append(f"{where}: enforcer {relative!r} is not a file in the repo")
            continue
        text = path.read_text(encoding="utf-8")
        if name and not defines(text, name, path.suffix == ".py"):
            found.append(f"{where}: {relative} has no {name!r}")
        if row["level"] == "prose" and normalize(row["rule"]) not in normalize(text):
            found.append(f"{where}: {relative} no longer says: {row['rule']}")
    return found


def main():
    found = problems()
    for problem in found:
        print(f"ERROR: {problem}")
    print("check-constraints: " + ("FAIL" if found else "PASS"))
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
