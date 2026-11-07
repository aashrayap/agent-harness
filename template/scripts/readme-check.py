#!/usr/bin/env python3
import argparse
import importlib.util
import json
import re
import sys
from pathlib import Path

MAX_LINES = 80
STATUS_ROWS = ("version", "works", "next")
HISTORY = re.compile(r"^#+\s*(history|changelog|releases?|what changed|timeline)\b", re.I | re.M)
DATE = re.compile(r"\b20\d\d-\d\d-\d\d\b")


def diagram_lint():
    spec = importlib.util.spec_from_file_location("diagram_lint", Path(__file__).absolute().parent / "diagram-lint.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def section(text, name):
    match = re.search(rf"^##\s+{name}\s*$(.*?)(?=^##\s|\Z)", text, re.M | re.S | re.I)
    return match.group(1) if match else None


def problems(root):
    readme, version = root / "README.md", root / "VERSION"
    if not readme.is_file():
        return ["no README.md"]
    text = readme.read_text(encoding="utf-8")
    found = []
    lines = text.splitlines()
    if not lines or not lines[0].startswith("# "):
        found.append("first line is not a '# Title'")
    paragraph = text.split("\n\n")[1].strip() if text.count("\n\n") else ""
    if not paragraph or "\n" in paragraph or paragraph.startswith(("#", "|", "`", "-")):
        found.append("the line after the title is not a one-line purpose")
    status = section(text, "Status")
    if status is None:
        found.append("no '## Status' table")
    else:
        rows = {cells[0].strip().lower(): cells[1].strip() for cells in
                (line.strip().strip("|").split("|") for line in status.splitlines() if line.strip().startswith("|"))
                if len(cells) >= 2}
        for name in STATUS_ROWS:
            if not rows.get(name):
                found.append(f"Status table has no {name.capitalize()} row")
        if version.is_file() and rows.get("version") and \
                rows["version"].strip("` ") != version.read_text().strip():
            found.append(f"Status Version {rows['version']} is not VERSION {version.read_text().strip()}")
    lint = diagram_lint()
    fences = lint.FENCE.findall(text)
    if not 1 <= len(fences) <= 2:
        found.append(f"{len(fences)} Mermaid diagrams (want 1 or 2)")
    for source in fences:
        found += [f"diagram: {problem}" for problem in lint.problems(source)[0]]
    if "AGENTS.md" not in text:
        found.append("no pointer to AGENTS.md, where the where-do-I-look table lives")
    if HISTORY.search(text) or DATE.search(text):
        found.append("history belongs in RELEASES.md: drop dated lines and history headings")
    if len(lines) > MAX_LINES:
        found.append(f"{len(lines)} lines (max {MAX_LINES})")
    return found


def main(argv=None):
    parser = argparse.ArgumentParser(description="Fail a README that is not the repo's short current truth.")
    parser.add_argument("repo", nargs="?", default=".")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    found = problems(Path(args.repo))
    if args.json:
        print(json.dumps({"ok": not found, "repo": str(Path(args.repo).resolve()), "problems": found}, indent=2))
    else:
        for problem in found:
            print(f"ERROR: README.md: {problem}")
        print("readme-check: " + ("FAIL" if found else "PASS"))
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
