# Skills

`skills/` owns Claude Code and Codex capability payloads. Source edits reach the runtime through
`setup.sh`; runtime copies are installation targets.

Use the [owner-mode skill list](engineering/owner-mode/SKILL.md) when discovery helps.

## Writing a skill

The layout, manifest and catalog rules are rows in
[CONSTRAINTS.tsv](../CONSTRAINTS.tsv) (`skill-manifests`, `skill-names-unique`,
`skill-catalog`); the checks name the fix. What they cannot check:

- Keep SKILL.md lean: trigger, core workflow, narrow reference links. Add a
  skill only for a needed capability, never a mandatory planning or approval
  chain; prefer composing an existing owner over a new entrypoint.
- Put support in `references/`, `scripts/`, `assets/`, `shared/` or `agents/`;
  other top-level files are not installed. A `claude/SKILL.md` or
  `codex/SKILL.md` wrapper is only for runtime syntax.
- Point at the runtime reference for models instead of repeating pins, keep
  third-party licenses/hashes with what you adapt, and change another skill's
  state only through its helper.

```bash
python3 scripts/validate-skill-manifests.py
python3 scripts/skill-instruction-audit.py --strict
```
