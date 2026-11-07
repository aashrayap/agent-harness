#!/usr/bin/env python3
import json
import re
import sys

SENDS = re.compile(r"^mcp__(?!ccd_).+__(send\w*|reply\w*|forward\w*|post_?message|create_event|update_event"
                   r"|respond_to_event|delete_event|share_file|send_draft)$", re.I)
REASON = ("Sending, replying, forwarding, inviting or sharing as the owner waits for their yes in this prompt "
          "(AGENTS.md, Always pause).")


def decide(event):
    if not SENDS.match(str(event.get("tool_name") or "")):
        return None
    return {"hookSpecificOutput": {"hookEventName": "PreToolUse",
                                   "permissionDecision": "ask",
                                   "permissionDecisionReason": REASON}}


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
