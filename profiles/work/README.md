# Work Profile

This portable overlay is applied only when the machine-local selector contains
`work`. It intentionally contains no employer, project, identity, region, or
service details. Put those details in repository-local instructions or
machine-local runtime configuration.

Enable it with the setup commands in the
[runtime reference](../../docs/harness-runtime-reference.md#setup).

The tracked `ensure.sh` is a deliberately neutral extension seam.
Machine-specific services and Codex settings stay outside Git, in the runtime's
own config, and setup leaves them alone.

`provided-skills` names skills another installer supplies on this profile.
Setup does not install, record, or retire them; on the first run it moves aside
its own earlier copies so the providing installer can take over. Put that
installer in the machine-local `state/work-ensure.sh`, which `ensure.sh` runs.
