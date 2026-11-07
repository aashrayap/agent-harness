import type { On } from 'claude-code'
import { test, expect } from 'claude-code/testing'

// Stands in for ~/.dot-agent/docs/diagrams/mermaid-widget.html.
const TEMPLATE = '<h2 class="sr-only">SUMMARY</h2><div id="m"></div><script>const src = `SOURCE`;</script>'

const input = (surface: 'desktop' | 'terminal') => ({
  model: 'claude-opus-5-5',
  promptModel: 'claude-opus-5-5',
  surfaces: [surface],
  tools: [],
  outputStyle: null,
  traits: [],
})

const stub = (on: On) => {
  on('env.get', () => ({ value: '/home/owner' }))
  on('fs.read', ($, e) => ({
    value: e.path === '/home/owner/.dot-agent/docs/diagrams/mermaid-widget.html' ? TEMPLATE : '',
  }))
  on('prompt.compose', () => ({ sections: [{ id: 'intro', text: 'x', scope: 'shared' as const }] }))
}

test('desktop prompts carry the template page, unchanged, after the drawing rules', async ($, on) => {
  stub(on)
  const { sections } = await $.prompt.compose(input('desktop'))
  const rule = sections.find(s => s.id === 'mermaid-style:rule')
  expect(rule?.scope).toBe('session')
  expect(rule?.text).toContain('never send raw Mermaid to show_widget')
  expect(rule?.text.endsWith(`\n\n${TEMPLATE}`)).toBe(true)
  expect(rule?.text).toContain('never C4Context')
  expect(rule?.text).toContain('at most 8 boxes and 8 words per box')
  expect(rule?.text).toContain('series of small diagrams')
  expect(rule?.text).toContain('color means state only')
  expect(rule?.text).toContain('diagram-lint.py')
})

test('other surfaces get no rule', async ($, on) => {
  stub(on)
  const { sections } = await $.prompt.compose(input('terminal'))
  expect(sections.map(s => s.id)).toEqual(['intro'])
})
