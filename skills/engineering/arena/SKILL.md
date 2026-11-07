---
name: arena
description: Run an expensive candidate tournament for one artifact, then reconcile and verify the winner.
disable-model-invocation: true
---

# Arena

Arena is an explicit, expensive candidate tournament. Use it only for `$arena`
or `/arena`, and only when materially different attempts could beat one
ordinary implementation.

It is not `parallel-plan` (plan-only), `verify` (judges a frozen commit), or
ordinary implementation (one solution owner may still use bounded research,
support, and review lanes). Arena creates several full candidates, selects a
base, grafts the best compatible parts, and subjects the synthesis to real
verification.

## Frame

Define one artifact and 3-6 concrete criteria. Give every candidate the same
task and grounding. Set the candidate count before dispatch; default to three
and require explicit user approval above three. Set a per-lane time or cost
limit.

Stop before fan-out if the task has one obvious implementation, the criteria
cannot distinguish candidates, cost or time is not bounded, required sources
or licenses are unresolved, or isolated write locations are unavailable.

## Fan out

Launch candidates concurrently. Concurrent writers require isolated git
worktrees; non-repository artifacts require separate temporary directories.
Each candidate returns its artifact, rationale, considered alternatives, and
verification evidence. Never let candidates write shared mutable state.
The parent monitors every lane against its declared limit. Interrupt a lane
when it reaches the limit, record it as a dropout, and do not replace it with an
unbudgeted candidate.

Use the central model/effort policy in the runtime reference linked from
AGENTS.md.
Check the actual dispatch surface; never substitute an unavailable model silently.

Require at least two complete candidates. Record dropouts. If only one
candidate finishes, return BLOCKED with that candidate and the dropout reasons
as evidence; do not synthesize. Stop immediately if any writer escapes its
isolation.

## Judge and reconcile

After all writers stop, dispatch one read-only cross-judge on a permitted model
when a slot and budget remain. In parallel, the parent reads every candidate
end to end and scores each criterion. The cross-judge is evidence, never the
decision owner.

Parent reconciliation selects the smallest coherent base, records the reason,
then manually grafts only compatible strengths from losing candidates. Record
the base, grafts, rejections, disagreements, and dropouts in a synthesis note.
Never paste candidates together mechanically.

If candidates diverge because the frame was ambiguous, reframe once. If a
second tournament still has no defensible base, stop and return the unresolved
criteria instead of averaging the candidates.

## Verify and stop

Run `verify` against the synthesized artifact at the real surface, including a
focused deterministic gate and an off-happy-path probe when behavior changed.
Arena does not weaken normal review, ownership, or shipping gates.

Stop with FAIL when real verification fails. One repair-and-reverify cycle is
allowed when the fix stays inside the chosen design; otherwise return the
failure and the candidate evidence. These stopping conditions cap cost and
prevent tournament churn.

Arena is complete only with one synthesized artifact, one synthesis note, and
a PASS/FAIL/BLOCKED verification verdict.
