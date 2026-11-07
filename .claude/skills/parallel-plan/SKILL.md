---
name: parallel-plan
description: Plan useful parallel work in chat with a rendered flow diagram (or labeled tree) and a complementary lane table, exact proposed settings, dependencies and verification.
disable-model-invocation: true
---

# Parallel Plan

This skill is plan-only: read enough context to make a useful plan, but do not
start agents or processes, edit the target project, or execute proposed work.

1. Establish the outcome, deliverable, constraints and non-goals.
2. Find useful independent work. Keep parent decisions and shared files explicit.
   If no useful parallelism exists, show an honest sequential parent-owned plan;
   never invent agents to fill the format.
3. Read the central runtime model policy linked from AGENTS.md and check the
   available dispatch surface. Label every planned lane with role, exact model
   target and reasoning effort. If settings are unresolved, say
   `unresolved — identity check required`; never guess or silently substitute.
   Planned settings are not observed runtime evidence.
4. Name every lane in plain words for the work it does, such as "Write the
   conformance check" or "Review the diff". Never a letter or code name (Lane A,
   W1, L2, Track B): the same plain name appears in the diagram node and the
   table row, so the owner reads either one without a key.
5. Default to two complementary in-chat visuals:
   - A diagram showing the exact launch sequence, concurrent waves,
     dependencies/waits, parent reconciliation and risk-appropriate
     verification: a rendered inline diagram where the client supports it
     (show_widget in the Claude desktop app), otherwise a labeled text tree.
   - A compact lane table, one row per lane, adding its bounded work, model,
     effort, isolated write scope/exclusions, returned evidence and handoff.
   Explain the launch order in plain language. For a sequential plan the table
   describes the parent stages and their settings without inventing workers.
6. Check dependency consistency, legibility and ownership. State the first
   authorized next action and any actual unresolved decisions, then stop.

Example lane table:

| Lane | Work | Model, effort | Writes | Returns |
|---|---|---|---|---|
| Write the conformance check | move it into template/ and run it from scripts/check | claude-opus-5-5, high | template/, scripts/check | check output |
| Review the diff | read the finished branch cold | claude-sonnet-5-5, medium | nothing | findings |

Visual owns richer presentation/rendering. Use it for durable or richer output
when requested or useful; ordinary plans need no HTML artifact, browser session
or separate file.
