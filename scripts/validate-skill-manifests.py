#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path


MAX_DESCRIPTION = 200


@dataclass
class Finding:
    severity: str
    skill: str
    message: str


@dataclass
class Result:
    checked_skills: int = 0
    checked_entries: int = 0
    findings: list[Finding] = field(default_factory=list)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def read_exact_text(path: Path) -> str:
    try:
        with path.open("r", encoding="utf-8", newline="") as handle:
            return handle.read()
    except OSError:
        return ""


def frontmatter_name(text: str) -> str:
    match = re.match(r"^---\n(.*?)\n---\n", text, flags=re.DOTALL)
    if not match:
        return ""
    for line in match.group(1).splitlines():
        if line.startswith("name:"):
            return line.split(":", 1)[1].strip().strip('"').strip("'")
    return ""


def frontmatter_description(text: str) -> str:
    match = re.match(r"^---\n(.*?)\n---\n", text, flags=re.DOTALL)
    lines = match.group(1).splitlines() if match else []
    for index, line in enumerate(lines):
        if not line.startswith("description:"):
            continue
        value = line.split(":", 1)[1].strip()
        if value in (">", "|"):
            folded = []
            for nested in lines[index + 1:]:
                if not nested.startswith((" ", "\t")):
                    break
                folded.append(nested.strip())
            value = " ".join(folded)
        elif value.startswith('"'):
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                pass
        return " ".join(value.strip("'").split())
    return ""


SAFE_SINGLE = re.compile(r"'(?:[^']|'')*'")
SAFE_LIST = re.compile(r"\[[A-Za-z0-9][\w ./-]*(?:, *[A-Za-z0-9][\w ./-]*)*\]")
SAFE_BLOCK = re.compile(r"[>|][+-]?")
SAFE_KEY = re.compile(r"( {2})?([A-Za-z][\w-]*):(?: (.*))?")


def safe_scalar(value: str) -> bool:
    if value.startswith('"'):
        try:
            return isinstance(json.loads(value), str)
        except json.JSONDecodeError:
            return False
    if value[0].isascii() and value[0].isalnum():
        return ": " not in value and " #" not in value and "\t" not in value and not value.endswith(":")
    return bool(SAFE_SINGLE.fullmatch(value) or SAFE_LIST.fullmatch(value))


def frontmatter_problems(text: str) -> list[str]:
    match = re.match(r"^---\n(.*?)\n---\n", text, flags=re.DOTALL)
    found: list[str] = []
    block_indent, body_indent, nested = None, None, False
    for line in match.group(1).splitlines() if match else []:
        indent = len(line) - len(line.lstrip(" "))
        if block_indent is not None and not line.strip():
            continue
        if block_indent is not None and indent > block_indent and body_indent in (None, indent):
            body_indent = indent
            continue
        if block_indent is not None and body_indent is not None and indent > body_indent:
            continue
        block_indent, body_indent = None, None
        fields = None if "\t" in line else SAFE_KEY.fullmatch(line)
        if not fields or (indent and not nested):
            found.append(f"unsupported line: {line.strip()}")
            continue
        value = (fields.group(3) or "").strip()
        if not indent:
            nested = not value
        if SAFE_BLOCK.fullmatch(value):
            block_indent = indent
        elif value and not safe_scalar(value):
            found.append(f"{fields.group(2)} needs double quotes")
    return found


def canonical_implicit_policy(text: str) -> bool | None:
    match = re.match(r"^---\n(.*?)\n---\n", text, flags=re.DOTALL)
    if not match:
        return None
    declarations = [
        line
        for line in match.group(1).splitlines()
        if "disable-model-invocation" in line
    ]
    if not declarations:
        return True
    if declarations == ["disable-model-invocation: true"]:
        return False
    return None


def canonical_json_string(line: str, prefix: str) -> str | None:
    if not line.startswith(prefix):
        return None
    encoded = line[len(prefix):]
    try:
        value = json.loads(encoded)
    except (json.JSONDecodeError, TypeError):
        return None
    if (
        not isinstance(value, str)
        or any(0xD800 <= ord(character) <= 0xDFFF for character in value)
        or json.dumps(value) != encoded
    ):
        return None
    return encoded


def canonical_openai_manifest(
    text: str, *, implicit: bool, skill: str
) -> str | None:
    if not text.endswith("\n") or "\r" in text:
        return None
    lines = text[:-1].split("\n")
    canonical: list[str] = []
    index = 0

    if lines and lines[0] == "interface:":
        canonical.append("interface:")
        index = 1
        for key in ("display_name", "short_description"):
            prefix = f"  {key}: "
            if index >= len(lines):
                return None
            encoded = canonical_json_string(lines[index], prefix)
            if encoded is None:
                return None
            value_text = json.loads(encoded)
            if key == "display_name" and not value_text.strip():
                return None
            if key == "short_description" and not 25 <= len(value_text) <= 64:
                return None
            canonical.append(prefix + encoded)
            index += 1
        if index < len(lines) and lines[index].startswith("  default_prompt:"):
            prefix = "  default_prompt: "
            encoded = canonical_json_string(lines[index], prefix)
            if encoded is None:
                return None
            if re.search(
                rf"\${re.escape(skill)}(?![A-Za-z0-9_-])",
                json.loads(encoded),
            ) is None:
                return None
            canonical.append(prefix + encoded)
            index += 1

    value = "true" if implicit else "false"
    canonical.extend(("policy:", f"  allow_implicit_invocation: {value}"))
    expected = "\n".join(canonical) + "\n"
    return expected if text == expected else None


def add(result: Result, severity: str, skill: str, message: str) -> None:
    result.findings.append(Finding(severity, skill, message))


def check_skill(skill_dir: Path, result: Result) -> None:
    skill = skill_dir.name
    root_skill_md = skill_dir / "SKILL.md"

    if not root_skill_md.is_file():
        return

    result.checked_skills += 1

    root_text = read_text(root_skill_md)
    if frontmatter_name(root_text) != skill:
        add(result, "ERROR", skill, "SKILL.md frontmatter name must equal skill folder")
    result.checked_entries += 1
    description = frontmatter_description(root_text)
    if not description:
        add(result, "ERROR", skill, "SKILL.md needs a description")
    elif len(description) > MAX_DESCRIPTION:
        add(result, "ERROR", skill,
            f"SKILL.md description is {len(description)} chars; keep it at most {MAX_DESCRIPTION}")

    for problem in frontmatter_problems(root_text):
        add(result, "ERROR", skill, f"SKILL.md frontmatter must stay a plain form, because bad YAML drops every field: {problem}")

    implicit_policy = canonical_implicit_policy(root_text)
    if implicit_policy is None:
        add(result, "ERROR", skill, "SKILL.md invocation policy must be canonical")

    openai_manifest = skill_dir / "agents" / "openai.yaml"
    if not openai_manifest.is_file():
        add(result, "ERROR", skill, "agents/openai.yaml is required")
    elif implicit_policy is not None:
        manifest_text = read_exact_text(openai_manifest)
        if canonical_openai_manifest(manifest_text, implicit=implicit_policy, skill=skill) is None:
            add(result, "ERROR", skill,
                "agents/openai.yaml must match the canonical schema and invocation policy")

    entry = skill_dir / "codex" / "SKILL.md"
    if entry.is_file():
        result.checked_entries += 1
        entry_text = read_text(entry)
        for problem in frontmatter_problems(entry_text):
            add(result, "ERROR", skill, f"codex/SKILL.md frontmatter must stay a plain form: {problem}")
        entry_name = frontmatter_name(entry_text)
        if entry_name and entry_name != skill:
            add(result, "ERROR", skill, f"codex/SKILL.md frontmatter name must equal {skill}")
        if implicit_policy is not None and canonical_implicit_policy(entry_text) != implicit_policy:
            add(result, "ERROR", skill, "codex/SKILL.md invocation policy must match root SKILL.md")


def validate(root: Path) -> Result:
    result = Result()
    seen: dict[str, str] = {}
    for category_dir in sorted((root / "skills").iterdir()):
        if not category_dir.is_dir():
            continue
        for skill_dir in sorted(category_dir.iterdir()):
            if not skill_dir.is_dir():
                continue
            if (skill_dir / "SKILL.md").is_file() and skill_dir.name in seen:
                add(result, "ERROR", skill_dir.name,
                    f"duplicate skill name in {category_dir.name}/ and {seen[skill_dir.name]}/")
            elif (skill_dir / "SKILL.md").is_file():
                seen[skill_dir.name] = category_dir.name
            check_skill(skill_dir, result)
    return result


def print_text(result: Result) -> None:
    print("Skill Source Validation")
    print(f"Checked {result.checked_skills} skills and {result.checked_entries} entrypoint(s).")
    if not result.findings:
        print("OK: no skill source issues found.")
        return
    for finding in result.findings:
        print(f"{finding.severity}: {finding.skill}: {finding.message}")


def main() -> int:
    argparse.ArgumentParser(description="Validate dot-agent skill sources.").parse_args()
    result = validate(repo_root())
    print_text(result)
    if any(finding.severity == "ERROR" for finding in result.findings):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
