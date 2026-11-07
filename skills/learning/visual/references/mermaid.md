# Mermaid Mode

Render a viewable HTML page for diagram requests beyond an ordinary inline
completion diagram.

## Drawing rules

Every Mermaid diagram, inline or in a page, is drawn for the reader:

- Plain words: box and edge labels say what the reader would say. No code
  names, file paths, flags, PR numbers or tags in a box unless the reader needs
  that path itself.
- Small: at most 8 boxes of at most 8 words; edge labels of one to three words
  or none.
- A series, not a chart: anything with three or more parts is shown as small
  diagrams in order, each adding one piece, with a sentence between them.
- One meaning per channel: color means state only, through `class X done`
  (working today), `todo` (being built or planned) or `problem` (broken or
  blocking); grouping uses subgraphs, never color. The inline template draws the
  legend from the classes the diagram uses.
- Check: dot-agent's `scripts/diagram-lint.py --json <source or file>`
  fails on more than 8 boxes, a label over 8 words, `classDef`, `style`,
  `linkStyle`, hex colors, init directives and C4 types.

## Viewer workflow

1. Get the Mermaid source: write it yourself for the concept, or take what the user provides (raw, a file, or a fenced block — the script strips fences).
2. Run the renderer:
   ```bash
   <this skill's folder>/scripts/render_mermaid.py --title "<title>" --code "<mermaid source>"
   ```
   For long diagrams, pass a file or pipe via stdin instead of `--code` to avoid shell-quoting pain:
   ```bash
   <this skill's folder>/scripts/render_mermaid.py diagram.mmd --title "<title>" --out tmp/diagram.html
   ```
3. The script writes the HTML, opens it (Chrome → default browser → `xdg-open`), and prints `file:`, `link:`, and `opened:`.
4. Always relay the `link:` (file:// URL) to the user, even when auto-open succeeds. If `opened: no`, tell them to open that link manually.

## Rules

- The page renders client-side via mermaid.js (CDN, pinned to v11) with `securityLevel: 'loose'` + `htmlLabels` so `<br/>` labels work; raw source is in a collapsible block; if the CDN is unreachable it shows the source with a clear message rather than a blank page.
- Inside a repo, pass `--out` to a scratch/ignored path (e.g. `tmp/`) to avoid cluttering the tree. With no `--out`, output lands in `~/.dot-agent/state/mermaid/`.
