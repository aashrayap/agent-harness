# Blast Radius

Use this Verify procedure when asked what a change could break, when the diff
crosses an ownership boundary, or when safety depends on behavior outside the
changed path.

The goal is not a long caller list. Find the one or two safety facts that make
the change safe, trace the breakage that search alone misses, and exercise
those facts with real code.

## Procedure

1. **Scope the change.** Record every changed path, symbol, data shape,
   configuration value, feature flag, migration, and rollback path. State what
   now behaves differently, including effects the diff does not spell out.
2. **Walk the dependency graph.** Inspect direct callers, transitive consumer
   code, pinned library source and patches, lifecycle or timing behavior,
   stored data, wire formats, generated artifacts, and another runtime or
   language that reads the same bytes. Search results are leads, not proof.
3. **Name the safety fact.** Reduce the risk to the smallest factual claim on
   which safety depends. Cite the owning source and walk the failure case far
   enough to show where it reaches or stops.
4. **Separate risk from clearance.** For each plausible break, record the
   affected consumer, likelihood, cost, evidence, and cheapest check. Keep
   confirmed risks apart from cases inspected and cleared.
5. **Build and run the verification matrix.** One row per safety fact or real
   risk: dependency or consumer, failure mode, deterministic gate, real-surface
   probe, observed evidence, and verdict. Prefer a script or focused test that
   imports the code or pinned dependency the product actually ships.
6. **Finish truthfully.** Mark a fact proven only when the test or running
   surface exercised it. Otherwise report the highest confidence level reached
   and label it unproven. Include the cheapest merge-time regression check.

## Confidence ladder

1. Assertion only.
2. Owning source cited.
3. Failure path walked and shown to stop.
4. Real script or test executed.
5. Running product reproduced.

A PASS requires level 4 for every central safety fact unless the user accepts
a narrower claim. Anything lower is BLOCKED or FAIL under Verify's verdict
contract; do not round it up.

Report each step's result in order, ending with the PASS/FAIL/BLOCKED verdict,
the cheapest pre-merge check, and remaining rollback or migration limits.
