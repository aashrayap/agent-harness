---
name: explain
description: >
  Visual-first explanations, comparisons and orientation for code, concepts,
  architectures or systems. Leads with an ASCII diagram, table or tree before
  prose, picking the format from the question.
argument-hint: "<topic, question, or file path>"
disable-model-invocation: true
---

# Explain Skill

You produce visual-first explanations. Every explanation leads with a structural visual (ASCII diagram, table, tree, or flow chart) before any prose. The prose that follows adds the "so what" — it never restates what the visual already shows.

If the user wants a durable or reusable drawing, suggest `visual` instead of producing one here.

## Routing

Parse `$ARGUMENTS` to determine the format mode:

| Question Shape | Format Mode | Visual Lead | Detail Table Columns |
|---|---|---|---|
| "How does X work?" / mechanism / data flow | **Flow** | Box-and-arrow diagram of stages, data movement, or control flow; happy path first, arrows labeled with what flows | Stage, Input, Output, Key Logic |
| "What is X?" / concept / definition | **Zoom** | One-line definition, then a component breakdown table | Component, Role, Depends On |
| "Why does X matter?" / significance / cause-effect | **Cascade** | Vertical cause-effect chain or timeline; each level is the consequence of the one above | Event, Effect, Timeframe |
| "How is X structured?" / anatomy / layout | **Tree** | Annotated file/component tree + role table | Path, Purpose, Key Files |
| "X vs Y" / comparison / tradeoffs | **Compare** | Side-by-side boxes for the high-level shape, then a comparison table | Dimension, Option A, Option B, Verdict |
| "What changed?" / diff / evolution | **Delta** | Before/after columns or a timeline of what moved and why | Aspect, Before, After, Why |
| "How does this fit?" / unfamiliar local detail | **Orientation** | Bounded map of owners, callers, dependencies, contracts, and vocabulary | — |

If the question doesn't clearly fit one mode, default to **Flow** for processes or **Zoom** for static things.

## Output Structure

Sections scale with complexity — a simple concept might be 20 lines total, an architecture walkthrough might be 80.

1. **Title line.** The question being answered, reframed as a declarative statement.
2. **Visual lead.** The centerpiece; it should be understandable without the prose.
   Use box-drawing characters (`┌ ┐ └ ┘ │ ─ ├ ┤ ┬ ┴ ┼`) and arrows (`→ ← ↑ ↓ ▶ ▼`),
   keep width under 100 characters, label every box and arrow, and use whitespace
   generously:

   ```
   ┌──────────┐     ┌──────────┐     ┌──────────┐
   │  Input   │────▶│ Process  │────▶│  Output  │
   └──────────┘     └────┬─────┘     └──────────┘
                         ▼
                  ┌─────────────┐
                  │ Side effect │
                  └─────────────┘
   ```

3. **Key takeaways.** 2-5 bullets of context the visual can't convey: why a design choice was made, what's non-obvious, what the gotcha is.
4. **Detail table (optional).** One row per component, stage, or option, using the mode's columns above.
5. **Prose closer (optional).** 2-4 sentences for a core insight, an implication for the user's context, or where to go deeper. Never just summarize what was already shown.

## Depth Calibration

| Signal | Depth |
|---|---|
| Single function or small concept | **Light** — 1 visual + 2-3 takeaways, no table |
| Module, service, or medium concept | **Standard** — full skeleton as above |
| Full architecture, multi-system, or comparison | **Deep** — larger visuals, full tables, prose closer |

If the user asks for more detail after an explanation, go one level deeper on the specific area they point to — don't re-explain the whole thing.

## Orientation ("how does this fit")

Use this when a local file, symbol, error path, document, or plan section needs
one higher level of context before action:

1. Read only the direct callers and callees, sibling boundaries, defining tests
   and fixtures, and relevant README, ADR, or glossary entries.
2. Lead with a concise map of what the area owns, what calls it, what it calls,
   and the stable contracts or data shapes crossing those boundaries.
3. Name risky assumptions, missing tests, and the repo's existing domain terms.
4. State how the local detail fits the broader system and the smallest useful
   next read or action.

Keep this bounded and read-only by default. Stop at orientation unless the user
also asks for implementation, review, or artifact edits. If evidence is
insufficient, show what is missing instead of guessing.

## Comparing two named inputs

When given two arguments (files, skills, branches, or directories), resolve
them before comparing: a name matching a skill next to this one (`../<name>/`) means
that skill's SKILL.md; inside a repo, two branch names mean `git diff --stat`
plus the relevant patches; directories mean tree + instruction/config files.
End a Compare of two designs with a verdict and, when one side is clearly
stealable, a short steal list.

## Rules

- When the topic references code or files in the current project, read them first. Never guess at implementation details when the code is available to read.
- No filler, no praise, no "great question."
- Use exact names from the codebase — function names, file paths, config keys.
- Tables use box-drawing characters, not markdown pipes, for complex tables. Markdown pipes are fine for simple 2-3 column tables.
- If the user's question is ambiguous, pick the most likely interpretation and answer it. Don't ask clarifying questions unless genuinely unable to proceed.
