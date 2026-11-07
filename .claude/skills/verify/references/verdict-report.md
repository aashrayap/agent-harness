# Verdict contract

Report the claim, the commit, each layer's result with its observed check, and
the evidence limits. Use a longer report only when the risk or requested
handoff needs it.

- PASS: an adequate observable check established the named claim.
- FAIL: an observed result contradicts the claim or shows an introduced regression.
- BLOCKED: required evidence is unavailable or ambiguous; name the exact missing
  check/access. This is not a verdict that the behavior failed.
- SKIP: the layer does not apply, with the reason. A documentation claim can
  still pass a link/structure/content check.

`scripts/verdict.py record` writes `<state>/verdicts/<sha>.json`, where
`<state>` is `DOT_AGENT_STATE_HOME` or `~/.dot-agent/state`. It holds the sha,
claim, the four layers with status and evidence, the review findings with
severity, kind, `file:line`, outcome and any dismissal reason, the overall
verdict, the limits and, after `approve`, the owner's words. `record` and `check` refuse a tree that differs from HEAD: uncommitted
or untracked files, changes against HEAD, or files flagged assume-unchanged or
skip-worktree. Ignored files are not checked; a claim that depends on one is a
stated limit. `check --claim` exits 0 only for a PASS recorded for HEAD and
that exact claim. It exits 2 outside a git repository or on a verdict file
that is unreadable, lacks a layer status, holds a malformed finding, or whose
verdict does not follow from its layers and findings.

Do not broaden a passing check into unobserved success. Report partially covered
claims separately and preserve required outstanding checks. For meaningful
off-happy-path risk, include the probe and observed result. Deliver evidence
inline or through a usable artifact link; a bare inaccessible remote path is
not evidence the reader can inspect.
