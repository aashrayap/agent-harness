# Verify recipe

The [verify skill](skills/engineering/verify/SKILL.md) runs five layers; this
file names dot-agent's surface for each. Record the verdict with
`python3.13 skills/engineering/verify/scripts/verdict.py record`.

| Layer | Here |
|---|---|
| L1 Checks | `PYTHON=python3.13 scripts/check --tests` (pre-commit runs it without `--tests`; CI with). Locally it warns until `.git/info/private-markers` lists the owner's private names, so the names scan can run; CI skips only that scan |
| L2 Contract | the test that pins the change; revert the source and watch it fail |
| L3 Live | setup into a temporary HOME (`HOME=$(mktemp -d) ./setup.sh` from a copy at `$HOME/.dot-agent`), then `python3.13 scripts/verify-profile.py`; on the owner's machine after a merge, `./setup.sh` then `verify-profile` |
| L4 Review | every PR: a fresh-context reviewer reads [Review](#review) first; deep for a high-risk PR (`verdict.py risk`), quick otherwise |
| L5 Verdict | pinned to the commit before the PR |

Outside judge: the owner, on their own machines; there is no automated judge yet.

## Review

Read this before the diff when reviewing a dot-agent change.

- Broken here means: setup loses or overwrites owner content, or installs
  something `verify-profile` would reject; a hook or the merge gate lets a
  denied action through or denies an allowed one; a check passes on the
  violation it names; a CONSTRAINTS.tsv row points at an enforcer that no
  longer enforces it; an instruction contradicts another or names a model
  outside the lock; private data reaches Git.
- A stale README.md, RELEASES.md or VERIFY.md is broken too (CONSTRAINTS
  `readme-current`, `docs-fresh`).
- Skip: generated skill tables, old RELEASES.md entries and the `.claude/skills/` copy (the drift check pins it to `skills/`).
- Findings follow the verify skill's L4 rules: `file:line` evidence and a
  BLOCKING or NOTE severity.
