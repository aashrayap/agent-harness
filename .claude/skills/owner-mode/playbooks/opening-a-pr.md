### Opening a PR

Invoked at the end of every other playbook.

**Worktree.** Work from a git worktree off the base branch, on a branch named `agent/<short-topic>` unless the repository or the task names the branch. Subagents inherit it. Multiple subagents on the same branch each get their own worktree, or `git fetch && git reset --hard origin/<branch>` between them. Dirty branch with unrelated work: patch out, fresh worktree, apply. Snarled worktree: reset from the base branch, redo minimally.

**Commits.** Commit liberally. Rebase into small, ordered commits before opening PRs. Each commit is a future PR: landable, ordered to tell the story. Amend when the fix belongs in a just-made commit. New commit when separable. Commit bodies don't restate the subject. A VERSION bump adds its `RELEASES.md` entry where the repository has one.

**PRs.** Run `deslop` over the diff before commit, and the no-comments check before review (`scripts/no-comments.py` in dot-agent, the repository's own linter elsewhere). Write every PR title, description, and commit body plainly (one word per action, keep articles, a plain verb over `-ing` where one works), then apply `unslop`.

**Verdict.** Before opening, `verify` has recorded a verdict for HEAD and `verdict.py check --claim` shows it. PASS opens. BLOCKED opens only when `## Verification` lists its open BLOCKING findings or the blocked layer and why; merging needs PASS. Write the body to a file first and run `verdict.py check --claim "<claim>" --body <file>`: it exits 0 only when the PR may open.

**Titles.** The repository's existing title style. Conventional Commits `type(scope): subject` only where the repository already uses them. No trailing period. The subject is short, imperative, and names a real symbol when one carries the change.

**Descriptions.** The PR body is a one-minute briefing, not a lab notebook, for a reviewer who has the diff. It says why the change exists, what it leaves out, what it could break, and how you proved it works. Write short, simple sentences with few identifiers, no walls of text. The body becomes the squash commit body, so keep that commit under about 40 lines. Use `##` headings, not bold lead-ins, in this order, and drop a section with nothing to say:

- `## Why`: the problem and approach, 1–3 short sentences. No SHAs, rebase genealogy, or "based on main" preamble.
- `## What changed`: 1–3 short bullets. Name a real symbol or path only when it carries the change. Name both sides of a rename or retarget.
- `## Scope`: always. 1–3 short items on what it covers and what it deliberately leaves out (a follow-up, a known gap). No symbols, paths, or file-by-file essay.
- `## Tradeoffs`: only rejected alternatives a reviewer would otherwise ask about. Skip when there was no real choice.
- `## Blast radius`: always opens with the line `verdict.py risk` prints, `Risk: low` or `Risk: high (<reasons>)`. Then 1–2 sentences on who or what it touches and why that is safe or risky. If main is red, state the cost of leaving it red.
- `## Verification`: 1–3 bullets, each a real run path and its outcome. Perf: one primary number with its unit, `before → after`, and a link to the run directory for the rest. No sample-size methodology, lane recitals, or metric tables.

After the sections, attach videos or screenshots when they prove a claim. Full SHAs, lane recitals, lever-correction essays, file-by-file checklists, and "CLEAN" verdicts go in a linked artifact, not the body.

**Forge.** `gh` only, for create, edit, view, watch, and merge.

**Built-in PR tool.** When the run provides a built-in PR tool, create, edit, retarget, and mark ready through it, never through `gh`. A CLI-made PR misses what the tool tracks. Use `gh` for everything the tool does not cover, and for every PR operation when the run has no such tool.

**Size and stacks.** Prefer five narrow PRs to one large PR. A stack is a base-branch chain. The root PR targets trunk. Each child branch rebases onto its parent's exact tip and its PR targets the parent branch. As a parent merges, move its child onto trunk per [shipping](shipping.md) step 4. Without a built-in PR tool, create a child with `gh pr create --base <parent-branch>`, and retarget one with `gh pr edit <pr> --base <parent-branch>`. Branch from trunk only for independent work. Rebase on trunk before substantial stack work.

**Readiness.** Open every PR ready, never as a draft. A built-in PR tool can default to draft, so set `draft: false` on every creation call through it. With `gh`, omit `--draft`. If a PR still opens as a draft, mark it ready through the PR tool, or run `gh pr ready <number>`. Run `gh pr view <number>` before you refer to PR status.

**Babysit.** Opening a PR does not start a babysit. Post the URL and keep building. Finish the phase or stack first. Run a separate babysit pass only when the user asks for one after the whole stack exists. A babysit for each new PR stalls the build and spends checks on commits later waves restart. Push back when feedback drifts from intent.

A subagent that opens a PR runs `deslop` and the no-comments check, and posts the URL. It returns to the parent without babysitting, unless it is an Autopilot-full or Autopilot-stack owner. That owner's brief assigns the babysit loop and is the ask [babysit](babysit.md) waits for. The owner starts the loop after its code-ready report, reports merge-ready or STACK-READY per its playbook, and is exempt from the rules here and in [babysit](babysit.md) that hold babysitting until a whole stack is built.

**Merge.** A low-risk PR merges once the merge gate passes: green CI, PASS for the exact head, no open BLOCKING finding. A high-risk PR waits for the owner's yes, recorded with `verdict.py approve` before the merge command.
