---
name: unslop
description: Finish human-facing prose without changing its meaning or governing output contract.
disable-model-invocation: true
---

# Unslop

Apply a finishing pass to human-facing prose. Make it sound written by a
specific person, not generated from a template.

## Contract first

Explicit style and output contracts win. Preserve `bullet-style`, `visual`,
templates, quotations, facts, numbers, links, code, and source-locked text. Do
not change required headings, labels, order, limits, or schemas. Improve only
the prose an active format contract leaves editable. If protected content
makes another output contract impossible, do not rewrite it. Stop and report
the conflict.

## Pass

1. Identify the audience, intended voice, and protected content. If those are
   unclear, preserve the draft's existing choices.
2. Read [patterns.md](references/patterns.md) for the prose being edited. Remove
   the tells that actually occur; do not mechanically apply every pattern.
3. Preserve meaning and the author's real point of view. Never invent facts,
   measurements, quotations, experiences, preferences, or certainty.
4. Read the result once as a skeptical human: cut remaining filler, vary rhythm
   where the format allows it, and replace vague abstractions with concrete
   language already supported by the source.

Return the finished prose only unless the user asks for an edit log. Preserve
any required outer contract, including repository-required outcome markers.
