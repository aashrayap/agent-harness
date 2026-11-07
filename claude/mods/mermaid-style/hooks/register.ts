import type { Register } from 'claude-code'

// The one template AGENTS.md names, read at each compose so edits there apply.
// It carries the theme CSS, the legend and the zoom viewer; this mod adds none.
const TEMPLATE = '/.dot-agent/docs/diagrams/mermaid-widget.html'

// The desktop app draws a widget from the model's tool input as it streams, so
// a tool.call rewrite never reaches the screen: the model has to write the
// finished HTML itself. This hands it the exact page to copy.
export function rule(page: string): string {
  return `Diagrams (mermaid-style mod): never write a \`\`\`mermaid fence in chat and never send raw Mermaid to show_widget; both show as text. To show a Mermaid diagram, call show_widget with widget_code set to exactly the page below, changing only SUMMARY (one sentence) and SOURCE (the Mermaid source, kept inside its backticks). The page ties colors to the theme, adds a legend for the states the diagram uses, fits the width and opens larger on a click. Draw for the reader:
- Plain words: every box and edge label is in the reader's words; no code names, file paths, flags, PR numbers or tags in a box unless the reader needs that path itself.
- Small: at most 8 boxes and 8 words per box; edge labels of one to three words or none. Anything with three or more parts becomes a series of small diagrams, each adding one piece, never one big chart.
- One meaning per channel: color means state only. Mark a box \`class X done\` (working today), \`todo\` (being built or planned) or \`problem\` (broken or blocking); group with subgraphs, never color. Never classDef, style, linkStyle, init directives or hex colors.
- Use flowchart, sequenceDiagram, stateDiagram or erDiagram; never C4Context or the other C4 types: Mermaid's C4 is experimental, ignores the theme (hard-coded blue boxes) and lays labels over the lines.
- Self-check: \`python3 ~/.dot-agent/scripts/diagram-lint.py --json '<source>'\` fails a diagram that breaks a limit it can count; when unsure, run it before sending.

${page}`
}

export const register: Register = on => {
  on('prompt.compose', async ($, e, next) => {
    const composed = await next(e)
    if (!e.surfaces.includes('desktop')) return composed
    const home = await $.env.get('HOME')
    const page = await $.fs.read(`${home}${TEMPLATE}`)
    return { sections: [...composed.sections, { id: 'mermaid-style:rule', text: rule(page), scope: 'session' }] }
  })
}
