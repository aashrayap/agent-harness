---
name: grill-me
description: Explicitly stress-test a plan or decision through frontier rounds, optionally recording resolved glossary terms and ADRs.
disable-model-invocation: true
---

# Grill Me

Use this optional interview when explicitly requested. It does not intercept
ordinary implementation requests. Resolve what source and prior decisions
already answer before asking the owner.

## Mode

- Use **docs mode** only when an explicit invocation's first argument is
  `docs`; consume that word. Every other explicit invocation uses **plain mode**.
- Before the first question, state the mode, the plan or design being tested,
  and any declared docs targets. Docs mode may update only `GLOSSARY.md`,
  `GLOSSARY-MAP.md`, and `docs/adr/*.md` (or their existing repo-local
  equivalents).
- When `GLOSSARY-MAP.md` declares multiple contexts, route a context-specific
  ADR to that context's local `docs/adr/`; reserve root `docs/adr/` for
  system-wide decisions.

## Interview loop

1. Read repo evidence that can answer a question without asking the user.
2. Map the subject as a design tree. Choose every unresolved decision whose
   prerequisites are settled; unanswered prerequisites hold only their
   dependent questions.
3. In plain mode, ask the whole independent frontier as one numbered round. In
   docs mode, batch independent questions when that reduces interruption, then
   record each accepted decision in its declared target. Give recommended answers and main tradeoffs. Ask through
   the supported runtime question tool when appropriate, plain text otherwise.
4. Wait for the user's answer. Do not ask a dependent question in the same
   round.
5. Reconcile the answer with earlier decisions and code. Surface conflicts
   instead of silently resolving them, recompute the frontier, and repeat until
   no meaningful branch remains silently assumed. Decisions remain the user's.
6. In docs mode, record a resolved decision immediately, but only in the
   declared targets:
   - sharpen vague or overloaded terms and update the appropriate glossary;
   - use project vocabulary and challenge conflicts with existing definitions;
   - test boundaries with concrete scenarios and cross-check claims in code;
   - offer an ADR only for a hard-to-reverse, surprising, real tradeoff.
   Read [GLOSSARY-FORMAT.md](references/GLOSSARY-FORMAT.md) before a glossary
   edit and [ADR-FORMAT.md](references/ADR-FORMAT.md) before an ADR.
7. When meaningful branches resolve, summarize the agreed decisions and
   remaining risks. Do not add a final confirmation ritual when the owner has
   already answered.

## Boundaries

- An explicit interview-only request never implements the plan.
- If implementation was already authorized in the same workflow, return to it
  after resolving actual decisions; no separate request is required.
- Do not mutate application code, tests, configuration, or undeclared docs.
- Create glossary or ADR files lazily, only after a term or decision resolves.
- Keep `GLOSSARY.md` to domain language, not implementation details or a spec.

The unified plain and docs modes adapt Matt Pocock's pinned interview skills;
see [UPSTREAM.md](references/UPSTREAM.md).
