---
name: correct
description: Turn a correction the owner made twice, or a review finding kind seen twice, into a rule at the strongest level that holds, proven by a check that fails on the real past mistake.
---

# Correct

A correction that recurs is a missing rule. The instruction is the symptom;
the rule belongs in structure. Adapted from poteto's `/correct` and his
encode-lessons-in-structure principle (MIT, pstack); ours keeps the rule table
in the repo's `CONSTRAINTS.tsv`.

## When

- The owner corrects the same mistake a second time, in any chat.
- `verdict.py kinds` names a finding kind seen twice.

One-off mistakes get fixed, not ruled.

## Steps

1. Name the mistake in one line and find each past instance: the chats, the
   commit, the PR or the verdict finding. Use its words, not a paraphrase.
   Never copy message text into a repo.
2. Name the cause: missing context, unmapped case, bad data or agent wrong.
   Missing context and bad data are fixed in the doc or the input; an
   unmapped case wants a check; agent wrong wants a rule the agent cannot skip.
3. Pick the home on the ladder, highest first, and say why each higher one
   does not work:
   - `impossible`: setup, a lock or the architecture makes the mistake
     unwritable.
   - `check`: a lint or script in `scripts/check` whose error names the fix.
   - `test`: a unit test that pins the behavior.
   - `hook`: a Claude Code hook that denies, asks or blocks at the moment of
     the act.
   - `prose`: a sentence in AGENTS.md or a skill, guarded by
     `check-constraints.py`. Only for judgment no code can see.
   - `memory`: a note for one Mac; last resort.
4. Search `CONSTRAINTS.tsv` first. If the rule is there at a lower level, the
   mistake is a repeat: raise that row, same `id`. If it is there at the right
   level, its enforcer has a hole: fix the enforcer.
5. Reconstruct the past mistake as a fixture (the old file at its commit, the
   command, the transcript turn) and write the proof test first. Run it
   against the code before your fix and watch it fail; then fix and watch it
   pass. A rule whose proof never failed proves nothing.
6. Add or edit the row: `id`, `rule`, `level`, `enforcer` (`path` or
   `path::name`), `proof` (the test names, then the past mistake it fails
   on), `notes` (what it does not cover). Kept prose rows say in `notes` why
   no higher level works.
7. Run `scripts/check --tests`, then ship through the verify skill like any
   change. Rules about AGENTS.md, hooks or CONSTRAINTS.tsv are high risk.

## Report

One line per rule: the mistake, the level and why not higher, the proof and
the past mistake it fails on. Give the CONSTRAINTS.tsv level counts before and
after.
