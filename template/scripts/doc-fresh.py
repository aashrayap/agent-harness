#!/usr/bin/env python3
import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

DOCS = {"README.md", "RELEASES.md", "VERIFY.md"}
EXEMPT = re.compile(r"^No doc change needed: \S", re.M)


def changed(base):
    result = subprocess.run(["git", "diff", "--name-only", f"{base}...HEAD"], capture_output=True, text=True)
    return result.stdout.split() if result.returncode == 0 else None


def pr_body(path):
    if path:
        return Path(path).read_text(encoding="utf-8")
    event = os.environ.get("GITHUB_EVENT_PATH")
    if event and Path(event).is_file():
        return (json.loads(Path(event).read_text()).get("pull_request") or {}).get("body") or ""
    return None


def main(argv=None):
    parser = argparse.ArgumentParser(description="Fail a behavior change that leaves README, RELEASES, VERIFY and docs/ untouched.")
    parser.add_argument("base", nargs="?", default="origin/main")
    parser.add_argument("--body", help="PR body file; CI reads it from GITHUB_EVENT_PATH")
    args = parser.parse_args(argv)
    files = changed(args.base)
    if files is None:
        if os.environ.get("CI"):
            print(f"ERROR: no {args.base} to compare with in CI; check out with fetch-depth: 0 and set BASE_REF")
            print("doc-fresh: FAIL")
            return 1
        print(f"doc-fresh: SKIP: no {args.base} to compare with")
        return 0
    docs = [name for name in files if name in DOCS or name.startswith("docs/")]
    behavior = [name for name in files if not name.endswith(".md") and name not in docs]
    if not behavior or docs:
        print("doc-fresh: PASS")
        return 0
    body = pr_body(args.body)
    if body is None:
        print("doc-fresh: SKIP locally: no PR body; CI enforces it")
        return 0
    if EXEMPT.search(body):
        print("doc-fresh: PASS (PR body: no doc change needed)")
        return 0
    print(f"ERROR: {len(behavior)} behavior file(s) changed ({', '.join(behavior[:3])}) but not README.md, "
          "RELEASES.md, VERIFY.md or docs/; update the stale one, or add a PR body line 'No doc change needed: <why>'")
    print("doc-fresh: FAIL")
    return 1


if __name__ == "__main__":
    sys.exit(main())
