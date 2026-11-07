---
name: prototype
description: Build throwaway logic or UI evidence to settle one design question. Use when a concrete artifact would resolve uncertainty faster than prose.
---

# Prototype

Build one disposable artifact for one named question. Read the relevant guide:

- Logic/state behavior: [LOGIC.md](references/LOGIC.md)
- UI shape: [UI.md](references/UI.md)

Keep it trivial to run, memory-only by default, visibly marked prototype, and
unpolished. Let the question determine the number of variants. The parent agent
evaluates technical evidence; the owner decides product preferences and consequential
tradeoffs. Record the question, evidence and verdict in the existing working
record. Preserve the prototype as primary-source evidence on an unmerged
`prototype/<name>` branch; main keeps only the validated decision.

Adapted from Matt Pocock's skills; see [UPSTREAM.md](references/UPSTREAM.md).
