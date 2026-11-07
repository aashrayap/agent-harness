# Upstream provenance

Adapted from `pstack/skills/arena/SKILL.md` in
[`cursor/plugins`](https://github.com/cursor/plugins) at commit
`fd6dd6f7276956a532bb78a748a8d2818b6eb5f4`.

Immutable source:
<https://github.com/cursor/plugins/blob/fd6dd6f7276956a532bb78a748a8d2818b6eb5f4/pstack/skills/arena/SKILL.md>

Source SHA-256:
`a2241e8500a44d9c16bd3260c8c70e28c4bb8a857c33061d42b267057e6f7093`.
Upstream `pstack/LICENSE` SHA-256:
`bc957ca6bee02792566a1a028d105e02e247c6e77cf057061674273da77b200e`.

Local changes replace Cursor-specific model files and identifiers with the
central runtime model policy (docs/harness-runtime-reference.md), require
isolated worktrees for concurrent writers, cap reruns and repairs, and make
parent reconciliation plus `verify` the completion gates. The
candidate/base/graft tournament remains intact.

The complete upstream license is in [LICENSE-MIT.md](LICENSE-MIT.md).
