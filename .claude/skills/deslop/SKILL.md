---
name: deslop
description: Hunt and delete slop (needless comments, stale sentences, copied rules, dead code) in a diff or the whole repo. A read-only hunter flags; you verify and delete. Invoke with $deslop or /deslop.
disable-model-invocation: true
---

# Deslop

Spawn the hunter. Act on accepted findings. Defer to the hunter's fresh view.

## Scope

Use the caller's paths or diff. `repo` audits the whole repository. Otherwise
use the current diff against the base branch, including the working tree.

## Steps

1. Spawn one fresh read-only helper: in Claude Code the read-only `Explore`
   type; in Codex a helper told it may not edit. Pass the scope and
   [references/hunter.md](references/hunter.md). Do not restate its rules.
2. Check every flag against the code. Reject flags outside the scope, flags on
   a real keep, and flags whose reason is wrong. Accept the rest. Keep only what
   matches the hunter's keep list, with proof the reason holds.
3. Delete accepted slop. For a `RESHAPE` flag, make the code say it (rename,
   extract, type) when the change is small; otherwise report it open.
4. A comment that encodes a constraint ("do not remove", "do not change this
   wording") becomes a check (test, lint or type) when that is cheap, and then
   the comment goes. Otherwise keep the comment and report the constraint
   open.
5. Rerun the checks for what changed.
6. Report lines removed, keeps with their reasons, `RESHAPE` items and open
   work.

On someone else's branch, report only.

Adapted from poteto's `no-comments` and Comment Sicko; see
[UPSTREAM.md](references/UPSTREAM.md).
