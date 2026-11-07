#!/usr/bin/env python3
import json
import re
import sys

CHANGES = {"Edit", "Write", "NotebookEdit", "MultiEdit"}
SHIPS = re.compile(r"\bgit\s+(commit|push)\b|\bgh\s+pr\s+(create|merge|edit)\b")
OUTCOME = re.compile(r"^(?![-\[])\W{0,3}(result|needs input|failed):", re.I | re.M)
REASON = ("This turn changed files or shipped work, so the reply must map the latest requests to done, "
          "not done or parked, and end with exactly one outcome line: `result: <delivered outcome>`, "
          "`needs input: <single human action>` or `failed: <structural reason>` (AGENTS.md, Communication). "
          "Found {count}. Add it, or say what is left and continue.")


def prompt(entry):
    content = (entry.get("message") or {}).get("content")
    if entry.get("type") != "user" or entry.get("isMeta") or entry.get("isSidechain"):
        return False
    if isinstance(content, str):
        return True
    return isinstance(content, list) and not any(
        isinstance(block, dict) and block.get("type") == "tool_result" for block in content)


def turn(lines):
    entries = []
    for line in lines:
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        if isinstance(entry, dict):
            entries.append(entry)
    start = max((index for index, entry in enumerate(entries) if prompt(entry)), default=-1)
    return [entry for entry in entries[start + 1:]
            if entry.get("type") == "assistant" and not entry.get("isSidechain")]


def blocks(entry):
    content = (entry.get("message") or {}).get("content")
    return [block for block in content if isinstance(block, dict)] if isinstance(content, list) else []


def substantive(entries):
    for entry in entries:
        for block in blocks(entry):
            if block.get("type") != "tool_use":
                continue
            if block.get("name") in CHANGES:
                return True
            command = (block.get("input") or {}).get("command") if block.get("name") == "Bash" else None
            if isinstance(command, str) and SHIPS.search(command):
                return True
    return False


def final_text(entries):
    for entry in reversed(entries):
        texts = [block.get("text") or "" for block in blocks(entry) if block.get("type") == "text"]
        if any(block.get("type") == "tool_use" for block in blocks(entry)):
            return None
        if texts:
            return "\n".join(texts)
    return None


def decide(event, read=lambda path: open(path, encoding="utf-8").read().splitlines()):
    if event.get("stop_hook_active") or not isinstance(event.get("transcript_path"), str):
        return None
    try:
        entries = turn(read(event["transcript_path"]))
    except OSError:
        return None
    if not substantive(entries):
        return None
    text = final_text(entries)
    if text is None:
        return None
    count = len(OUTCOME.findall(text))
    if count == 1:
        return None
    return {"decision": "block", "reason": REASON.format(count=count)}


def main():
    try:
        event = json.load(sys.stdin)
    except ValueError:
        return 0
    decision = decide(event if isinstance(event, dict) else {})
    if decision:
        print(json.dumps(decision))
    return 0


if __name__ == "__main__":
    sys.exit(main())
