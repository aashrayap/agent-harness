# Verification Options Menu

Pick by what the change risks and what signal each method buys. Prefer a
deterministic, re-runnable gate when one exists; use judgment for what it
cannot express. Layered gates add confidence only when their failure modes differ.

## Deterministic gates

- **Focused test / typecheck loop** — the cheapest gate: run the narrowest
  command that pins the claim. For requested TDD, observe red before green.
- **react-doctor** (React stacks) — `npx react-doctor@latest --scope
  changed`: 60+ rules, health score, reports only issues the change
  introduced. Fix in small batches, re-scan until clean; score must not
  regress. Tune false positives in `doctor.config.ts`.
- **Baseline / only-new-issues** — on noisy repos, compare against main and
  flag only new failures or new alerts; inherited breakage is context, not
  a FAIL.
- **Mutation testing** (Stryker/PIT/mutmut) — verifies the tests, not the
  code: surviving mutants prove the tests can't detect broken behavior.
  Worth it for core logic; slow, scope to changed files.
- **Property-based testing** (fast-check/Hypothesis) — assert invariants
  over generated inputs so a test cannot simply mirror the bug;
  counterexamples become durable repros.
- **Snapshot / visual regression** — byte or pixel diffs (Playwright
  snapshots, Chromatic/Percy/Argos). Good change detectors, weak
  correctness oracles; baselines churn on intentional change.
- **Contract tests** (Pact-style) — pin a cross-service interface so a
  one-sided refactor breaks deterministically without the whole system.

## Real-surface runs

- **Drive the surface** — CLI → terminal, server/API → socket, library →
  public export, agent → run the agent.
- **Browser via Playwright** — accessibility-tree snapshots + screenshots;
  walk the changed flow, assert visible text/URL/network. Signed-in and
  enterprise SSO flows: [browser verification](browser-verification.md).
- **Computer use** — for surfaces with no automation handle (desktop,
  third-party admin UIs). Slow, judgment-heavy; a spot-check, not a gate.
- **Probe** — one off-happy-path run per behavioral change: wrong input,
  repeat with stale state, the adjacent error path. Pick the probe the
  diff points at.

## Judgment and CI

- **Adversarial refutation** — ask the L4 reviewer to *disprove* the
  change (exploit, counterexample, missed requirement); convert any confirmed
  refutation into a failing test.
- **Babysit CI to green** — after pushing, watch checks, fix, re-run; cap
  retries so a flaky test can't run the loop away.
- **PR-gate reviewer** — advisory model review on the PR; never the sole gate.

## Choosing

Ask: what does this change risk, and which option would catch that
failure? A parser wants property tests; a checkout flow wants a browser
run; a refactor wants the existing suite plus mutation on the touched
core; a security-sensitive diff wants adversarial refutation on top of
gates. Prefer the option that leaves a re-runnable check behind.
