#!/usr/bin/env python3
from pathlib import Path
import argparse
import re

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "skills/engineering/owner-mode/SKILL.md"
START = "<!-- skill-list:start -->"
END = "<!-- skill-list:end -->"


def field(block, name):
    lines = block.splitlines()
    for index, line in enumerate(lines):
        if not line.startswith(f"{name}:"):
            continue
        value = line[len(name) + 1:].strip()
        if value not in (">", "|"):
            return value.strip("\"'")
        folded = []
        for nested in lines[index + 1:]:
            if not nested.startswith((" ", "\t")):
                break
            folded.append(nested.strip())
        return " ".join(folded)
    return ""


def active_skills():
    skills = {}
    for path in sorted((ROOT / "skills").glob("*/*/SKILL.md")):
        match = re.match(r"^---\n(.*?)\n---\n", path.read_text(), re.DOTALL)
        if not match:
            raise SystemExit(f"missing frontmatter: {path.relative_to(ROOT)}")
        name = field(match.group(1), "name")
        if not name or name in skills:
            raise SystemExit(f"invalid or duplicate skill name: {path.relative_to(ROOT)}")
        skills[name] = match.group(1)
    return skills


def render(text):
    lines = ["| Skill | Mode | Capability |", "| --- | --- | --- |"]
    for name, block in sorted(active_skills().items()):
        description = " ".join(field(block, "description").split()).replace("|", "&#124;")
        mode = "explicit" if "disable-model-invocation: true" in block.splitlines() else "model"
        lines.append(f"| `{name}` | {mode} | {description} |")
    head, rest = text.split(START, 1)
    _, tail = rest.split(END, 1)
    return f"{head}{START}\n" + "\n".join(lines) + f"\n{END}{tail}"


def main():
    parser = argparse.ArgumentParser(description="Generate the skill list in owner-mode from skill frontmatter.")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    current = TARGET.read_text(encoding="utf-8")
    expected = render(current)
    if args.check:
        if current != expected:
            print("Skill list differs from source; run scripts/skill-catalog.py.")
            return 1
        print("Skill list matches source.")
        return 0
    TARGET.write_text(expected, encoding="utf-8")
    print("Updated the owner-mode skill list from source.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
