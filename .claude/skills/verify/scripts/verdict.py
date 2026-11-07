#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import subprocess
import sys

LAYERS = ("checks", "contract", "live", "review")
DETERMINISTIC = ("checks", "contract")
STATUSES = ("PASS", "FAIL", "BLOCKED", "SKIP")
NEEDS_EVIDENCE = ("live", "review")
CARRIED = re.compile(r"carried from (\S+?)[.,;)]*(?:\s|$)", re.I)
SEVERITIES = ("BLOCKING", "NOTE")
OUTCOMES = ("fixed", "dismissed", "open")
CAUSES = ("missing context", "unmapped case", "bad data", "agent wrong")
WHERE = re.compile(r"[^\s:]+:\d+")
KIND = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
HIGH_RISK = (
    ("setup or install", re.compile(r"(^|/)(setup|install|apply)[^/]*$|retire-managed-runtime|verify-profile"
                                  r"|(^|/)scripts/(toml_edit\.py|toml_compat\.py|[\w-]+-audit\.py|codex-delegation-check\.sh)$"
                                  r"|(^|/)profiles/[^/]+/(.+\.(sh|py)|provided-skills)$")),
    ("hooks, CI or the merge gate", re.compile(r"(^|/)(\.githooks|hooks|\.github)/|(^|/)hooks\.json$|(^|/)scripts/check$|verify/scripts/verdict\.py$")),
    ("hooks, CI or the merge gate", re.compile(
        r"(^|/)scripts/(validate-skill-manifests|skill-catalog|profile-lint|check-constraints|one-home-check"
        r"|forbidden-words|no-comments|diagram-lint|readme-check|doc-fresh|owner-mode-upstream"
        r"|build-repo-skills|check-version-bump|dropped-rules|cloud-setup)\.(py|sh)$"
        r"|^template/conform\.py$|^scripts/[^/]+\.allow$|^\.gitignore$|^\.claude/settings\.json$")),
    ("AGENTS.md or CLAUDE.md", re.compile(r"(^|/)(AGENTS|CLAUDE)\.md$")),
    ("CONSTRAINTS.tsv", re.compile(r"(^|/)CONSTRAINTS\.tsv$")),
    ("model locks", re.compile(r"model-lock|(^|/)codex/")),
    ("private data", re.compile(r"private|(^|/)\.env", re.I)),
    ("money or credentials", re.compile(r"secret|credential|token|password|payment|billing|\.pem$|\.key$", re.I)),
    ("outside actions", re.compile(r"deploy|publish|send|mail|notify", re.I)),
)


class VerdictError(Exception):
    pass


def git(*args: str) -> str:
    result = subprocess.run(["git", *args], capture_output=True, text=True)
    if result.returncode:
        raise VerdictError(f"git {args[0]} failed: {result.stderr.strip() or 'not a git repository'}")
    return result.stdout.strip()


def tree_differs() -> str:
    if git("status", "--porcelain", "--untracked-files=normal", "--ignore-submodules=none"):
        return "uncommitted or untracked files"
    if subprocess.run(["git", "-c", "core.fileMode=true", "diff", "--quiet", "--ignore-submodules=none", "HEAD"], capture_output=True).returncode:
        return "changes against HEAD"
    for line in git("ls-files", "-v").splitlines():
        tag = line[:1]
        if tag == "S" or tag.islower():
            return f"assume-unchanged or skip-worktree flag on {line[2:]}"
    return ""


def verdicts_dir() -> Path:
    root = os.environ.get("DOT_AGENT_STATE_HOME") or "~/.dot-agent/state"
    return Path(root).expanduser() / "verdicts"


def parse_layer(value: str) -> tuple[str, dict]:
    name, _, rest = value.partition("=")
    status, _, evidence = rest.partition(":")
    status = status.strip().upper()
    if name not in LAYERS or status not in STATUSES:
        raise argparse.ArgumentTypeError(
            f"expected one of {'/'.join(LAYERS)}=one of {'/'.join(STATUSES)}[:evidence], got {value!r}")
    return name, {"status": status, "evidence": evidence.strip()}


def parse_finding(value: str) -> dict:
    parts = [part.strip() for part in value.split("|")]
    usage = ("expected SEVERITY|kind|file:line|summary|OUTCOME[|reason[|cause]] with SEVERITY "
             f"{'/'.join(SEVERITIES)}, OUTCOME {'/'.join(OUTCOMES)} and cause one of {', '.join(CAUSES)}, "
             f"got {value!r}")
    if len(parts) not in (5, 6, 7):
        raise argparse.ArgumentTypeError(usage)
    severity, kind, where, summary, outcome = parts[:5]
    reason = parts[5] if len(parts) > 5 else ""
    cause = parts[6].lower().replace("-", " ") if len(parts) > 6 else ""
    if severity.upper() not in SEVERITIES or outcome.lower() not in OUTCOMES or not summary:
        raise argparse.ArgumentTypeError(usage)
    if cause and cause not in CAUSES:
        raise argparse.ArgumentTypeError(usage)
    if not KIND.fullmatch(kind):
        raise argparse.ArgumentTypeError(f"finding kind {kind!r} must be lowercase-kebab, such as unpinned-merge")
    if not WHERE.fullmatch(where):
        raise argparse.ArgumentTypeError(f"finding needs file:line evidence, got {where!r}")
    if outcome.lower() == "dismissed" and not (reason and cause):
        raise argparse.ArgumentTypeError(
            f"a dismissed finding needs a reason and a cause ({', '.join(CAUSES)}): {value!r}")
    finding = {"severity": severity.upper(), "kind": kind, "where": where, "summary": summary,
               "outcome": outcome.lower(), "reason": reason}
    if cause:
        finding["cause"] = cause
    return finding


def open_blocking(findings: list) -> list:
    return [f for f in findings if f.get("severity") == "BLOCKING" and f.get("outcome") == "open"]


def overall(layers: dict, findings: list = ()) -> str:
    statuses = {layer["status"] for layer in layers.values()}
    for status in ("FAIL", "BLOCKED"):
        if status in statuses:
            return status
    if open_blocking(list(findings)) or layers["review"]["status"] != "PASS":
        return "BLOCKED"
    return "PASS" if any(layers[name]["status"] == "PASS" for name in DETERMINISTIC) else "BLOCKED"


def risk(changes: list, findings: list = ()) -> list:
    reasons = []
    for status, path in changes:
        if status == "removed":
            reasons.append(f"deletes {path}")
        for label, pattern in HIGH_RISK:
            if pattern.search(path) and label not in reasons:
                reasons.append(label)
    if any(f.get("severity") == "BLOCKING" and f.get("outcome") == "dismissed" for f in findings):
        reasons.append("a BLOCKING finding was dismissed")
    return reasons


def load(path: Path) -> dict:
    try:
        entry = json.loads(path.read_text())
    except (OSError, ValueError) as error:
        raise VerdictError(f"unreadable verdict {path}: {error}")
    layers = entry.get("layers") if isinstance(entry, dict) else None
    if not isinstance(layers, dict) or any(
            not isinstance(layers.get(name), dict) or layers[name].get("status") not in STATUSES
            for name in LAYERS):
        raise VerdictError(f"malformed verdict {path}: every layer needs a status")
    if not isinstance(entry.get("limits", []), list):
        raise VerdictError(f"malformed verdict {path}: limits must be a list")
    findings = entry.get("findings", [])
    if not isinstance(findings, list) or any(
            not isinstance(f, dict) or f.get("severity") not in SEVERITIES or f.get("outcome") not in OUTCOMES
            or not WHERE.fullmatch(str(f.get("where") or ""))
            or (f["outcome"] == "dismissed" and not str(f.get("reason") or "").strip())
            or f.get("cause", CAUSES[0]) not in CAUSES
            for f in findings):
        raise VerdictError(f"malformed verdict {path}: each finding needs a severity, file:line, an outcome "
                           "and a reason when dismissed")
    if entry.get("verdict") != overall(layers, findings):
        raise VerdictError(f"malformed verdict {path}: verdict does not follow from its layers and findings")
    approved = entry.get("approved")
    if approved is not None and (entry["verdict"] != "PASS" or not isinstance(approved, dict)
                                 or not str(approved.get("words") or "").strip()):
        raise VerdictError(f"malformed verdict {path}: only a PASS verdict can carry the owner's approval, with their words")
    return entry


def evidence_problem(layers: dict) -> str:
    empty = [name for name in NEEDS_EVIDENCE if not layers[name]["evidence"]]
    if empty:
        return f"{' and '.join(empty)} need evidence: say what was observed or why it was skipped"
    for name in LAYERS:
        for carried in CARRIED.findall(layers[name]["evidence"]):
            try:
                changed = git("diff", "--name-only", carried, "HEAD")
            except VerdictError:
                return f"{name} evidence is carried from {carried}, which is not a commit here"
            if changed:
                return (f"{name} evidence is carried from {carried}, but HEAD differs from it in "
                        f"{len(changed.splitlines())} file(s); rerun {name} on HEAD")
    return ""


def record(args) -> int:
    layers = dict(args.layer)
    missing = [name for name in LAYERS if name not in layers]
    if missing:
        print(f"verdict: missing layers: {', '.join(missing)}", file=sys.stderr)
        return 2
    differs = tree_differs()
    if differs:
        print(f"verdict: commit first; the tree differs from HEAD: {differs}", file=sys.stderr)
        return 2
    problem = evidence_problem(layers)
    if problem:
        print(f"verdict: {problem}", file=sys.stderr)
        return 2
    sha = git("rev-parse", "HEAD")
    entry = {
        "sha": sha,
        "repo": git("rev-parse", "--show-toplevel"),
        "claim": args.claim,
        "layers": {name: layers[name] for name in LAYERS},
        "findings": args.finding,
        "verdict": overall(layers, args.finding),
        "limits": args.limit,
        "recorded_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    target = verdicts_dir()
    target.mkdir(parents=True, exist_ok=True)
    (target / f"{sha}.json").write_text(json.dumps(entry, indent=2) + "\n")
    print(f"verdict: {entry['verdict']} recorded for {sha[:12]}")
    for finding in open_blocking(args.finding):
        print(f"open BLOCKING: {finding['where']} {finding['summary']}")
    return 0 if entry["verdict"] == "PASS" else 1


def check(args) -> int:
    sha = git("rev-parse", "HEAD")
    path = verdicts_dir() / f"{sha}.json"
    if not path.is_file():
        print(f"verdict: no verdict recorded for HEAD {sha[:12]}", file=sys.stderr)
        return 1
    entry = load(path)
    if entry.get("sha") != sha:
        print(f"verdict: recorded sha does not match HEAD {sha[:12]}", file=sys.stderr)
        return 1
    if entry.get("claim") != args.claim:
        print(f"verdict: recorded claim {entry.get('claim')!r} does not match {args.claim!r}", file=sys.stderr)
        return 1
    differs = tree_differs()
    if differs:
        print(f"verdict: the tree differs from HEAD: {differs}", file=sys.stderr)
        return 1
    layers = ", ".join(f"{name} {layer['status']}" for name, layer in entry["layers"].items())
    print(f"verdict: {entry['verdict']} for {sha[:12]} ({layers})")
    for limit in entry.get("limits", []):
        print(f"limit: {limit}")
    for f in entry.get("findings", []):
        if f.get("outcome") == "open":
            print(f"open finding: {f['severity']} {f['where']} {f['summary']}")
    if args.body:
        try:
            body = Path(args.body).read_text()
        except OSError as error:
            raise VerdictError(f"unreadable PR body {args.body}: {error}")
        problems = body_problems(entry, body)
        for problem in problems:
            print(f"verdict: {problem}", file=sys.stderr)
        if not problems and entry["verdict"] != "PASS":
            print("verdict: the PR may open BLOCKED; its body lists what blocks it; merging still needs PASS")
        return 1 if problems else 0
    return 0 if entry["verdict"] == "PASS" else 1


def body_problems(entry: dict, body: str) -> list:
    if entry["verdict"] == "PASS":
        return []
    section = re.search(r"^## Verification\s*$(.*?)(?=^## |\Z)", body, re.M | re.S)
    text = section.group(1) if section else ""
    if not text.strip():
        return [f"a {entry['verdict']} PR body needs a ## Verification section listing what blocks it"]
    blocking = open_blocking(entry.get("findings", []))
    if blocking:
        return [f"## Verification omits the open BLOCKING finding {f['where']} {f['summary']}"
                for f in blocking if f["where"] not in text]
    stopped = [name for name, layer in entry["layers"].items()
               if layer["status"] in ("FAIL", "BLOCKED") or (name == "review" and layer["status"] != "PASS")]
    stopped = stopped or list(DETERMINISTIC)
    said = [line for line in text.lower().splitlines() if re.search(r"\b(blocked|fail(ed)?|skip(ped)?)\b", line)]
    if not any(re.search(rf"\b{name}\b", line) for name in stopped for line in said):
        return [f"## Verification does not name the blocked layer ({', '.join(stopped)}) and why"]
    return []


def gate(sha: str, high_risk: list = ()) -> str:
    path = verdicts_dir() / f"{sha}.json"
    if not path.is_file():
        return f"no verdict recorded for {sha[:12]}"
    entry = load(path)
    if entry.get("sha") != sha:
        return f"the verdict file for {sha[:12]} names another sha"
    blocking = open_blocking(entry.get("findings", []))
    if blocking:
        return f"{sha[:12]} has {len(blocking)} open BLOCKING finding(s): " + "; ".join(
            f"{f['where']} {f['summary']}" for f in blocking)
    if entry["verdict"] != "PASS":
        return f"the verdict for {sha[:12]} is {entry['verdict']}; merging needs PASS"
    reasons = list(high_risk) + risk([], entry.get("findings", []))
    if reasons and not entry.get("approved"):
        return (f"{sha[:12]} is high risk ({', '.join(dict.fromkeys(reasons))}) and has no recorded approval "
                f"from the owner: verdict.py approve {sha[:12]} --words \"<their words>\" after they say yes")
    return ""


def gate_command(args) -> int:
    problem = gate(args.sha)
    if problem:
        print(f"verdict: {problem}", file=sys.stderr)
        return 1
    print(f"verdict: {args.sha[:12]} may merge if its changed paths are low risk")
    return 0


def approve(args) -> int:
    path = verdicts_dir() / f"{args.sha}.json"
    if not path.is_file():
        print(f"verdict: no verdict recorded for {args.sha[:12]}", file=sys.stderr)
        return 1
    entry = load(path)
    if entry["verdict"] != "PASS":
        print(f"verdict: only a PASS verdict can be approved; this one is {entry['verdict']}", file=sys.stderr)
        return 1
    if not args.words.strip():
        print("verdict: an approval needs the owner's words", file=sys.stderr)
        return 2
    entry["approved"] = {"words": args.words.strip(),
                         "at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    path.write_text(json.dumps(entry, indent=2) + "\n")
    print(f"verdict: the owner's approval recorded for {args.sha[:12]}")
    return 0


def branch_changes(base: str) -> list:
    changes = []
    for line in git("diff", "--name-status", "-M", f"{base}...HEAD").splitlines():
        status, *paths = line.split("\t")
        changes.append(("removed" if status.startswith("D") else "changed", paths[-1]))
        if status.startswith("R"):
            changes.append(("changed", paths[0]))
    return changes


def risk_command(args) -> int:
    sha = git("rev-parse", "HEAD")
    path = verdicts_dir() / f"{sha}.json"
    findings = load(path).get("findings", []) if path.is_file() else []
    reasons = risk(branch_changes(args.base), findings)
    print(f"Risk: high ({', '.join(reasons)})" if reasons else "Risk: low")
    return 0


def kinds(args) -> int:
    seen: dict[str, list[dict]] = {}
    for path in sorted(verdicts_dir().glob("*.json")):
        try:
            entry = load(path)
        except VerdictError:
            continue
        for finding in entry.get("findings", []):
            seen.setdefault(finding.get("kind") or "unnamed", []).append(
                {"where": f"{path.stem[:12]} {finding['where']}", "cause": finding.get("cause") or "unknown"})
    if args.by_cause:
        causes: dict[str, dict[str, int]] = {}
        for kind, items in seen.items():
            for item in items:
                causes.setdefault(item["cause"], {}).setdefault(kind, 0)
                causes[item["cause"]][kind] += 1
        if args.json:
            print(json.dumps(causes, indent=2, sort_keys=True))
            return 0
        for cause, by_kind in sorted(causes.items(), key=lambda pair: -sum(pair[1].values())):
            listed = ", ".join(f"{kind} {count}" for kind, count in sorted(by_kind.items(), key=lambda p: -p[1]))
            print(f"{cause}: {sum(by_kind.values())} ({listed})")
        return 0
    repeated = {kind: items for kind, items in seen.items() if len(items) >= args.min}
    if args.json:
        print(json.dumps({kind: [item["where"] for item in items] for kind, items in repeated.items()}, indent=2))
        return 0
    for kind, items in sorted(repeated.items()):
        causes = sorted({item["cause"] for item in items})
        print(f"{kind}: seen {len(items)} times, cause {', '.join(causes)} "
              f"({', '.join(item['where'] for item in items)}); propose a lint rule or CONSTRAINTS.tsv row")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Record or check a verify verdict pinned to HEAD.")
    sub = parser.add_subparsers(dest="command", required=True)
    rec = sub.add_parser("record", help="write the verdict for HEAD")
    rec.add_argument("--claim", required=True)
    rec.add_argument("--layer", action="append", type=parse_layer, default=[],
                     help="name=STATUS[:evidence] for checks, contract, live and review")
    rec.add_argument("--limit", action="append", default=[], help="an evidence limit")
    rec.add_argument("--finding", action="append", type=parse_finding, default=[],
                     help="SEVERITY|kind|file:line|summary|OUTCOME[|reason[|cause]]: BLOCKING or NOTE; "
                          "fixed, dismissed or open; cause missing context, unmapped case, bad data or "
                          "agent wrong (a dismissal needs a reason and a cause)")
    rec.set_defaults(func=record)
    chk = sub.add_parser("check", help="fail unless HEAD has a recorded PASS for the claim")
    chk.add_argument("--claim", required=True)
    chk.add_argument("--body", help="PR body file: exit 0 when the PR may open, PASS or BLOCKED with "
                                    "## Verification listing each open BLOCKING finding or the blocked layer")
    chk.set_defaults(func=check)
    gat = sub.add_parser("gate", help="fail unless a sha has a PASS verdict with no open BLOCKING finding")
    gat.add_argument("sha")
    gat.set_defaults(func=gate_command)
    apr = sub.add_parser("approve", help="record the owner's yes to merge a high-risk PR at this head")
    apr.add_argument("sha")
    apr.add_argument("--words", required=True)
    apr.set_defaults(func=approve)
    rsk = sub.add_parser("risk", help="print the risk tier of HEAD against a base, for the PR body")
    rsk.add_argument("--base", default="origin/main")
    rsk.set_defaults(func=risk_command)
    knd = sub.add_parser("kinds", help="list finding kinds seen at least --min times across verdicts")
    knd.add_argument("--min", type=int, default=2)
    knd.add_argument("--json", action="store_true")
    knd.add_argument("--by-cause", action="store_true", help="count findings by cause, then kind")
    knd.set_defaults(func=kinds)
    args = parser.parse_args()
    try:
        return args.func(args)
    except VerdictError as error:
        print(f"verdict: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
