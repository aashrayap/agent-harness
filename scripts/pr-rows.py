#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import binascii
from datetime import datetime, timedelta, timezone
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys

VERDICT = Path(__file__).resolve().parents[1] / "skills/engineering/verify/scripts/verdict.py"
_SPEC = importlib.util.spec_from_file_location("verdict", VERDICT)
verdict = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(verdict)

FIELDS = (
    ("link", re.compile(r"\[[\w.-]+#\d+\]\(https://\S+\)")),
    ("version", re.compile(r"v(\d+\.\d+\.\d+|—)")),
    ("title", re.compile(r"\S.* — \S.*")),
    ("checks", re.compile(r"checks [✅❌]")),
    ("verdict", re.compile(r"verdict (PASS|BLOCKED)")),
    ("risk", re.compile(r"risk (low|high)")),
    ("needs", re.compile(r"needs: \S.*")),
)
GROUPS = ("Needs you", "Running", "Done")
HEADING = re.compile(r"^\W*(Needs you|Running|Done)\W*$")
SEPARATOR = " · "
GREEN = {"SUCCESS", "NEUTRAL", "SKIPPED"}
TITLE = re.compile(r"^(\d+\.\d+\.\d+):\s*(.*)$")
SEMVER = re.compile(r"\d+\.\d+\.\d+")
NO_VERSION = "—"
JSON_FIELDS = "number,title,body,url,headRefOid,isDraft,statusCheckRollup,mergedAt"


def field_of(part: str) -> str:
    for name, pattern in sorted(FIELDS, key=lambda field: field[0] == "title"):
        if pattern.fullmatch(part):
            return name
    return ""


def check_row(row: str) -> list[str]:
    found = [field_of(part) for part in row.strip().split(SEPARATOR)]
    names = [name for name, _ in FIELDS]
    missing = [name for name in names if name not in found]
    if not missing and found != names:
        missing.append("field order")
    return missing


def entry_for(sha: str) -> dict | None:
    try:
        entry = verdict.load(verdict.verdicts_dir() / f"{sha}.json")
    except verdict.VerdictError:
        return None
    return entry if entry.get("sha") == sha else None


def checks_green(rollup: list[dict]) -> bool:
    states = [item.get("conclusion") or item.get("state") or "" for item in rollup or []]
    return bool(states) and all(state.upper() in GREEN for state in states)


def plain(text: str) -> str:
    return " ".join(re.sub(r"[`*_\[\]]", "", text).replace("·", "-").replace(" — ", " - ").split())


def why_line(body: str) -> str:
    section = re.split(r"^## Why\s*$", body or "", maxsplit=1, flags=re.M)
    text = section[1] if len(section) == 2 else (body or "")
    text = re.split(r"^## ", text, maxsplit=1, flags=re.M)[0]
    sentence = re.split(r"(?<=[.!?])\s", plain(text), maxsplit=1)[0]
    return sentence[:117] + "..." if len(sentence) > 120 else sentence


def title_parts(pr: dict) -> tuple[str, str, str]:
    match = TITLE.match(pr["title"])
    version, rest = (match.group(1), match.group(2)) if match else ("", pr["title"])
    short, _, what = rest.partition(": ")
    what = what or why_line(pr.get("body", "")) or "see the PR"
    return version, plain(short), plain(what)


def branch_version(repo: str, sha: str) -> str:
    result = subprocess.run(["gh", "api", f"repos/{repo}/contents/VERSION?ref={sha}", "--jq", ".content"],
                            capture_output=True, text=True)
    if result.returncode:
        return ""
    try:
        text = base64.b64decode(result.stdout).decode().strip()
    except (binascii.Error, UnicodeDecodeError):
        return ""
    return text if SEMVER.fullmatch(text) else ""


def row_for(repo: str, pr: dict, changes: list | None, head_version: str = "") -> tuple[str, str]:
    title_version, short, what = title_parts(pr)
    version = head_version or title_version or NO_VERSION
    green = checks_green(pr.get("statusCheckRollup", []))
    entry = entry_for(pr["headRefOid"])
    status = "PASS" if entry and entry["verdict"] == "PASS" else "BLOCKED"
    findings = entry.get("findings", []) if entry else []
    high = ["unread changed files"] if changes is None else verdict.risk(changes, findings)
    blocking = len(verdict.open_blocking(findings))
    if pr.get("mergedAt"):
        group, needs = "Done", "none, merged"
    elif pr.get("isDraft"):
        group, needs = "Running", "agent: finish the draft"
    elif not green:
        group, needs = "Running", "agent: green checks"
    elif blocking:
        group, needs = "Running", f"agent: fix {blocking} BLOCKING finding(s)"
    elif status != "PASS":
        group, needs = "Running", "agent: a PASS verdict"
    elif high and not entry.get("approved"):
        group, needs = "Needs you", "merge yes/no"
    else:
        group, needs = "Running", "none, the agent merges"
    row = SEPARATOR.join([
        f"[{repo.split('/')[-1]}#{pr['number']}]({pr['url']})",
        f"v{version}",
        f"{short} — {what}",
        f"checks {'✅' if green else '❌'}",
        f"verdict {status}",
        f"risk {'high' if high else 'low'}",
        f"needs: {needs}",
    ])
    return group, row


def gh_json(args: list[str]):
    result = subprocess.run(["gh", *args], capture_output=True, text=True)
    if result.returncode:
        raise SystemExit(f"pr-rows: gh {' '.join(args[:3])} failed: {result.stderr.strip()}")
    return json.loads(result.stdout)


def pr_changes(repo: str, number: int) -> list | None:
    try:
        pages = gh_json(["api", f"repos/{repo}/pulls/{number}/files", "--paginate", "--slurp"])
    except SystemExit:
        return None
    files = [item for page in pages for item in page]
    return ([(item.get("status") or "", item.get("filename") or "") for item in files]
            + [("renamed", item["previous_filename"]) for item in files if item.get("previous_filename")])


def list_prs(repo: str, days: int) -> list[dict]:
    open_prs = gh_json(["pr", "list", "-R", repo, "--state", "open", "--json", JSON_FIELDS])
    since = (datetime.now(timezone.utc) - timedelta(days=days)).date().isoformat()
    merged = gh_json(["pr", "list", "-R", repo, "--state", "merged", "--search", f"merged:>={since}",
                      "--json", JSON_FIELDS])
    return open_prs + merged


def grouped(rows: list[tuple[str, str]]) -> list[str]:
    lines = []
    for group in GROUPS:
        members = [row for name, row in rows if name == group]
        if members:
            lines += [group, *members]
    return lines


def report(rows: list[str]) -> int:
    failed = 0
    for row in rows:
        missing = check_row(row)
        if missing:
            failed = 1
            print(f"pr-rows: row missing {', '.join(missing)}: {row}", file=sys.stderr)
    return failed


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Print one row per PR under Needs you, Running and Done, or check rows: "
                    "[repo#N](url) · vX.Y.Z · short title — what it does · checks ✅/❌ · "
                    "verdict PASS/BLOCKED · risk low/high · needs: ...")
    parser.add_argument("repos", nargs="*", help="owner/repo to list open and recently merged PRs from")
    parser.add_argument("--days", type=int, default=1, help="Done covers PRs merged in this many days")
    parser.add_argument("--check", metavar="FILE", help="check each row of FILE ('-' for stdin)")
    args = parser.parse_args()
    if args.check:
        text = sys.stdin.read() if args.check == "-" else Path(args.check).read_text()
        rows = [line for line in text.splitlines() if line.strip() and not HEADING.match(line)]
        failed = report(rows)
        if not failed:
            print(f"pr-rows: PASS {len(rows)} rows")
        return failed
    if not args.repos:
        parser.error("give at least one owner/repo, or --check FILE")
    rows = [row_for(repo, pr, pr_changes(repo, pr["number"]), branch_version(repo, pr["headRefOid"]))
            for repo in args.repos for pr in list_prs(repo, args.days)]
    for line in grouped(rows):
        print(line)
    return report([row for _, row in rows])


if __name__ == "__main__":
    sys.exit(main())
