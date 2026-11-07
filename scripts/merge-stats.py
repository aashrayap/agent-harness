#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

VERDICT = Path(__file__).resolve().parents[1] / "skills/engineering/verify/scripts/verdict.py"
_SPEC = importlib.util.spec_from_file_location("verdict", VERDICT)
verdict = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(verdict)
KINDS = ("auto", "owner", "outside")
LIMIT = ("reads only this Mac's verdicts, so a PR verified or approved on another Mac, "
         "or merged by the owner in the web UI, counts as outside")


def kind_of(sha: str) -> str:
    try:
        entry = verdict.load(verdict.verdicts_dir() / f"{sha}.json")
    except verdict.VerdictError:
        return "outside"
    if entry.get("sha") != sha or entry["verdict"] != "PASS" or "findings" not in entry:
        return "outside"
    return "owner" if entry.get("approved") else "auto"


def merged(repo: str, since: str) -> list[dict]:
    result = subprocess.run(
        ["gh", "pr", "list", "-R", repo, "--state", "merged", "--limit", "500", "--search",
         f"merged:>={since}", "--json", "number,headRefOid,mergedAt"],
        capture_output=True, text=True)
    if result.returncode:
        raise SystemExit(f"merge-stats: gh pr list -R {repo} failed: {result.stderr.strip()}")
    return json.loads(result.stdout)


def tally(prs: list[dict]) -> dict:
    counts = {kind: [] for kind in KINDS}
    for pr in prs:
        counts[kind_of(pr["headRefOid"])].append(pr["number"])
    return counts


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Count merged PRs by who let them through: auto (PASS, no approval needed), "
                    "owner (PASS with the owner's recorded approval) or outside (no PASS verdict with a review log "
                    "for the head: merged by hand, in the web UI or before 2.3.0).")
    parser.add_argument("repos", nargs="+", help="owner/repo")
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    since = (datetime.now(timezone.utc) - timedelta(days=args.days)).date().isoformat()
    report = {repo: tally(merged(repo, since)) for repo in args.repos}
    if args.json:
        print(json.dumps({"since": since, "limit": LIMIT, "repos": report}, indent=2))
        return 0
    print(f"Merges since {since}")
    for repo, counts in report.items():
        parts = [f"{kind} {len(numbers)}" for kind, numbers in counts.items()]
        print(f"{repo.split('/')[-1]}: {', '.join(parts)}")
        for kind, numbers in counts.items():
            if numbers:
                print(f"  {kind}: {', '.join(f'#{n}' for n in numbers)}")
    print(f"limit: {LIMIT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
