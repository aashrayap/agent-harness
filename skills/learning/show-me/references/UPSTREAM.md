# Upstream provenance

Adapted from `plugins/show-me/skills/show-me/SKILL.md` in
[`humanlayer/skills`](https://github.com/humanlayer/skills) at commit
`3c2629142c5d437428269b1b722b08c0b87f574d` (plugin version `1.0.1`).

Immutable source:
<https://github.com/humanlayer/skills/blob/3c2629142c5d437428269b1b722b08c0b87f574d/plugins/show-me/skills/show-me/SKILL.md>

Source SHA-256:
`bea6da70a58096730b9aeb0bae293ddf4726103a98efc9ce13c481619942a810`.
Upstream `LICENSE` SHA-256:
`5f13c18ea00ea5c1384f41745feeca774079164f7f59a92e4ac0899ad217b26f`.

Local changes make the skill explicit-only and inline-only, distinguish its
lightweight role from dot-agent's deeper `explain` owner, and replace the
upstream Claude-specific `Bash(open ...)` HTML path with a recommendation that
the user explicitly invoke dot-agent's `visual` artifact owner. The inline
visual format selection remains intact; two redundant `diff` examples were cut.

The complete upstream license is in [LICENSE-MIT.md](LICENSE-MIT.md).
