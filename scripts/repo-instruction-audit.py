#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import sqlite3
import subprocess
import sys
import time

sys.dont_write_bytecode = True

try:
    import tomllib
except ModuleNotFoundError:
    try:
        import tomli as tomllib
    except ModuleNotFoundError:
        import toml_compat as tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable


RUNTIME_PREFERENCE_ANCHORS = (
    "claude code and codex are both primary runtimes",
)
LEGACY_RUNTIME_ANCHORS = (
    "native Claude desktop app and native Codex as peers",
    "native Claude desktop app and native Codex are peer runtimes",
    "Claude Code and Codex are peer runtimes",
)


@dataclass
class RepoSource:
    path: Path
    reason: str


@dataclass
class RepoFinding:
    severity: str
    repo: str
    message: str


@dataclass
class RepoStatus:
    repo: str
    sources: list[str]
    agents: str
    claude: str
    findings: list[RepoFinding] = field(default_factory=list)


@dataclass
class AuditResult:
    discovered_paths: int = 0
    checked_repos: list[RepoStatus] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)

    @property
    def findings(self) -> list[RepoFinding]:
        return [finding for repo in self.checked_repos for finding in repo.findings]

    @property
    def warnings(self) -> list[RepoFinding]:
        return [finding for finding in self.findings if finding.severity == "WARN"]


def dot_agent_home() -> Path:
    return Path(os.environ.get("DOT_AGENT_HOME", Path(__file__).resolve().parents[1])).expanduser()


def codex_home() -> Path:
    return Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")).expanduser()


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def load_toml(path: Path) -> dict[str, Any]:
    try:
        with path.open("rb") as handle:
            return tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError):
        return {}


def pathish(value: str) -> bool:
    return value.startswith("/") or value.startswith("~/")


def iter_path_strings(node: Any) -> Iterable[str]:
    if isinstance(node, str):
        if pathish(node):
            yield node
        return
    if isinstance(node, list):
        for item in node:
            yield from iter_path_strings(item)
        return
    if isinstance(node, dict):
        for key, value in node.items():
            if isinstance(key, str) and pathish(key):
                yield key
            yield from iter_path_strings(value)


def codex_project_paths(config_path: Path) -> list[RepoSource]:
    data = load_toml(config_path)
    projects = data.get("projects")
    sources: list[RepoSource] = []
    if isinstance(projects, dict):
        for key in projects:
            if isinstance(key, str) and pathish(key):
                sources.append(RepoSource(Path(key).expanduser(), f"codex config {config_path}"))
    return sources


def allowlist_paths(path: Path) -> list[RepoSource]:
    if not path.is_file():
        return []
    data = load_toml(path)
    return [RepoSource(Path(raw).expanduser(), f"allowlist {path}") for raw in iter_path_strings(data)]


def latest_codex_state_db(home: Path) -> Path | None:
    candidates = sorted(home.glob("state_*.sqlite"), key=lambda item: item.stat().st_mtime)
    return candidates[-1] if candidates else None


def recent_codex_cwds(home: Path, *, days: int, limit: int) -> list[RepoSource]:
    db = latest_codex_state_db(home)
    if db is None:
        return []

    cutoff = int(time.time() - days * 86400)
    uri = f"file:{db}?mode=ro"
    try:
        conn = sqlite3.connect(uri, uri=True)
    except sqlite3.Error:
        return []

    try:
        rows = conn.execute(
            """
            SELECT cwd, MAX(updated_at) AS last_seen
            FROM threads
            WHERE cwd IS NOT NULL
              AND cwd != ''
              AND updated_at >= ?
            GROUP BY cwd
            ORDER BY last_seen DESC
            LIMIT ?
            """,
            (cutoff, limit),
        ).fetchall()
    except sqlite3.Error:
        rows = []
    finally:
        conn.close()

    return [RepoSource(Path(row[0]).expanduser(), f"recent codex cwd {db}") for row in rows]


def git_root(path: Path) -> Path | None:
    try:
        completed = subprocess.run(
            ["git", "-C", str(path), "rev-parse", "--show-toplevel"],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )
    except OSError:
        return None
    if completed.returncode != 0:
        return None
    root = completed.stdout.strip()
    return Path(root).resolve() if root else None


def should_skip(path: Path) -> bool:
    roots = (Path("/tmp"), Path("/private/tmp"), Path.home() / "Documents" / "Codex",
             codex_home() / "worktrees")
    return any(path.is_relative_to(root) for root in roots) or "/state/backups/" in str(path)


def normalize_repo(source: RepoSource) -> Path | None:
    try:
        candidate = source.path.expanduser().resolve()
    except OSError:
        return None
    if not candidate.exists() or should_skip(candidate):
        return None
    if candidate.is_file():
        candidate = candidate.parent
    root = git_root(candidate)
    if root is None and source.reason.startswith("recent codex cwd"):
        return None
    return root or candidate


def discover_sources(dot_agent: Path, *, days: int, limit: int) -> list[RepoSource]:
    sources = [RepoSource(dot_agent, "dot-agent")]
    sources.extend(codex_project_paths(codex_home() / "config.toml"))
    sources.extend(allowlist_paths(dot_agent / "state" / "collab" / "active-repos.toml"))
    sources.extend(recent_codex_cwds(codex_home(), days=days, limit=limit))
    return sources


def file_status(path: Path) -> str:
    if not path.is_file():
        return "missing"

    text = " ".join(read_text(path).split()).casefold()
    if any(anchor.casefold() in text for anchor in LEGACY_RUNTIME_ANCHORS):
        return "legacy-runtime"
    if any(anchor in text for anchor in RUNTIME_PREFERENCE_ANCHORS):
        return "ok"
    return "unverified"


def inspect_repo(repo: Path, sources: list[str], *, require_runtime: bool = False) -> RepoStatus:
    agents_status = file_status(repo / "AGENTS.md")
    claude_status = file_status(repo / "CLAUDE.md")
    status = RepoStatus(
        repo=str(repo),
        sources=sorted(set(sources)),
        agents=agents_status,
        claude=claude_status,
    )

    if agents_status == "legacy-runtime":
        status.findings.append(
            RepoFinding("WARN", str(repo), "AGENTS.md contains legacy peer-runtime wording; owner review required")
        )
    elif require_runtime and agents_status != "ok":
        status.findings.append(
            RepoFinding("WARN", str(repo), "harness AGENTS.md lacks the current runtime declaration")
        )
    elif agents_status != "ok":
        detail = "no local AGENTS.md" if agents_status == "missing" else "local runtime declaration unrecognized"
        status.findings.append(
            RepoFinding("INFO", str(repo), f"{detail}; inheritance not verified (not evidence of drift)")
        )

    return status


def audit(days: int, limit: int, *, dot_agent_only: bool = False) -> AuditResult:
    dot_agent = dot_agent_home()
    if dot_agent_only:
        result = AuditResult(discovered_paths=1)
        try:
            repo = dot_agent.resolve()
        except OSError:
            result.skipped.append(f"{dot_agent} (dot-agent)")
            return result
        if not repo.exists():
            result.skipped.append(f"{dot_agent} (dot-agent)")
            return result
        result.checked_repos.append(inspect_repo(git_root(repo) or repo, ["dot-agent"], require_runtime=True))
        return result

    sources = discover_sources(dot_agent, days=days, limit=limit)
    result = AuditResult(discovered_paths=len(sources))
    repos: dict[Path, list[str]] = {}

    for source in sources:
        repo = normalize_repo(source)
        if repo is None:
            result.skipped.append(f"{source.path} ({source.reason})")
            continue
        repos.setdefault(repo, []).append(source.reason)

    for repo, repo_sources in sorted(repos.items(), key=lambda item: str(item[0])):
        result.checked_repos.append(inspect_repo(repo, repo_sources, require_runtime="dot-agent" in repo_sources))

    return result


def print_text(result: AuditResult) -> None:
    findings = result.findings
    print("Repo Instruction Audit")
    print(f"Checked {len(result.checked_repos)} repo roots from {result.discovered_paths} discovered path(s).")
    print(f"WARN: {len(result.warnings)} known wording/source issue(s); "
          f"INFO: {len(findings) - len(result.warnings)} unverified local declaration(s).")
    print("Wording checks do not verify effective instruction loading or inheritance.")
    for finding in findings:
        print(f"{finding.severity}: {finding.repo} | {finding.message}")
    if result.skipped:
        print(f"INFO: skipped {len(result.skipped)} non-existent or out-of-scope path(s).")


def main() -> int:
    parser = argparse.ArgumentParser(description="Check known AGENTS.md runtime wording; preserve historical CLAUDE.md.")
    parser.add_argument("--strict", action="store_true", help="Exit non-zero when WARN findings exist.")
    parser.add_argument(
        "--dot-agent-only",
        action="store_true",
        help="Audit only the harness source repo; ignore unrelated recent/allowlisted repos.",
    )
    args = parser.parse_args()

    result = audit(days=30, limit=80, dot_agent_only=args.dot_agent_only)
    print_text(result)

    if args.strict and (result.warnings
                        or (args.dot_agent_only and len(result.checked_repos) != 1)):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
