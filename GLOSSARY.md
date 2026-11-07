# Glossary

One word, one meaning. Docs and skills use these words and avoid the rest.
`scripts/forbidden-words.py` enforces the retired ones.

## Layers

- **Template**: the starter files a repo copies once from
  [template/](template/README.md), then owns; its AGENTS.md names the template
  version it follows. Avoid: scaffold, boilerplate.
- **dot-agent**: the harness: the method (playbooks, verify, deslop, deeper),
  the rules, setup and the template, installed once into `~/.claude`.
  Avoid: config repo.

## System

- **Owner**: the one person the harness works for. They decide goals,
  priorities, risky merges and anything on the Always pause list in
  AGENTS.md.
- **Chat**: one agent conversation in Claude or Codex. Avoid: thread, session.
- **Domain**: one repo and the chat that owns it. A chat does its own domain's
  work and hands the rest to the owner of that domain as a brief.
- **Skill**: a selectively loaded capability with one `SKILL.md`. Avoid:
  plugin, command.
- **Always-on job**: anything that runs without the owner starting it, on a
  schedule or an event, such as the scheduled hunter. Avoid: bot, daemon.

## Loops

- **Outer loop**: the scheduled hunter. It proposes CONSTRAINTS rows and
  findings and never acts.
- **Inner loop**: the owner and one focused Chat on one item: playbook, build,
  check, verify, PR, merge gate. The only loop where work changes.

## Review and merge

- **BLOCKING, NOTE**: the two review finding severities, defined in the verify
  skill's L4. Only BLOCKING stops a merge.
- **High risk, low risk**: a PR's merge tier. `HIGH_RISK` in `verdict.py` is
  the list AGENTS.md names; `verdict.py risk` prints the tier. Agents merge low risk once the
  merge gate passes.

## Outside terms

How these words line up with poteto's pstack (MIT). Same means the words
already match.

| Ours | poteto (pstack) | Decision |
| --- | --- | --- |
| Outer loop | outer loop | same word; ours proposes rules |
| Inner loop | engineering lifecycle | kept |
| Always-on job | outer-loop bot, routine | kept: poteto uses coordinator for a per-project lead |
| Gardening, scheduled hunter | gardening, code-scanning routine | same |
| `CONSTRAINTS.tsv` | rule table in `/correct` | kept the file: a check can read a table outside the instruction file |
| impossible > check > test > hook > prose > memory | architecture > types > lint > test > docs | same order; impossible covers architecture and types (no type checker here), check covers lints, hook and memory are homes `/correct` lacks |
| verify, verdict | verifier agents, self-verification | same |
| Task | task | same |
| harness | shared engineering environment | kept: the name both runtimes install under |
