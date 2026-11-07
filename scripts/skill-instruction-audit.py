#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path


DANGLING_SOURCE_REF = "skills/AGENTS.md"
SHARED_DIRS = ("scripts", "assets", "references", "shared", "agents", "playbooks", "principles")


@dataclass
class Finding:
    severity: str
    skill: str
    runtime: str
    message: str


@dataclass
class AuditResult:
    checked_skills: int = 0
    checked_payloads: int = 0
    findings: list[Finding] = field(default_factory=list)


def dot_agent_home() -> Path:
    return Path(os.environ.get("DOT_AGENT_HOME", Path(__file__).resolve().parents[1])).expanduser()


def runtime_home(name: str) -> Path:
    env_name = f"{name.upper()}_HOME"
    default = Path.home() / f".{name}"
    return Path(os.environ.get(env_name, default)).expanduser()


def provided_skills(dot_agent: Path) -> set[str]:
    state = Path(os.environ.get("DOT_AGENT_STATE_HOME", dot_agent / "state")).expanduser()
    marker = state / "machine-profile"
    if not marker.is_file():
        return set()
    path = dot_agent / "profiles" / marker.read_text().strip() / "provided-skills"
    if not path.is_file():
        return set()
    return {line.strip() for line in path.read_text().splitlines() if line.strip()}


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def runtime_entry(runtime: str, skill_dir: Path) -> str:
    if (skill_dir / runtime / "SKILL.md").is_file():
        return f"{runtime}/SKILL.md"
    return "SKILL.md"


def audit_skill_runtime(result: AuditResult, skill_dir: Path, runtime: str) -> None:
    skill_name = skill_dir.name
    entry = runtime_entry(runtime, skill_dir)
    source_entry = skill_dir / entry
    payload_root = runtime_home(runtime) / "skills" / skill_name
    installed_entry = payload_root / "SKILL.md"
    result.checked_payloads += 1

    def warn(message: str) -> None:
        result.findings.append(Finding("WARN", skill_name, runtime, message))

    if not source_entry.is_file():
        warn(f"missing source entry {entry}")
        return

    source_text = read_text(source_entry)
    installed_text = read_text(installed_entry)

    if DANGLING_SOURCE_REF in source_text:
        warn(f"source entry references {DANGLING_SOURCE_REF}")

    if not installed_entry.is_file():
        warn("runtime payload missing SKILL.md")
        return

    if DANGLING_SOURCE_REF in installed_text:
        warn(f"installed payload references {DANGLING_SOURCE_REF}")

    if installed_text != source_text:
        warn("installed SKILL.md differs from selected source entry; rerun setup")

    for shared_dir in SHARED_DIRS:
        source_shared = skill_dir / shared_dir
        installed_shared = payload_root / shared_dir
        if not source_shared.exists():
            continue
        if not installed_shared.exists():
            warn(f"runtime payload missing {shared_dir}/")
            continue
        for source_file in source_shared.rglob("*"):
            if not source_file.is_file() or "__pycache__" in source_file.parts or source_file.suffix in (".pyc", ".pyo"):
                continue
            relative = source_file.relative_to(source_shared)
            installed_file = installed_shared / relative
            if not installed_file.is_file():
                warn(f"runtime payload missing {shared_dir}/{relative}")
            elif installed_file.read_bytes() != source_file.read_bytes():
                warn(f"installed {shared_dir}/{relative} differs from source")


def audit(dot_agent: Path, runtime: str = "codex") -> AuditResult:
    skills_root = dot_agent / "skills"
    result = AuditResult()
    provided = provided_skills(dot_agent)

    skill_dirs = sorted(
        skill_dir
        for category_dir in skills_root.iterdir()
        if category_dir.is_dir()
        for skill_dir in category_dir.iterdir()
        if skill_dir.is_dir()
    )
    for skill_dir in skill_dirs:
        skill_name = skill_dir.name
        if not (skill_dir / "SKILL.md").is_file():
            continue

        result.checked_skills += 1

        if skill_name in provided:
            continue

        audit_skill_runtime(result, skill_dir, runtime)

    if (runtime_home(runtime) / "skills" / "AGENTS.md").exists():
        result.findings.append(Finding(
            "WARN", "skills", runtime,
            "runtime skills directory contains AGENTS.md; directory policy should stay source-only"))

    return result


def print_text(result: AuditResult) -> None:
    print("Skill Instruction Audit")
    print(f"Checked {result.checked_skills} skills, {result.checked_payloads} runtime payloads.")
    if not result.findings:
        print("OK: no skill instruction drift found.")
        return
    print(f"WARN: {len(result.findings)} issue(s) found.")
    for finding in result.findings:
        print(f"{finding.severity}: {finding.skill} [{finding.runtime}] {finding.message}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit installed skill payloads for instruction drift.")
    parser.add_argument("--strict", action="store_true", help="Exit non-zero when WARN findings exist.")
    parser.add_argument("--runtime", choices=("codex", "claude"), default="codex",
                        help="Runtime whose installed payloads to audit.")
    args = parser.parse_args()

    result = audit(dot_agent_home(), args.runtime)
    print_text(result)

    if args.strict and result.findings:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
