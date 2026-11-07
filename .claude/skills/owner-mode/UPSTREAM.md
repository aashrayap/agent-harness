# Upstream provenance

owner-mode's playbooks and principles are poteto's (Lauren Tan) `poteto-mode`
playbooks and `principle-*` skills from
[`cursor/plugins`](https://github.com/cursor/plugins) under `pstack/`, MIT,
pinned at
<https://github.com/cursor/plugins/tree/99743e9c151c8537cbbf1f98bb38f34ef3368453/pstack>.
A few rules come from Christian Bager Bach Houmann's MIT port
[`chhoumann/t3-pstack`](https://github.com/chhoumann/t3-pstack) at
`5a8b33f83cb62d8cfd5819d6e45447a932b49084`. t3-pstack credits its
stop-an-abandoned-agent and review-gate rules to Michael Denyer's
[`pstack-claude`](https://github.com/michael-denyer/pstack-claude) (MIT), which
was read only as a reference for Cursor to Claude translations; no text is
copied from it. [LICENSE-MIT.md](LICENSE-MIT.md) is t3-pstack's `LICENSE`:
pstack's license (SHA-256
`bc957ca6bee02792566a1a028d105e02e247c6e77cf057061674273da77b200e`) with the
two port authors' notices added.

## Files

Each row names one of our files, the upstream text it came from, the commit,
and the SHA-256 of that upstream text (not of our file). A file built from
several sources has a row per source. `babysit.md` carries poteto's Bugbot
triage rubric as its last section, and `SKILL.md` carries poteto-mode's
principle and playbook index merged with the owner's rules.

<!-- upstream-files:start -->
| Local file | Repo | Upstream file | Commit | SHA-256 |
| --- | --- | --- | --- | --- |
| `SKILL.md` | `chhoumann/t3-pstack` | `plugins/pstack/hooks/session-start-context.md` | `5a8b33f83cb62d8cfd5819d6e45447a932b49084` | `bca9228e3bdaaa9922aad52f4f1ce22b18dc4da0c138ebaa56fd7b4a932dce38` |
| `SKILL.md` | `chhoumann/t3-pstack` | `plugins/pstack/skills/poteto-mode/SKILL.md` | `5a8b33f83cb62d8cfd5819d6e45447a932b49084` | `77c5b8d38687c6ced6b1fb4bd7cb28056151c832648b143f038fb9ebb3249431` |
| `SKILL.md` | `cursor/plugins` | `pstack/skills/poteto-mode/SKILL.md` | `99743e9c151c8537cbbf1f98bb38f34ef3368453` | `c5e6b605f46e5d9fbab31afa7a99d3d50680f2180d1fdfae3a924901bc52d99a` |
| `LICENSE-MIT.md` | `chhoumann/t3-pstack` | `LICENSE` | `5a8b33f83cb62d8cfd5819d6e45447a932b49084` | `6501cf688d92764a93f25f4b9340c8a9e2e426022407e6b0e3159b1f2d96e4b9` |
| `LICENSE-MIT.md` | `cursor/plugins` | `pstack/LICENSE` | `99743e9c151c8537cbbf1f98bb38f34ef3368453` | `bc957ca6bee02792566a1a028d105e02e247c6e77cf057061674273da77b200e` |
| `playbooks/authoring-a-skill.md` | `cursor/plugins` | `pstack/skills/poteto-mode/playbooks/authoring-a-skill.md` | `99743e9c151c8537cbbf1f98bb38f34ef3368453` | `f6a13a445c360b48d6cd72780ac01955f45b82826476efe0e67c7559329407aa` |
| `playbooks/autonomous-run.md` | `cursor/plugins` | `pstack/skills/poteto-mode/playbooks/autonomous-run.md` | `99743e9c151c8537cbbf1f98bb38f34ef3368453` | `6ac974fd2b09748add56493e89f578a35a6a9289e1026515878d81ef3cf129d1` |
| `playbooks/autopilot-full.md` | `cursor/plugins` | `pstack/skills/poteto-mode/playbooks/autopilot-full.md` | `99743e9c151c8537cbbf1f98bb38f34ef3368453` | `acf4f4a58c11045f9d3e8807d907a877e61ca6432b079f1087d7d30fc931566f` |
| `playbooks/autopilot-stack.md` | `cursor/plugins` | `pstack/skills/poteto-mode/playbooks/autopilot-stack.md` | `99743e9c151c8537cbbf1f98bb38f34ef3368453` | `c6bcb18b2ce605e77a2a2225854590a4b9a687911f79331746d91a4fe9a52e60` |
| `playbooks/babysit.md` | `cursor/plugins` | `pstack/skills/poteto-mode/playbooks/babysit.md` | `99743e9c151c8537cbbf1f98bb38f34ef3368453` | `e261c1ff5581e0f8fc6c686f34de4b535f87473e77beabea7dd8323021214610` |
| `playbooks/babysit.md` | `cursor/plugins` | `pstack/skills/poteto-mode/references/bugbot-triage.md` | `99743e9c151c8537cbbf1f98bb38f34ef3368453` | `b2d146c770d8d3593e1ef3d77b668039b8e1f78093ea1a86f1d45d7f99614309` |
| `playbooks/bug-fix.md` | `cursor/plugins` | `pstack/skills/poteto-mode/playbooks/bug-fix.md` | `99743e9c151c8537cbbf1f98bb38f34ef3368453` | `66e26542dad131cfd7df80ac0cdf81ed4d85e7b5e3f0eb65b933888760c4831f` |
| `playbooks/eval.md` | `cursor/plugins` | `pstack/skills/poteto-mode/playbooks/eval.md` | `99743e9c151c8537cbbf1f98bb38f34ef3368453` | `a93d449a908236afa6645179651844094b1547dbab4e484cffcdda630e4b90bf` |
| `playbooks/feature.md` | `cursor/plugins` | `pstack/skills/poteto-mode/playbooks/feature.md` | `99743e9c151c8537cbbf1f98bb38f34ef3368453` | `af8ce700b99953741cb547e34308fde0cf6b98ce67e1652c800d0deedf53aba1` |
| `playbooks/hillclimb.md` | `cursor/plugins` | `pstack/skills/poteto-mode/playbooks/hillclimb.md` | `99743e9c151c8537cbbf1f98bb38f34ef3368453` | `942c1565b75ad02a2cb6230dd7c1ebd87e19f59a00319ebac2b6616007bf018f` |
| `playbooks/investigation.md` | `cursor/plugins` | `pstack/skills/poteto-mode/playbooks/investigation.md` | `99743e9c151c8537cbbf1f98bb38f34ef3368453` | `dc66bcf6af3a074fc7f67aa5e12b93ef571a4fb4d8e17f2f1af5ae5359f42e46` |
| `playbooks/multi-phase-plan.md` | `cursor/plugins` | `pstack/skills/poteto-mode/playbooks/multi-phase-plan.md` | `99743e9c151c8537cbbf1f98bb38f34ef3368453` | `5f239457bfdec3345c92caa06c59bf0257c662b89353f25a1c02ea942dcd00b1` |
| `playbooks/opening-a-pr.md` | `cursor/plugins` | `pstack/skills/poteto-mode/playbooks/opening-a-pr.md` | `99743e9c151c8537cbbf1f98bb38f34ef3368453` | `a5aef646de8b651306c2d10974623650e4a013a245aec1c00525bbe0e31bfa76` |
| `playbooks/orchestrate.md` | `cursor/plugins` | `pstack/skills/poteto-mode/playbooks/orchestrate.md` | `99743e9c151c8537cbbf1f98bb38f34ef3368453` | `08dce6c9e7be1d13bc6944ab9b51665f935c531437f5e088bc53d2a62099ef05` |
| `playbooks/pause-safely.md` | `cursor/plugins` | `pstack/skills/poteto-mode/playbooks/pause-safely.md` | `99743e9c151c8537cbbf1f98bb38f34ef3368453` | `77968cfe5f4a71a8cd33e0ae8ffcdbd88dd693a212c240457773e6c40c96c21d` |
| `playbooks/perf-issue.md` | `cursor/plugins` | `pstack/skills/poteto-mode/playbooks/perf-issue.md` | `99743e9c151c8537cbbf1f98bb38f34ef3368453` | `c12aa2f82de7651a11676a3d5fea168f539b7f0faaa3a501d279255dd2a469c8` |
| `playbooks/prototype.md` | `cursor/plugins` | `pstack/skills/poteto-mode/playbooks/prototype.md` | `99743e9c151c8537cbbf1f98bb38f34ef3368453` | `7aa1f52c691c3d46d5afc527b23f90977fce869ce33573c73c81a4c7f0cde962` |
| `playbooks/refactoring.md` | `cursor/plugins` | `pstack/skills/poteto-mode/playbooks/refactoring.md` | `99743e9c151c8537cbbf1f98bb38f34ef3368453` | `0f5dd38113379ea8cf61e2182eca0a7478eea9a869eb40c2dddab3335aeca197` |
| `playbooks/runtime-forensics.md` | `cursor/plugins` | `pstack/skills/poteto-mode/playbooks/runtime-forensics.md` | `99743e9c151c8537cbbf1f98bb38f34ef3368453` | `3463372b578c28f27c236f2627f09b5c5b1e85e86db7399fb984f3892fb450f5` |
| `playbooks/session-pickup.md` | `chhoumann/t3-pstack` | `plugins/pstack/skills/poteto-mode/playbooks/session-pickup.md` | `5a8b33f83cb62d8cfd5819d6e45447a932b49084` | `7b59e501edf115287cb2c358ff9f2d402e84bd9a688e2c2d823fa5229530b59a` |
| `playbooks/session-pickup.md` | `cursor/plugins` | `pstack/skills/poteto-mode/playbooks/session-pickup.md` | `99743e9c151c8537cbbf1f98bb38f34ef3368453` | `d194f2a7ef392c1598ef3f0e3b561370ca25c2c7a78308007af4aa46ada8ee12` |
| `playbooks/shipping.md` | `cursor/plugins` | `pstack/skills/poteto-mode/playbooks/shipping.md` | `99743e9c151c8537cbbf1f98bb38f34ef3368453` | `bf56339bdf7e0223bcff5abf4e8599e3f5b547b3fcc3b4ce9475e6e7dda14a9f` |
| `playbooks/trace-forensics.md` | `cursor/plugins` | `pstack/skills/poteto-mode/playbooks/trace-forensics.md` | `99743e9c151c8537cbbf1f98bb38f34ef3368453` | `ef0bbf79856a4ae1a8993d54c1a1da159cb97623941b652c0069cf75a017e0f5` |
| `playbooks/visual-parity.md` | `cursor/plugins` | `pstack/skills/poteto-mode/playbooks/visual-parity.md` | `99743e9c151c8537cbbf1f98bb38f34ef3368453` | `950ca51999a6454c98eee6bcbc3d1bbe501a4e3a5d5439b6f6ddc378991b256c` |
| `playbooks/worktree-cleanup.md` | `cursor/plugins` | `pstack/skills/poteto-mode/playbooks/worktree-cleanup.md` | `99743e9c151c8537cbbf1f98bb38f34ef3368453` | `be04ae0afe19d4a4da5bcc4e94455f68dbebd1cda6eb0f456ca0d358ecf76c00` |
| `principles/attack-the-premise.md` | `cursor/plugins` | `pstack/skills/principle-attack-the-premise/SKILL.md` | `99743e9c151c8537cbbf1f98bb38f34ef3368453` | `6a932884daad4aa189e9b5d1665226bbc75621d4d2a398fd4003bebd382f4599` |
| `principles/boundary-discipline.md` | `cursor/plugins` | `pstack/skills/principle-boundary-discipline/SKILL.md` | `99743e9c151c8537cbbf1f98bb38f34ef3368453` | `62ac2862c2caa22dd14531f51c9c6bb445ceb198ca98a687e25b4d47c1f10a28` |
| `principles/build-the-lever.md` | `cursor/plugins` | `pstack/skills/principle-build-the-lever/SKILL.md` | `99743e9c151c8537cbbf1f98bb38f34ef3368453` | `3434b0ad0c640c6f1d7960be7a8986c3bcdc14e26060360dec29903df60074ff` |
| `principles/encode-lessons-in-structure.md` | `cursor/plugins` | `pstack/skills/principle-encode-lessons-in-structure/SKILL.md` | `99743e9c151c8537cbbf1f98bb38f34ef3368453` | `228963799189f481827d6f28065f278bc2008ffa37030b1234cbd5814d36b9e9` |
| `principles/exhaust-the-design-space.md` | `cursor/plugins` | `pstack/skills/principle-exhaust-the-design-space/SKILL.md` | `99743e9c151c8537cbbf1f98bb38f34ef3368453` | `2de83d99f93f60ec6313455b0bc9aa9f0bfb93dd59f414f403691322db00d4db` |
| `principles/experience-first.md` | `cursor/plugins` | `pstack/skills/principle-experience-first/SKILL.md` | `99743e9c151c8537cbbf1f98bb38f34ef3368453` | `58903529d733b1c1a7c9ccf127d45ef3c7d0d9f0b81164a4dc6b80efe6f2912b` |
| `principles/explain-the-number.md` | `cursor/plugins` | `pstack/skills/principle-explain-the-number/SKILL.md` | `99743e9c151c8537cbbf1f98bb38f34ef3368453` | `cd5a25f9e7cf023627ccb470dc5faa97542f29b4319496a32b839a8e1e988047` |
| `principles/fix-root-causes.md` | `cursor/plugins` | `pstack/skills/principle-fix-root-causes/SKILL.md` | `99743e9c151c8537cbbf1f98bb38f34ef3368453` | `8df3c8c3fe57eb0055a5c8efab8ab144557fdf301da70b1cdc77a3a3ef3f3052` |
| `principles/foundational-thinking.md` | `cursor/plugins` | `pstack/skills/principle-foundational-thinking/SKILL.md` | `99743e9c151c8537cbbf1f98bb38f34ef3368453` | `864b827e8199d946ce58beca0f89c4ed4099ed6e426fb698a3aaa45de2a9eea2` |
| `principles/guard-the-context-window.md` | `cursor/plugins` | `pstack/skills/principle-guard-the-context-window/SKILL.md` | `99743e9c151c8537cbbf1f98bb38f34ef3368453` | `af0b9dd70b43628ce4a59a4d332e9d9ad055084e460f430e7a757495c627e81a` |
| `principles/laziness-protocol.md` | `cursor/plugins` | `pstack/skills/principle-laziness-protocol/SKILL.md` | `99743e9c151c8537cbbf1f98bb38f34ef3368453` | `1be6e7a435f26a75a76eb848b9c3d611b9977d0f5822361753244da25ca3ca45` |
| `principles/make-operations-idempotent.md` | `cursor/plugins` | `pstack/skills/principle-make-operations-idempotent/SKILL.md` | `99743e9c151c8537cbbf1f98bb38f34ef3368453` | `7aa9327cf1f1aa057e95d47a0a78bd88a8f9d556b608866fee939d455a53a019` |
| `principles/migrate-callers-then-delete-legacy-apis.md` | `cursor/plugins` | `pstack/skills/principle-migrate-callers-then-delete-legacy-apis/SKILL.md` | `99743e9c151c8537cbbf1f98bb38f34ef3368453` | `580ad9bb1a0994ecb924321ba49efc38a2f85c64e22c76fb133f57a78272a2e6` |
| `principles/minimize-reader-load.md` | `cursor/plugins` | `pstack/skills/principle-minimize-reader-load/SKILL.md` | `99743e9c151c8537cbbf1f98bb38f34ef3368453` | `1ea2b7fef2391cae5844c4efdbd59031f775e8a52d06b7495d707229a200dcca` |
| `principles/model-the-domain.md` | `cursor/plugins` | `pstack/skills/principle-model-the-domain/SKILL.md` | `99743e9c151c8537cbbf1f98bb38f34ef3368453` | `52c0d85e0c3827c41c18299b642657d7b47eaf77b7b31609e42e0df42b84c75f` |
| `principles/never-block-on-the-human.md` | `cursor/plugins` | `pstack/skills/principle-never-block-on-the-human/SKILL.md` | `99743e9c151c8537cbbf1f98bb38f34ef3368453` | `05030a7a083c337676f793881b4e93cd218e8f1dd676529f56e6ac1d3efb8d1f` |
| `principles/outcome-oriented-execution.md` | `cursor/plugins` | `pstack/skills/principle-outcome-oriented-execution/SKILL.md` | `99743e9c151c8537cbbf1f98bb38f34ef3368453` | `10eb91633aa570355ba4bb37088fcade2b22e498df7a58edc749e65bc5a78e2d` |
| `principles/prove-it-works.md` | `cursor/plugins` | `pstack/skills/principle-prove-it-works/SKILL.md` | `99743e9c151c8537cbbf1f98bb38f34ef3368453` | `ec79a15025bac8d33d62011c54f3b612733fd2a024e623b531b3637aa75070e2` |
| `principles/redesign-from-first-principles.md` | `cursor/plugins` | `pstack/skills/principle-redesign-from-first-principles/SKILL.md` | `99743e9c151c8537cbbf1f98bb38f34ef3368453` | `170e0a658783e43fee8ec5a8c2422a4abb8f69cef621dd1819a95910b8207034` |
| `principles/separate-before-serializing-shared-state.md` | `cursor/plugins` | `pstack/skills/principle-separate-before-serializing-shared-state/SKILL.md` | `99743e9c151c8537cbbf1f98bb38f34ef3368453` | `05294b40448e927c5da1c7b6f5c6b9fed3744637e3833d2d948b9154a9dd00bb` |
| `principles/sequence-verifiable-units.md` | `cursor/plugins` | `pstack/skills/principle-sequence-verifiable-units/SKILL.md` | `99743e9c151c8537cbbf1f98bb38f34ef3368453` | `2ccbbacc56ace5afdfb8670cef19d7bd009fb2a0033b9a741cbdf2b6baf72187` |
| `principles/subtract-before-you-add.md` | `cursor/plugins` | `pstack/skills/principle-subtract-before-you-add/SKILL.md` | `99743e9c151c8537cbbf1f98bb38f34ef3368453` | `8c93bb9d1a7f38e2ef37655d93f0e790fa59903105af3d500cc8a663ebe45f3f` |
| `principles/test-behavior-not-implementation.md` | `cursor/plugins` | `pstack/skills/principle-test-behavior-not-implementation/SKILL.md` | `99743e9c151c8537cbbf1f98bb38f34ef3368453` | `f7223698623b6a26fea49c751e466b38e6691b1f32ce841d3983e7ffbe2b74a6` |
| `principles/type-system-discipline.md` | `cursor/plugins` | `pstack/skills/principle-type-system-discipline/SKILL.md` | `99743e9c151c8537cbbf1f98bb38f34ef3368453` | `5cdaf79785e3c12b2592b9469ee8c272143eb86ab7a18d8382197cea5fd30106` |
<!-- upstream-files:end -->

`python3.13 scripts/owner-mode-upstream.py --check` (run by `scripts/check`)
fails when a playbook or principle has no row, a row names a missing file, or
a nested `SKILL.md` appears. `--compare <checkout>/pstack` reads a checkout of
upstream, or of a port laid out like `pstack/`, and lists each file as
unchanged, changed (with a diff against ours) or new since the pin.

## Local changes

The text is poteto's, edited only where it named a Cursor-only tool, and the owner's
policy merged into the playbook it governs. The edits follow one term map:

| Upstream | Here |
| --- | --- |
| `Task`, `subagent_type`, `run_in_background`, `poteto-agent` | The Agent tool; a fresh subagent told to read owner-mode's `SKILL.md` first. |
| `AskQuestion` | `AskUserQuestion`, only for a call no experiment can settle. |
| Model slugs, `/setup-pstack` roles, fast tiers, Grok defaults, cross-family judges | `claude-opus-5-5` for every role; a "different model" opinion is a fresh-context `claude-opus-5-5` reviewer. |
| Cursor `/loop` | Claude Code `/loop`. |
| `agent-transcripts/`, `~/.cursor/projects` | `~/.claude/projects/<this-project-slug>/` only. |
| Cursor cloud agent, Cursor restart | A worktree subagent or cloud session; compaction, a Mac switch or a session end. |
| `control-ui`, `control-cli` | The Claude Browser pane, Claude computer use, the `run` skill or Bash. |
| `deslop`, `no-comments`, `unslop`, `technical-writing`, `create-skill` | Our `deslop`, `scripts/no-comments.py` or the repo's linter, our `unslop`, the repo's skill rules. |
| `swarm`, `figure-it-out` | `parallel-plan`, or a Workflow when the owner asked for one. |
| `show-me-your-work`, `ketchup` | The working record; the final reply per AGENTS.md. |
| `how`, `why` | Read the code with cited paths; `git log` and `git blame`. |
| `architect`, `interrogate`, `tdd`, `benchmark-checklist` | Parallel design exploration per `exhaust-the-design-space`, `verify`'s independent review, `test-behavior-not-implementation`, `explain-the-number`. |
| Origin, `gt`, `merge-queue`, `watch-pr` | `gh` only; `gh pr checks --watch` and `gh pr view`. |
| `orch.ts`, `check-plan.mjs`, `worktree-audit.sh` | Not carried; the step is done by hand and says so. |

The owner's policy lives in the playbooks it governs: the branch, title, verdict,
Risk line and merge gate in `opening-a-pr.md`; the risk-tiered merge in
`babysit.md`, `shipping.md`, the autopilots and `orchestrate.md`; parked
Always pause items in `autonomous-run.md`; the working record in
`pause-safely.md`; this-project-only transcripts in `session-pickup.md` and
`eval.md`; owner-gated deletes in `worktree-cleanup.md`.

Upstream keeps the mode explicit-only with a Cursor custom mode, and t3-pstack
starts it with a session-start hook. Here the description starts it on three
kinds of work, because Claude Code has no custom mode and the owner chose
description routing over a hook.

## Upstream changes since 4e5b1cf

The adapted version before the vendored one pinned `4e5b1cf` (2026-10-04).
Every upstream commit since then that touches these files is in the text:

| Commit | Change |
| --- | --- |
| `df58112` | Default models to Opus and Grok, drop Sol (mapped to `claude-opus-5-5`) |
| `00b14f1` | Distill prompts to cut tokens |
| `08bd59b` | Cut sections from Babysit and Worktree cleanup |
| `2bd5dd4` | The chat that starts the mode runs the playbook |
| `364a77e` | Leaf skills live at `../<name>/SKILL.md`; helpers get this file's path |
| `b93e811` | Drop the ignored `mode` and `reminder` frontmatter |
| `ce649c0` | Match subagent effort to the job; shipping and autopilot rewrites |
| `8043881` | Autopilot loops catch the operator up |
| `e5136d8` | Restate four principles as reasoning |
| `99743e9` | Cut marginal sections from the type-system and migrate-callers principles |

To move the pin: run `--compare` against the new commit, port each changed
file through the term map, then update its row's commit and SHA-256.

## Claude port

poteto has said she is porting pstack to Claude. When it lands, run
`--compare` against her port. Her port is the better source: take its text,
keep only the owner's policy (the model, the risk-tiered merge, the owner-gated
deletes, the verdict gate and the working record), drop the term-map rows the
port makes unnecessary, and record the new rows.
