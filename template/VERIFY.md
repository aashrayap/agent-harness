# Verify recipe

Five layers; this file names this repo's surface for each.

| Layer | Here |
|---|---|
| L1 Checks | `scripts/check --tests`; it warns until `.git/info/private-markers` lists the owner's private names, one per line, so the names scan can run |
| L2 Contract | the test that pins the change; revert the source and watch it fail |
| L3 Live | CLI: `<command> --json`. Server: `<probe>`. UI: screenshot the current view first and compare it with the request or the owner's screenshot; screenshot it again when done, name both paths in the verdict and show the owner the after screenshot. Data: `<read that shows the stored result>` |
| L4 Review | every PR: a fresh-context reviewer reads [Review](#review) first; risk sets quick or deep |
| L5 Verdict | the result, pinned to the commit before the PR |

Outside judge: no judge yet. Name the person, user or metric outside this repo
that says the work is good once there is one.

## Review

The L4 reviewer reads this section before the diff.

- Broken here means: `<what a user or caller would see go wrong: wrong output, lost data, a crash, a report that lies>`.
- Skip: `<generated, vendored or lock files>`.
- README.md still shows the current truth: `scripts/readme-check.py` passes, and
  a behavior change updates README, RELEASES or VERIFY where they went stale,
  or the PR body says `No doc change needed: <why>` (`scripts/doc-fresh.py`; any file under `docs/` counts as a doc).
- Every finding cites `file:line` and is BLOCKING (it breaks something) or
  NOTE (style, nit or pre-existing). Only BLOCKING stops a merge.

## Golden cases

Inputs whose right answer the owner has signed off, kept as tests so
`scripts/check --tests` runs them: `<input>` gives `<signed-off answer>`.
Add one whenever a wrong answer reaches the owner; a golden case never
changes without the owner's yes.

## Misses by cause

Each review finding may name its cause: context was missing, a case was
unmapped, the data was bad, or the agent was wrong. A kind seen twice becomes
a `CONSTRAINTS.tsv` row.
