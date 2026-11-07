# dot-agent Harness Runtime Reference

Read when selecting models, dispatching agents or changing setup.

## Models

| Client | Use | Model | Effort |
| --- | --- | --- | --- |
| Claude Code (CLI and desktop) | Everything (default, subagents) | `claude-opus-5-5` | `high` (`medium` for bounded work) |
| Claude Code (CLI and desktop) | Fast, simple work: quick lookups, mechanical edits, light subagents | `claude-sonnet-5-5` | `medium` |

- Claude picks Sonnet explicitly (`model: sonnet` on an agent, `/model
  sonnet`); the `haiku` alias also resolves to Sonnet. Anything unpinned
  stays on Opus. Setup enforces this: `claude/model-lock.json` →
  `~/.claude/settings.json`.
- Operating the other app's UI at the owner's request is allowed; running its
  models is not. Record which model did the work truthfully.
- Runtimes share only through working records in git.

## Codex: paused, not retired

Codex is paused, so no Codex model runs and Codex work goes to Claude. Its
pins stay in `codex/config.toml`, which setup installs with `--runtime codex`
or `all`, so Codex resumes unchanged when it returns.

## Setup

- Install once per Mac, update on clean `main` (an open PR is not installed
  production), then check:

  ```bash
  git clone https://github.com/<you>/agent-harness.git ~/.dot-agent && ~/.dot-agent/setup.sh --runtime claude
  cd ~/.dot-agent && git pull --ff-only && ./setup.sh
  python3 ~/.dot-agent/scripts/verify-profile.py
  ```

  To apply a machine profile from `profiles/`, `echo <profile> >
  ~/.dot-agent/state/machine-profile` and rerun setup. `./setup.sh --check-instructions` runs the read-only
  audits; `scripts/check --tests` runs the repository checks CI runs. Setup
  sets `core.hooksPath` to `.githooks`, whose pre-commit refuses commits on
  `main` or `master` and runs the static checks, and merges
  `claude/hooks.json` into `~/.claude/settings.json`: a PreToolUse hook that
  denies pushes to main or master (the hook allows the call when its script
  is missing, so an old checkout never blocks Bash), and a merge gate,
  `claude/hooks/merge-gate.py`, that denies `gh pr merge` unless the PR's
  checks are green, its head has a PASS verdict with no open BLOCKING
  finding, `--match-head-commit` pins that head, and its changed files were
  read. A low-risk PR then merges; a high-risk PR (`verdict.py risk`) also
  needs the owner's yes, recorded with `verdict.py approve` (AGENTS.md, Always
  pause). The agent records their words, so the gate stops accidents, not a
  dishonest agent. These are guards against accidents, not walls: the push hook reads the
  command text, so a push hidden behind a variable or alias gets through;
  `git commit --no-verify` skips the commit guard; and with `core.hooksPath`
  set, hooks in `.git/hooks` no longer run.
- Keep tracked config portable: no private context, trusted-project
  allowlists, permission bypasses, or machine overrides.
- `CONSTRAINTS.tsv` lists every enforced rule: `id`, `rule`, `level`
  (impossible > check > test > hook > prose > memory), `enforcer` (a repo
  path, optionally `path::name`), `proof` (the past mistake or test the
  enforcer fails on; required above prose) and `notes`.
  `scripts/check-constraints.py` checks each enforcer exists and each prose
  rule still appears in its file. `verify-profile.py` is the install check; it takes the same
  `--runtime` as setup and defaults to the saved one.
- A retired managed skill that is now a link into another repo belongs to
  that repo, so setup and `verify-profile` leave it alone.
- `--runtime` picks what setup installs: `codex` (the default), `all`, or
  `claude` for a Claude-only Mac. Setup saves an explicit choice in
  `state/runtime-scope` and reuses it on a bare `./setup.sh`. Moving to
  `claude` retires the Codex links and unedited skill copies setup installed
  to `state/backups/retirement/`; the owner's own Codex files, edited skills,
  history and `config.toml` stay.
- Codex app automations live in `~/.codex/automations`; setup never creates or
  removes them.
- `~/.claude/CLAUDE.md` is machine-local: setup only keeps its first line an
  import of the generated instructions and backs the file up before changing
  it. A same-named skill of the owner's in `~/.claude/skills` blocks setup instead of
  being replaced.
- `VERSION` on `main` rises with every merged PR (patch by default, minor for
  new behavior, major for a breaking change); CI enforces the bump. Setup
  records the installed version, and `./setup.sh --version` compares source,
  installed and `origin/main` so both Macs can confirm they match.
- Deleted skills, settings and LaunchAgents that setup once installed retire
  to `state/backups/retirement/` and `state/retired-launchagents/`
  (`scripts/fixtures/retired-runtime.json` lists them).

## Boundaries

- Work sync and harness update are separate operations. Work sync reconciles
  commitments and the intended outcome record through their owners;
  harness update changes executable source, skills and setup, with the
  commands above and the yes it needs in [AGENTS.md](../AGENTS.md#always-pause).
  Missing or unpublished other-Mac work is disclosed, never invented.
- `~/.dot-agent` owns portable executable source; each repository's own
  `AGENTS.md` supplies its project boundary. Claude Code conversations remain
  evidence.
- Credentials, tokens, service bindings and runtime pins stay machine-local;
  never transport raw runtime state or tokens. A synthetic install receipt does
  not prove behavior on another machine.
