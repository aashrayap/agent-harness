---
name: visual
description: "Create clear visual explanations, plans and artifact pages: a clean white overview, concise bullets and a story. Mermaid for flows, images when they explain, tree mode on request."
argument-hint: "<what to visualize; optional mode: tree|mermaid|overview-page; optional output path>"
disable-model-invocation: true
---

# Visual

One entrypoint for visual output. Pick the cheapest mode that satisfies the
request, read that mode's reference file, then follow it.

Lead with a takeaway, show the idea visually, then name the next step. Prefer
concise bullets, useful images and Mermaid planning diagrams. Omit routine
badges, numbered labels and repeated status text. Start pages from the
overview template's style and choose sections for the story.

## Mode Selection

| Need | Mode | Read first | Output |
| --- | --- | --- | --- |
| Map files to add/modify/read/ignore before building | tree | `references/tree.md` | Annotated ASCII tree in the reply |
| See a diagram now (flowchart, sequence, state, graph) | mermaid | `references/mermaid.md` | HTML viewer |
| A visual overview, plan, comparison, or context page | overview-page | `references/overview-page.md` | Clean white HTML page published as an Artifact (or opened locally) |

- An explicit mode word from the user wins.
- No mode named: overview-page is the default whenever the user wants an
  artifact, overview, or shareable status page. Use tree alone for
  implementation plans and mermaid alone when the user just wants to see the
  shape now.
- Tree and mermaid also render as components inside an overview page; prefer
  composing them there over separate outputs when the request is a page.
- "Artifact" is an output surface, not a skill name.
- Pure understanding or comparison with no artifact belongs to `explain`;
  return here only if a durable diagram is then requested.

## Shared Delivery Rules

- Ordinary task-completion diagrams stay inline and follow the governing
  completion contract; they do not require this skill, a file or a browser.
  Use a labeled tree when an inline visual is unavailable.
- For visual artifacts, show the human-readable surface: the tree text, the
  mermaid `link:`, or rendered `.png` paths. These artifact rules do
  not replace the surrounding explanation of the problem and result.
- For saved artifacts, keep editable sources next to rendered output for future
  edits; treat them as internal artifacts.
- Inspect rendered artifacts before citing them; fix and rerender until readable.
