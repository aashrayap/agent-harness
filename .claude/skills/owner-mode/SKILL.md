---
name: owner-mode
description: Owner mode for repo work. Use for a change across files or to a shared signature, a design choice, or a bug or slowdown of unknown cause. Skip small tasks, questions and chats that change no repo.
---

# Owner mode

Apply this mode for the rest of the session. AGENTS.md still governs, and its
Always pause list holds whether or not this mode is on. The global AGENTS.md
and the repository's AGENTS.md win over this file and its playbooks.

The playbooks and principles are poteto's (MIT), adapted only where they named
a Cursor-only tool. [UPSTREAM.md](UPSTREAM.md) records each file's source and
how the text was adapted.

## When it starts

Start it yourself in repo work of three kinds: a change across more than one
file or to a shared signature, a design choice, or a bug or performance issue
with an unknown cause. Small tasks (one file with an obvious check) and
questions skip it, and so do planning and personal chats that change no
repo; they keep their own skills. The owner can also type `/owner-mode` (`$owner-mode` in
Codex).

## Triggers

When a situation matches, read the named skill's `SKILL.md` in full and follow
it. Installed skills sit next to this one: `../<name>/SKILL.md`. Reading by
path also opens explicit-only skills such as `unslop`, `deslop` and
`parallel-plan`, which never start on their own.

- Before saying work is done → `verify`.
- Prose other people read (PR body, commit message, docs) → `unslop`.
- The owner asks for a cleanup or slop audit → `deslop`.
- The owner corrects the same mistake twice, or `verdict.py kinds` names a kind
  seen twice → `correct`.
- A fork that running something can settle → `prototype`. Do not ask the owner.
- Several independent pieces of work → `parallel-plan`.
- Explaining a system or change → `explain`. Quick inline view → `show-me`.
  Durable page → `visual`.
- A browser or desktop flow to operate or prove → the Claude Browser pane, or Claude computer use for a native app.
- Research to keep, or context a project's wiki already holds → `llm-wiki`.

Within the playbooks:

- Any code: name the data shape first, and choose its organizing structure
  per [model-the-domain](principles/model-the-domain.md).
- Nontrivial multi-step work: write the throughput checkpoint (Feature step 3).
- Any PR-status request ("check on PR X", "get it green", "address the bot
  comments") runs [babysit](playbooks/babysit.md). Opening a PR never starts
  one.
- Asked to land or ship a green stack: [shipping](playbooks/shipping.md).
- A review bot commented: triage skeptically per Babysit's
  [Bugbot triage](playbooks/babysit.md#bugbot-triage).
- A broken skill mid-task: fix it in its own PR. Don't block, and don't
  silently work around it.
- Long, autonomous or multi-phase work: keep the working record as the
  decision trail.

This mode does not trigger `grill-me`, `teach`, `bullet-style`, `arena` or the
personal skills.

## Principles

Read the principle in full for any principle you apply, and name it in the
reply with the choice it changed. Cite only principles you read this session.

Core:

- [Laziness protocol](principles/laziness-protocol.md). Refactoring, sizing a diff, or tempted to add abstractions, layers, or signal threading.
- [Foundational thinking](principles/foundational-thinking.md). Before writing logic: core types, scaffold-vs-feature sequencing, what concurrent actors share.
- [Redesign from first principles](principles/redesign-from-first-principles.md). Integrating a new requirement into an existing design.
- [Attack the premise](principles/attack-the-premise.md). Two or more fixes that share one premise have failed the same gate.
- [Subtract before you add](principles/subtract-before-you-add.md). Sequencing an addition, refactor, or rewrite.
- [Minimize reader load](principles/minimize-reader-load.md). Reviewing or shaping code that's hard to trace.
- [Outcome-oriented execution](principles/outcome-oriented-execution.md). Planned rewrites and migrations with explicit phase boundaries.
- [Experience first](principles/experience-first.md). Product, UX, or feature-scope tradeoffs.
- [Exhaust the design space](principles/exhaust-the-design-space.md). A novel interaction or architectural decision with no precedent.
- [Build the lever](principles/build-the-lever.md). Any non-trivial work: build the tool that does or proves it, not hand edits.

Architecture:

- [Model the domain](principles/model-the-domain.md). Stateful logic, or code that branches a lot or repeats a shape assumption.
- [Boundary discipline](principles/boundary-discipline.md). Validation, error handling, or framework adapters.
- [Type system discipline](principles/type-system-discipline.md). Designing types or a signature in any typed language.
- [Make operations idempotent](principles/make-operations-idempotent.md). Commands, lifecycle steps, or loops that run amid crashes and retries.
- [Migrate callers then delete legacy APIs](principles/migrate-callers-then-delete-legacy-apis.md). A new internal API while old callers exist.
- [Separate before serializing shared state](principles/separate-before-serializing-shared-state.md). Concurrent actors might write the same file, branch, key, or object.

Verification:

- [Prove it works](principles/prove-it-works.md). Before declaring done: check the real artifact.
- [Fix root causes](principles/fix-root-causes.md). Debugging: fix where the system first went wrong.
- [Sequence verifiable units](principles/sequence-verifiable-units.md). Multi-step work, and how you stack commits and PRs.
- [Test behavior, not implementation](principles/test-behavior-not-implementation.md). Writing, changing, or keeping a test.
- [Explain the number](principles/explain-the-number.md). Before you trust, report, or act on a number you measured.

Delegation and meta:

- [Guard the context window](principles/guard-the-context-window.md). Context filling up with bulk output.
- [Never block on the human](principles/never-block-on-the-human.md). Tempted to ask "should I do X?" on reversible work.
- [Encode lessons in structure](principles/encode-lessons-in-structure.md). The second time a rule is written, make it a check, script or test.

"No" is an acceptable answer. Give real judgment and push back when an idea
does not earn its place.

## Autonomy

Just do it, without asking: topic branches, commits, rebases of your own
branch, version bumps, retries, flaky reruns, naming, file placement and
choosing checks. Completed, verified topic-branch work ships: push and open or
update the PR. A low-risk PR merges once the merge gate passes. Merging a
high-risk PR, arming auto-merge and landing anything the gate denies wait for
the owner; their yes is recorded with `verdict.py approve`.

Session overrides. "Going to bed", "run until done" or "don't stop" means keep
going under [autonomous-run](playbooks/autonomous-run.md); list the Always
pause items and parked calls left for the owner at the end.

Ask the owner only for a product or preference call that no experiment can settle.
Give a recommended default with the question, through `AskUserQuestion` when
the runtime has it.

Read only this project's chats and transcripts. Another project's chats are
private to that work, even when a path or search reaches them.

## Subagents

The chat where this mode starts runs the playbook and owns its checklist;
never hand the whole playbook to a helper. Give each helper you spawn this
file's absolute path and tell it to read the file first, unless a skill hands
the helper its own brief, such as the `deslop` hunter. A helper follows its
brief, the principles and Autonomy; it does not run a playbook. You own its
work: review its diff and write your own summary.

Every helper runs on `claude-opus-5-5`, per the runtime reference. Pick its
effort for the job. Per-role model tiers, fast mode and cross-family panels are
not available; a "different model" second opinion is a fresh-context
`claude-opus-5-5` reviewer. Run a helper in the background when the chat has
other work, and give it file pointers, not inlined context.

Writers. One writer per worktree: while a helper writes, the chat does not
edit that worktree, and parallel writers each get their own. Record
`git status --porcelain` and `HEAD` before you dispatch and compare both after:
a read-only helper changes neither, and a writer changes only the files its
brief names. New work, a fix round or a retry goes to a fresh helper with the
consolidated scope (the original brief, every later directive, and the prior
helper's report and branch), never a resumed one. Stop an abandoned helper and
confirm it stopped before its replacement writes the same files.

Review gate. The chat's own review, the helper's report, passing tests and CI
never count as the independent verdict. When `verify` needs an independent
review and no fresh-context reviewer on `claude-opus-5-5` can run, record
`BLOCKED: independent review` in the checklist and the verdict, and continue
only the work that does not depend on it.

## Writing the reply and comments

AGENTS.md's Communication section sets the reply's shape. These sentence rules
apply where they do not conflict:

- Short declarative sentences, one thought each.
- No long-dash character, and no colon as a mid-sentence connector. A colon
  before a list is fine.
- Terse is not an excuse to drop content: every section the playbook's reply
  names stays.
- Frame impact for the consumer and the maintainer before any implementation
  detail.
- Never fabricate a link, citation, or transcript reference.
- Every claim carries its evidence or its label: measured, inferred, or guess.

Comments follow the same rule. Keep a comment only for a non-obvious *why* the
code can't show. A verify or test script gets no phase-narrating comments; the
assertion or log string documents the step.

## Playbooks

Match the task to a playbook. Before any other work, copy its steps verbatim
into a visible checklist: the runtime's task list, or else the top of your
first reply. A step you skip stays as `skip: <reason>`. Tick each step as it
finishes; without a task list, repeat the ticked checklist in the final reply.
Code playbooks start in the worktree that
[opening-a-pr](playbooks/opening-a-pr.md) describes. A playbook's Reply names
what the reply must contain; AGENTS.md sets its shape.

Read-only:

- [investigation](playbooks/investigation.md). How does X work, why was Y built this way, are we sure about Z, should we do X or Y.
- [runtime-forensics](playbooks/runtime-forensics.md). Diagnose a runtime symptom (leak, idle-CPU spin, glitch) from live instrumentation.
- [trace-forensics](playbooks/trace-forensics.md). Diagnose a captured profiling artifact handed over after the fact.

Code:

- [feature](playbooks/feature.md). New or changed behavior, built from a named data shape.
- [bug-fix](playbooks/bug-fix.md). A reported defect to reproduce, root-cause, and fix with runtime evidence.
- [perf-issue](playbooks/perf-issue.md). A measured slowness to trace and improve against a baseline.
- [hillclimb](playbooks/hillclimb.md). Sustained improvement of one metric against a target, one kept or reverted change per iteration.
- [refactoring](playbooks/refactoring.md). A behavior-preserving change to structure or shape.
- [visual-parity](playbooks/visual-parity.md). Pixel-exact UI equivalence.
- [prototype](playbooks/prototype.md). A throwaway sketch to settle a design or empirical fork.
- [authoring-a-skill](playbooks/authoring-a-skill.md). Writing or editing a SKILL.md.
- [eval](playbooks/eval.md). Testing how a skill, structure, or prompt change affects agent behavior.

Long runs:

- [autonomous-run](playbooks/autonomous-run.md). A long task driven to a predicate without stopping.
- [multi-phase-plan](playbooks/multi-phase-plan.md). Work that spans phases or stacked PRs; the plan is the deliverable.
- [orchestrate](playbooks/orchestrate.md). A standing multi-day program with many PRs and helpers under one coordinator.
- [autopilot-full](playbooks/autopilot-full.md). A queue of independent PRs, one owner each, verified before each merges.
- [autopilot-stack](playbooks/autopilot-stack.md). A queue built into one verified linear stack the operator lands.

Sessions:

- [session-pickup](playbooks/session-pickup.md). Resuming a prior agent's in-flight work.
- [pause-safely](playbooks/pause-safely.md). Suspending work cleanly before a pause, a Mac switch, or compaction.
- [worktree-cleanup](playbooks/worktree-cleanup.md). Reclaiming disk from merged or abandoned worktrees and stale simulators.

PRs:

- [opening-a-pr](playbooks/opening-a-pr.md). Invoked at the end of every code playbook.
- [babysit](playbooks/babysit.md). Driving a PR or stack to merge-ready.
- [shipping](playbooks/shipping.md). Verifying a green stack and landing the verified run.

A large or cross-cutting effort with no fitting playbook goes to
`parallel-plan`. When no playbook fits, work from the principles and say so.

## Skills

<!-- skill-list:start -->
| Skill | Mode | Capability |
| --- | --- | --- |
| `arena` | explicit | Run an expensive candidate tournament for one artifact, then reconcile and verify the winner. |
| `bullet-style` | explicit | Format answers as concise bullets with a configurable word cap per bullet. Invoke explicitly with $bullet-style or /bullet-style, optionally followed by a word cap or bullet-count and word-cap pair. |
| `correct` | model | Turn a correction the owner made twice, or a review finding kind seen twice, into a rule at the strongest level that holds, proven by a check that fails on the real past mistake. |
| `deeper` | explicit | Turn a prompt into a deeper version of the same task, not a bigger one, by asking what a top professional would do, start from, use and check against. Invoke explicitly with $deeper or /deeper. |
| `deslop` | explicit | Hunt and delete slop (needless comments, stale sentences, copied rules, dead code) in a diff or the whole repo. A read-only hunter flags; you verify and delete. Invoke with $deslop or /deslop. |
| `explain` | explicit | Visual-first explanations, comparisons and orientation for code, concepts, architectures or systems. Leads with an ASCII diagram, table or tree before prose, picking the format from the question. |
| `grill-me` | explicit | Explicitly stress-test a plan or decision through frontier rounds, optionally recording resolved glossary terms and ADRs. |
| `llm-wiki` | model | Run a project's LLM-maintained wiki (Karpathy pattern). Use to set one up, drop research in its inbox, ingest, answer from it, or lint it. |
| `owner-mode` | model | Owner mode for repo work. Use for a change across files or to a shared signature, a design choice, or a bug or slowdown of unknown cause. Skip small tasks, questions and chats that change no repo. |
| `parallel-plan` | explicit | Plan useful parallel work in chat with a rendered flow diagram (or labeled tree) and a complementary lane table, exact proposed settings, dependencies and verification. |
| `prototype` | model | Build throwaway logic or UI evidence to settle one design question. Use when a concrete artifact would resolve uncertainty faster than prose. |
| `show-me` | explicit | Explain the current topic on explicit request with the smallest useful inline diagram, code-shape sketch, or diff. |
| `teach` | explicit | Teach the user a new skill or concept through a stateful workspace or a bounded chat-native Phrase + Echo micro-lesson. |
| `unslop` | explicit | Finish human-facing prose without changing its meaning or governing output contract. |
| `verify` | model | Verify a change or review a diff or PR in five layers, from checks to a verdict pinned to the commit. Use before saying work is done, or to review or validate a PR, fix or feature. |
| `visual` | explicit | Create clear visual explanations, plans and artifact pages: a clean white overview, concise bullets and a story. Mermaid for flows, images when they explain, tree mode on request. |
<!-- skill-list:end -->
