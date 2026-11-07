# Wiki schema

This project's knowledge base, kept in the LLM wiki pattern (Karpathy, April
2026). It holds what we know about the world: findings, sources, tools and
the things they describe. Decisions and how-to-work rules live in project
memory; plans live in their own documents. Replace this paragraph with what
this wiki covers and what it must never change.

## Who writes what

| Path | Written by | Rule |
|---|---|---|
| `../inbox/` | any thread | one folder per dump, `YYYY-MM-DD-slug/`, with a `NOTE.md` line saying what it is and who made it |
| `raw/` | wiki keeper only | inbox folders move here on ingest; never edited afterwards |
| `sources/`, `topics/`, `entities/` | wiki keeper only | the pages below |
| `index.md` | `wiki.py index` | generated from frontmatter; never edited by hand |
| `log.md` | wiki keeper only | append-only |

One writer avoids last-write-wins on a shared folder. A reader that finds a
page wrong drops a correction note in the inbox instead of editing it.

## Reading it

1. Read `index.md`. Every page has one line saying what it answers.
2. Open only the pages that match the question, and follow `[[links]]`.
3. Open `raw/` only to check a claim a result depends on.
4. Do not grep the whole wiki on a network mount; every file read downloads.

## Page types

- **source**: one per raw item, `sources/<slug>.md`. What it is, when and by
  whom, the 5 to 10 claims that matter here with labels, and where it
  disagrees with other sources.
- **topic**: a question that keeps coming back, `topics/<slug>.md`. Leads with
  the current answer in two or three sentences, then evidence, then open
  questions. Synthesizes across sources; never a copy of one.
- **entity**: a company, tool, organization or platform,
  `entities/<slug>.md`. Facts with sources and the topics it appears in.

Every page starts with this frontmatter. `type` is source, topic or entity;
`confidence` is the weakest label the summary rests on; `status` is current,
stale or superseded, and a superseded page names its replacement.

```yaml
---
title: Posting APIs
type: topic
summary: One line; index.md shows it.
sources: [official-api-docs, scheduler-review]
updated: 2026-10-18
confidence: measured
status: current
superseded_by:
---
```

Claims in a body carry **[measured]**, **[inferred]** or **[guess]**. A source
that checked a fact itself makes it measured; vendor claims stay inferred.
Links are `[[slug]]`, which Obsidian reads too. Slugs are kebab-case and unique
across the three folders.

## Operations

**Ingest** (when the inbox has items, and in a daily sweep):
1. Move each inbox folder to `raw/` unchanged.
2. Write its source page.
3. Update or create the topic and entity pages it touches; prefer updating
   an existing page, and note contradictions on both pages.
4. Run `wiki.py index`, append one `log.md` line per page touched, then
   `wiki.py lint`.

**Query** (anyone): read as above. An answer that took real synthesis and will
be asked again goes to the inbox as `answer.md`, so it becomes a page.

**Lint** (weekly): `wiki.py lint` finds missing frontmatter, broken links,
unknown sources, pages missing from the index, orphans, stale current pages
and waiting inbox folders. Then judge what a script cannot: contradictions,
duplicates to merge, and questions asked with no page. Fix what is
mechanical; report only what needs the owner.

## Scale

Index-first reading holds to roughly 150 pages. Past that, add a search layer
such as qmd instead of reading more of the index.
