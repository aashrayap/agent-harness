---
name: llm-wiki
description: Run a project's LLM-maintained wiki (Karpathy pattern). Use to set one up, drop research in its inbox, ingest, answer from it, or lint it.
argument-hint: "init <dir> | ingest | query <question> | lint"
---

# LLM wiki

One knowledge base per project: an inbox anyone writes, a wiki one keeper
writes, and an index every reader opens first. The instance's own `AGENTS.md`
is its schema and wins over this file.

```text
inbox/YYYY-MM-DD-slug/ ──ingest──▶ wiki/raw/ (immutable)
                                   wiki/sources/  one page per raw item
                                   wiki/topics/   current answers, synthesized
                                   wiki/entities/ companies, tools, platforms
                                   wiki/index.md  generated; read first
                                   wiki/log.md    append-only
```

## Set up

1. `python3 <this skill's folder>/scripts/wiki.py init <project>/wiki`
   creates the folders, a sibling `inbox/`, `log.md`, `index.md` and
   `AGENTS.md` from
   [references/schema.md](references/schema.md). It never overwrites.
2. Edit the schema's first paragraph: what this wiki covers and what it must
   never change.
3. Name one keeper (a dedicated thread or chat). Give it two routines: a
   daily ingest sweep and a weekly lint.
4. Add one line to the project's instructions: "Drop research in `inbox/`;
   read `wiki/index.md` before researching anything."
5. First ingest: copy existing research into `inbox/` and ingest it.

Keep separate wikis for separate audiences, such as a private project wiki
and a public learning wiki, rather than tagging one; a query may read a
sibling's index.

## Roles

- **Anyone:** write a dump into `inbox/<date>-<slug>/` with a `NOTE.md`; read
  `index.md` first for context. Never edit the wiki directly.
- **Keeper:** ingest, regenerate the index, lint, and keep each page small.
  Follow the instance's `AGENTS.md`.

## Ingest, query, lint

The steps are in the schema. The deterministic parts are verbs:

```bash
wiki="<this skill's folder>/scripts/wiki.py"
python3 "$wiki" index <wiki>
python3 "$wiki" lint <wiki> --json
```

An instance on a shared folder that other sessions run from, such as a
cloud Claude Project, keeps a copy at `wiki/scripts/wiki.py`.

`lint` exits 2 when the folder has no `index.md`, 1 on any structural
finding (frontmatter fields and values, broken links, unknown or malformed
sources, duplicate slugs, an index out of step with the pages, even by one summary) and 0 when
only stale pages, orphans or a waiting inbox remain. Run `index` before
`lint` after every ingest.

Obsidian is optional and read-only: open a copy of the wiki folder as a vault
for the graph and backlinks. Past about 150 pages, add a search layer.
