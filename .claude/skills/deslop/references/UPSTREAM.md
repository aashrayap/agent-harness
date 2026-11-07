# Upstream provenance

Adapted from [`cursor/plugins`](https://github.com/cursor/plugins) at commit
`4e5b1cf2ccb0ea3716f08c8ee0a5856b5ab93536`.

Immutable source:
<https://github.com/cursor/plugins/tree/4e5b1cf2ccb0ea3716f08c8ee0a5856b5ab93536/pstack>

| Local file | Upstream file | Upstream SHA-256 |
| --- | --- | --- |
| `SKILL.md` | `pstack/skills/no-comments/SKILL.md` | `5c5b0882297d704c3a9720c52b7a793c68b013eaf717989f0945624efdfe2b05` |
| `references/hunter.md` | `pstack/agents/comment-sicko.md` | `c0fd0383008da45fc78cfac17b9007d62c42f87ad1c8d5c2fb658b1fd01f7c82` |

Upstream `pstack/LICENSE` SHA-256:
`bc957ca6bee02792566a1a028d105e02e247c6e77cf057061674273da77b200e`
([LICENSE-MIT.md](LICENSE-MIT.md)).

Local changes keep the split between a read-only hunter and a parent that
verifies and deletes. The hunter is a brief passed to a read-only helper
rather than a separate agent definition, so it works in Claude Code and Codex
without new install targets. Its scope widens from comments to stale
sentences, copied rules and dead code, because this harness is mostly prose.
The `architect`, `how` and `why` steps are dropped because the harness does
not carry those skills.
