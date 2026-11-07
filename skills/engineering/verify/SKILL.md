---
name: verify
description: Verify a change or review a diff or PR in five layers, from checks to a verdict pinned to the commit. Use before saying work is done, or to review or validate a PR, fix or feature.
---

# Verify

Name the exact claim, the frozen target commit, the changed scope and the
failure modes that matter. Then run the layers in order, scaled to risk as L1
and L4 describe. Each layer ends PASS,
FAIL, BLOCKED or SKIP with a reason; see
[the verdict contract](references/verdict-report.md). Pick the checks inside a
layer from [verification options](references/verification-options.md).

A review request alone authorizes reporting, not fixing someone else's branch.
With implementation authority, repair in-scope failures, rerun the affected
layers and keep going.

## L1 Checks

Run the repository's deterministic gate: lint, typecheck and the focused tests
that pin the claim. In the dot-agent repo a docs, config or small local edit with
no new behaviour runs those focused tests plus `PYTHON=python3.13 scripts/check`;
anything else adds `--tests` for the full suite. On a noisy repository, compare against the base and fail only
on new failures.

## L2 Contract tests

Pin the claim with a test against a public interface and synthetic fixtures,
never live or private data. Revert must fail for each new behaviour test:
revert only the source change, run the test and watch it fail, then restore. A
test that still passes without the change proves nothing; fix it or drop it.
Edits to existing tests and changes with no new behaviour, such as docs and
pure config, skip the revert. Docs and pure config changes record SKIP.

## L3 Live probes

Run only when the claim is about a live surface; otherwise record SKIP. Drive
that surface: a CLI in the terminal, a server
through its socket, a UI in a browser (see references/browser-verification.md) or with Claude computer use. Add one off-happy-path probe the diff points at: wrong input, stale
state or the adjacent error path. Never test a destructive path against live
data when an isolated fixture can prove it. Use
[blast radius](references/blast-radius.md) when safety depends on code outside
the changed path. A surface you cannot reach is BLOCKED, not PASS.

A UI change is proven by screenshots. Whoever builds it screenshots the
current version first and compares it with what the owner described or sent; the
differences are the work. A verifier who arrives later takes the before view
from the base commit. When the change is done, screenshot the same view again
and name both screenshot paths in the `live=` evidence. Show the after
screenshot to the owner: inline in the desktop app, as its file path in a terminal.
A UI claim without an after screenshot is BLOCKED, not PASS; where no screen
is reachable, record BLOCKED with that reason.

## L4 Independent review

Every PR gets one; risk sets the depth. Quick: one pass over the diff for what
breaks. Deep: also trace callers, setup paths and failure modes. Deep is for a
high-risk change (`verdict.py risk` prints the tier) or an explicit review
request. A PASS verdict needs a passing review layer.

1. Freeze the target commit and diff. Take reviewer model and effort from the
   runtime reference AGENTS.md links, and confirm they are available. No
   available reviewer records BLOCKED, never SKIP.
2. Start one fresh-context reviewer. Give it the frozen target, the claim, the
   requirements, the repository instructions and the Review section of the
   repository's VERIFY.md (what broken means there, paths to skip). Brief it to
   disprove the claim: an exploit, a counterexample or a missed requirement.
   Also ask: does the change solve its stated problem and fit the system; on a
   bug fix, does it fix the root cause or only the symptom; which CLAUDE.md or
   AGENTS.md lines does it make stale. Each finding cites `file:line` and is
   BLOCKING when it breaks something, or NOTE for style, nits and problems the
   change did not introduce. No finding twice. Do not steer its conclusions or
   share your own evidence.
3. Verify each finding against the actual code path, and against primary
   documentation when external behavior matters. Dismiss speculative cases and
   broad rewrites with a short reason. When a confirmed finding names a bug
   class, sweep for sibling instances the change introduced.
4. Turn each confirmed BLOCKING finding into a failing test, then fix it when
   authorized. Ask only when a fix needs a new contract, owner or authority.
5. Rounds: one review, then one re-check that reads only the fix's diff. A
   BLOCKING finding still open after the re-check stays open: the PR may open
   BLOCKED with it listed, and the approach needs rethinking before more rounds.
6. Log every finding with the verdict, each fixed, dismissed with a reason, or
   open. Dismissing a BLOCKING finding makes the PR high risk.

A clean review states no actionable findings for the inspected commit. Review
never substitutes for an L2 or L3 behavioral check.

When the same kind of finding appears twice, it becomes a lint rule or a
CONSTRAINTS.tsv row at the strongest level that holds. `verdict.py kinds`
lists every kind seen at least twice across recorded verdicts, with its
causes, and `verdict.py kinds --by-cause` counts misses by cause. No scheduled job reads them, so run both when
closing a review. The
[correct skill](../correct/SKILL.md) turns a repeated kind or correction into a
rule.

## L5 Verdict

Commit first, then record the verdict for that exact commit with
`scripts/verdict.py` from this skill's folder:

```bash
python3 <this skill's folder>/scripts/verdict.py record \
  --claim "<the claim>" \
  --layer "checks=PASS:scripts/check --tests" --layer contract=PASS \
  --layer "live=BLOCKED:<why the surface was unreachable>" \
  --layer "review=PASS:quick review, 1 NOTE" \
  --finding "NOTE|stale-doc|README.md:12|names the old flag|fixed" \
  --limit "<what was not observed>"
```

Each `--layer` takes `name=STATUS` or `name=STATUS:evidence`, and all four
layers are required; `live` and `review` always need evidence, even a SKIP
reason. Each `--finding` is
`SEVERITY|kind|file:line|summary|OUTCOME[|reason[|cause]]`: severity
BLOCKING or NOTE, a lowercase-kebab kind, outcome fixed, dismissed (with a
reason and a cause) or open, and the cause of the miss: missing context,
unmapped case, bad data or agent wrong (leave the reason empty to give only a
cause: `NOTE|stale-doc|a.md:3|old flag|fixed||missing context`). Evidence that says "carried from <sha>" records only
when that commit's tree equals HEAD; otherwise rerun the layer. Recording
refuses a tree that differs from HEAD. The verdict is FAIL if any layer
failed; BLOCKED if any was blocked, if review did not pass, if a BLOCKING
finding is open, or if neither `checks` nor `contract` passed; otherwise PASS.
Run `verdict.py check --claim "<the claim>"` before claiming done or opening a
PR: it exits 0 only when HEAD has a recorded PASS for that claim, so any new
commit needs a fresh verdict. Exit 1 means no PASS (FAIL, BLOCKED or stale);
read the recorded layers before deciding.

A BLOCKED verdict may open a PR when the body lists its open findings or
blocked layer, which `verdict.py check --claim "<the claim>" --body <file>`
checks; merging needs PASS. FAIL opens nothing. The merge gate hook
denies `gh pr merge` unless the PR's checks are all green, the head has a PASS
verdict with no open BLOCKING finding, the command pins that head with
`--match-head-commit <head sha>`, and a high-risk PR carries the owner's yes,
recorded with `verdict.py approve <head sha> --words "<their words>"` only after
they give it. A low-risk PR that passes the gate may be merged by the agent.
Ignored and locally excluded files are not checked; name them as a limit when
they matter.

Report findings first, with severity and paths, then the claim, the per-layer
results, the reviewer settings and the evidence limits.
