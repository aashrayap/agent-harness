# Releases

Newest first. Each entry says what is new and what each machine must do after pulling.

## 2.27.1 — 2026-11-07
New: the README is cut to about 100 words with one diagram.
Setup: none.

## 2.27.0 — 2026-11-06
New: public snapshot of the private `dot-agent` harness at its version 2.27.0. The rules table, hooks, merge gate, verify flow, `scripts/check`, tests, skills and repo template are kept. Removed as private or machine-specific: the personal task and chat tooling the harness was wired to, its three hooks (domain note, chat title, open-list), the store-boundary check, the handoff and expense skills, and the private release history; their rows left `CONSTRAINTS.tsv`. `ash-mode` is now `owner-mode`, and rules say "the owner" for the one person the harness works for. Earlier release notes stay in the private repo.
Setup: fresh install, `./setup.sh --runtime claude`.
