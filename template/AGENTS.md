# REPO

Follows template 2.

What is true only in this repo: authority, judgment and where to look.
Enforced rules are rows in [CONSTRAINTS.tsv](CONSTRAINTS.tsv), not lines here.

## Where do I look

| For | Go to |
|---|---|
| What a word means | [GLOSSARY.md](GLOSSARY.md) |
| Every enforced rule and its proof | [CONSTRAINTS.tsv](CONSTRAINTS.tsv) |
| How to prove a change works | [VERIFY.md](VERIFY.md) |
| The one command that checks everything | `scripts/check --tests` |
| What changed, what to run after pulling | [VERSION](VERSION), [RELEASES.md](RELEASES.md) |
| What must stay out of Git | `scripts/private-boundary.py` |
| Team skills (optional) | `.agents/skills/` |
| Repos a launchpad gathers (optional) | `launchpad.json` |

## Method

- A mistake corrected twice becomes a CONSTRAINTS.tsv row at the strongest
  level that holds: impossible > check > test > hook > prose > memory. A row
  points at its enforcer and never restates it.
- Work runs plan, build, `scripts/check --tests`, the [VERIFY.md](VERIFY.md)
  layers, then a PR that raises VERSION with a RELEASES.md entry.

## Authority

- What an agent may change here without asking, and what waits for the owner.

## Judgment

- The few calls a check cannot make, each one line.
