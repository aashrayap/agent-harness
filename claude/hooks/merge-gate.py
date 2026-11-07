#!/usr/bin/env python3
import functools
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
GH_VALUE_FLAGS = {"-R", "--repo", "-t", "--subject", "-b", "--body", "-F", "--body-file",
                  "-A", "--author-email", "--match-head-commit"}
PASSING = {"pass", "skipping"}
API_MERGE = re.compile(r"pulls/[^/\s]+/merge\b|\b(mergePullRequest|enablePullRequestAutoMerge)\b")
HTTP_TOOLS = {"curl", "wget", "http", "https", "xh"}
API_ONLY = ("merge through `gh pr merge <n> --match-head-commit <sha>` so the gate can check it; "
            "a merge through the REST or GraphQL API or an MCP merge tool skips the gate")


AUTO_ONLY = "arming auto-merge skips this gate, so the owner arms it themselves in the app or GitHub; otherwise merge through `gh pr merge`"


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@functools.cache
def helpers():
    return load("no_push_to_main", HERE / "no-push-to-main.py")


def gh_merge(argv):
    positional, repo, match, skip = [], [], None, None
    for word in argv:
        if skip:
            if skip in ("-R", "--repo"):
                repo = ["--repo", word]
            elif skip == "--match-head-commit":
                match = word
            skip = None
        elif word.startswith("--repo="):
            repo = ["--repo", word.split("=", 1)[1]]
        elif word.startswith("--match-head-commit="):
            match = word.split("=", 1)[1]
        elif word in GH_VALUE_FLAGS:
            skip = word
        elif not word.startswith("-"):
            positional.append(word)
    if positional[:2] != ["pr", "merge"]:
        return None
    return positional[2:3] + repo, match


def merges(command, cwd=None, depth=0):
    if depth > 4:
        return []
    shell = helpers()
    command, bodies = shell.split_heredocs(command)
    found = [merge for body in bodies for merge in merges(body, cwd, depth + 1)]
    try:
        words = shell.tokens(command)
    except ValueError:
        loose = re.search(r"\bgh\b.*\bpr\s+merge\b", command, re.S) or API_MERGE.search(command)
        return found + ([(None, None, cwd)] if loose else [])
    for inner in re.findall(r"\$\((.*)\)|`([^`]*)`", command, re.S):
        found += merges("".join(inner), cwd, depth + 1)
    for argv in shell.segments(words):
        if argv[:1] in (["cd"], ["pushd"]) and len(argv) > 1:
            cwd = os.path.join(cwd or os.getcwd(), os.path.expanduser(argv[1]))
            continue
        for index, word in enumerate(argv):
            name = os.path.basename(word)
            rest = argv[index + 1:]
            if name == "gh":
                merge = gh_merge(rest)
                if merge is not None:
                    found.append((*merge, cwd))
                elif "api" in rest and any(API_MERGE.search(item) for item in rest):
                    found.append((None, "api", cwd))
                break
            if name in HTTP_TOOLS and any(API_MERGE.search(item) for item in rest):
                found.append((None, "api", cwd))
                break
            if name in shell.SHELLS and rest:
                found += merges(" ".join(rest), cwd, depth + 1)
                break
    return found


def run_gh(args, cwd):
    try:
        result = subprocess.run(["gh", *args], capture_output=True, text=True, cwd=cwd, timeout=20)
    except (OSError, subprocess.TimeoutExpired) as error:
        return None, str(error)
    try:
        return json.loads(result.stdout), ""
    except ValueError:
        return None, (result.stderr or result.stdout).strip() or f"gh exited {result.returncode}"


def changes(view, cwd, gh):
    match = re.match(r"https://github\.com/([^/]+/[^/]+)/pull/(\d+)", str(view.get("url") or ""))
    if not match:
        return None, "the PR has no GitHub URL"
    pages, error = gh(["api", f"repos/{match.group(1)}/pulls/{match.group(2)}/files", "--paginate", "--slurp"], cwd)
    if not isinstance(pages, list) or not all(isinstance(page, list) for page in pages):
        return None, error or "unexpected files response"
    files = [item for page in pages for item in page if isinstance(item, dict)]
    names = {item.get("filename") for item in files} - {None, ""}
    if len(names) != view.get("changedFiles", len(names)):
        return None, f"read {len(names)} of {view.get('changedFiles')} changed files"
    found = [(item.get("status") or "", item.get("filename") or "") for item in files]
    return found + [("renamed", item["previous_filename"]) for item in files if item.get("previous_filename")], ""


def problems(selector, match, cwd, gh=run_gh, gate=None):
    view, error = gh(["pr", "view", *selector, "--json", "headRefOid,number,url,changedFiles"], cwd)
    if not isinstance(view, dict) or not view.get("headRefOid"):
        return [f"could not read the PR ({error or 'no head commit'})"]
    sha, number = view["headRefOid"], view.get("number", "?")
    found = []
    if match is None:
        found.append(f"add --match-head-commit {sha} so the merge lands only the head this gate checked")
    elif match != sha:
        found.append(f"--match-head-commit {match} is not #{number}'s head {sha}")
    checks, error = gh(["pr", "checks", *selector, "--json", "name,bucket"], cwd)
    if not isinstance(checks, list):
        found.append(f"could not read checks for #{number} ({error})")
    elif not checks:
        found.append(f"#{number} reports no checks")
    else:
        red = [f"{check.get('name')} {check.get('bucket')}" for check in checks
               if check.get("bucket") not in PASSING]
        if red:
            found.append(f"#{number} checks are not all green: {', '.join(red)}")
        elif not any(check.get("bucket") == "pass" for check in checks):
            found.append(f"#{number} has only skipped checks")
    verdict = load("verdict", ROOT / "skills/engineering/verify/scripts/verdict.py")
    changed, error = changes(view, cwd, gh)
    if changed is None:
        found.append(f"#{number} changed files could not be read, so its risk is unknown: {error}")
    high = ["unread changed files: " + error] if changed is None else verdict.risk(changed)
    try:
        problem = (gate or verdict.gate)(sha, high)
    except verdict.VerdictError as error:
        problem = str(error)
    if problem:
        found.append(problem)
    return found


def decide(event, gh=run_gh, gate=None):
    tool_input = event.get("tool_input")
    name = str(event.get("tool_name") or "")
    if name.startswith("mcp__") and "merge_pull_request" in name:
        return deny(API_ONLY)
    if name.endswith("__set_auto_merge"):
        return deny(AUTO_ONLY) if isinstance(tool_input, dict) and tool_input.get("enabled") is not False else None
    if name not in helpers().COMMAND_TOOLS or not isinstance(tool_input, dict):
        return None
    cwd = helpers().command_cwd(event, tool_input)
    found = []
    for selector, match, where in merges(str(tool_input.get("command") or ""), cwd):
        if selector is None:
            found.append(API_ONLY if match == "api" else "could not parse the merge command")
        else:
            found += problems(selector, match, where, gh, gate)
    if not found:
        return None
    return deny("; ".join(found))


def deny(problem):
    reason = ("Merge gate: " + problem + ". A merge needs green checks, a PASS verdict with no open "
              "BLOCKING finding for the PR head pinned with --match-head-commit, and for a high-risk PR "
              "The owner's yes recorded with verdict.py approve.")
    return {"hookSpecificOutput": {"hookEventName": "PreToolUse",
                                   "permissionDecision": "deny",
                                   "permissionDecisionReason": reason}}


def main():
    try:
        event = json.load(sys.stdin)
    except ValueError:
        return 0
    try:
        decision = decide(event if isinstance(event, dict) else {})
    except Exception as error:
        decision = {"hookSpecificOutput": {"hookEventName": "PreToolUse",
                                           "permissionDecision": "deny",
                                           "permissionDecisionReason": f"Merge gate failed: {error!r}"}}
    if decision:
        print(json.dumps(decision))
    return 0


if __name__ == "__main__":
    sys.exit(main())
