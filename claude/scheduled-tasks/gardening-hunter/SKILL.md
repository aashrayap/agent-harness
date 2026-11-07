---
name: gardening-hunter
description: Read-only slop and template-drift hunt, one isolated hunter per template repo; prints findings for the owner to decide
---

This file is installed by ~/.dot-agent/setup.sh from claude/scheduled-tasks/gardening-hunter/SKILL.md; edit it there.

Use only the model claude-opus-5-5. Read ~/.dot-agent/AGENTS.md, then read ~/.dot-agent/skills/engineering/deslop/references/scheduled-hunter.md and follow it exactly. Its hunter brief is the hunter.md file next to it.

Repos to hunt, one isolated read-only `Explore` helper each, run in parallel: every repo step 2 of that file finds. Give each helper only its own repo: scope `repo` set to that path, the hunter.md brief, and that repo's `CONSTRAINTS.tsv` and `AGENTS.md` as the rules it checks against. A helper never reads another repo. Each finding's `repo` is the repo it came from.

Template drift, yourself: run `python3 ~/.dot-agent/template/sync-rules.py drift <every repo above> --json`; it checks the template number, `conform.py` and the rules file of each repo that follows the template, each gap naming its fix, and leaves `gaps` null for one that never adopted it. Each repo with gaps gets one finding: `kind` `template-drift`, `severity` `medium`, `recommendation` `do`, `title` the first gap, `why` the gaps joined, and `evidence_count` the number of gaps. Never run `write` or `apply.sh` yourself.

README drift, yourself: for each repo above that follows the template, run `python3 ~/.dot-agent/template/scripts/readme-check.py <repo> --json`. Each repo whose `ok` is false gets one finding: `kind` `readme-drift`, `severity` `medium`, `recommendation` `do`, `title` the first problem, `why` the problems joined, and `evidence_count` the number of problems.

Hard rules:
- Report only. Never edit, commit, push, switch branches or open a PR in any repository.
- Never copy chat message text, private data or tokens into a finding.
- Do not mine chats or review verdicts for repeated corrections.

When done, reply with the findings list, then one line: the number of findings by severity and repo, and anything that blocked you.
