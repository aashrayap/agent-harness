# Overview Page

Start every page from [assets/overview-page.html](../assets/overview-page.html):
copy it, replace TITLE and the example sections, and keep its `<style>` block
unchanged. It carries the palette, the 880px column, the table and grid styles
and the Mermaid contrast overrides below.

A clean white page that tells a useful visual story. Organize around what the
reader needs to understand or decide, not a fixed set of dashboard components.

## Shape the story

- Start with a clear title and one takeaway.
- Show the relationship, journey, or choice visually.
- Add a few concise bullets where explanation is needed.
- End with the next action or unresolved decision.
- Keep sources and supporting detail in expandable sections or a quiet footer.

For a plan, a useful sequence is starting point → options → decision → next
step. Adapt it to the subject; do not turn it into mandatory headings.

## Choose the visual

- Prefer Mermaid for planning flows, dependencies, sequences and decisions.
  Show real branches and waits; keep labels short and meaningful.
- Use images, screenshots or illustrations when they explain a concrete idea.
  Caption only what the reader needs to notice. Avoid decorative stock imagery
  and repeated icons that add no information. Use the available image skill
  when generation or editing would help; label illustrative material honestly.
- Use a small comparison table when tradeoffs are easier to scan side by side.
- Use cards only for parallel choices. Include a tree only when hierarchy or
  file structure matters. Neither is a required page section.
- Let the visual carry the explanation; do not repeat every label in prose.

## Reduce the text

- Default to short, natural bullets, usually under ten words.
- Keep necessary qualifiers, uncertainty, units and source attribution.
- Remove routine badge rows, tag pills, category codes and numbered labels.
- Show status only when it changes a decision or next action.
- Avoid redundant eyebrows, subtitles, captions and section summaries.
- Use plain headings that say what the reader will learn.
- Keep implementation and verification metadata out of the main story.

## Appearance

- White background (`#FFFFFF`, `color-scheme: light`).
- Dark ink (`#182420`), muted text (`#5E6E68`).
- One restrained accent (`#0E6E5C`), light dividers (`#E3E9E6`).
- System sans-serif for prose; monospace only for actual code or paths.
- Centered reading column, roughly 880px wide; generous whitespace.
- Responsive layout; no page-wide horizontal scrolling.

## Page pattern

For status overviews across projects or systems; plans and comparisons keep
the template's style and choose their own sections.

- Title, then one accent takeaway line under it.
- A status table first when the page covers several projects or repos.
- One section per project or system: a plain heading, a one-line takeaway, a
  Mermaid flowchart grouped into subgraphs by stage (`direction TB` inside),
  then a two-column Part/Now table of components and their state.
- Small parallel views (one per repo) go in a `.grid` section.
- End with the reader's next steps.
- Required: write it, then a fresh reviewer cuts the visible text by about half
  and checks each claim against its source; that review is the page's one
  check before publishing.

## Mermaid on white

In an Artifact, write diagrams as `<pre class="mermaid">` blocks; the viewer
renders them without a script.

Some viewers override Mermaid with dark fills. Preserve contrast with both:

1. A diagram class definition:
   `classDef default fill:#FFFFFF,stroke:#182420,color:#182420`
2. Scoped CSS `!important` overrides inside the diagram container for
   `.node rect/polygon/circle`, `.nodeLabel`, `.cluster rect`,
   `.cluster-label`, `.edgePath path`, `.flowchart-link`, `.marker`, and
   `.edgeLabel`: white fills, dark labels and muted edges.

Outside an Artifact, render diagrams with `references/mermaid.md` (the page has
no Mermaid script of its own). Keep a useful static
fallback when the page needs to work without the external renderer.

## Deliver and inspect

Produce one HTML page. Publish only through an authorized capability;
otherwise save locally and open it when supported. Reuse the same output path
and favicon on revisions.

Inspect the actual output: readable visuals, no clipping, concise text and a
clear takeaway. Expand supporting detail to check it too. Verify the relevant
controls when available. If preview is blocked, state what was and was not
checked; a companion image does not verify the HTML layout or interactions.
