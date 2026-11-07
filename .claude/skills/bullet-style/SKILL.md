---
name: bullet-style
description: Format answers as concise bullets with a configurable word cap per bullet. Invoke explicitly with $bullet-style or /bullet-style, optionally followed by a word cap or bullet-count and word-cap pair.
disable-model-invocation: true
---

# Bullet Style

Format responses as scannable bullets with strict per-bullet word caps.

## Parameters

- Default: no bullet cap, 10 words per bullet.
- One arg: `bullet-style N` sets word cap.
- Two args: `bullet-style B N` sets max B bullets, N words each.
- Spoken run-together arg (dictation joins the numbers): a single
  3-digit number splits first digit / last two — `310` = 3 bullets,
  10 words each; `520` = 5 bullets, 20 words each.
- A 4-digit number splits two/two — `1015` = 10 bullets, 15 words.
- 1–2 digit numbers keep the one-arg word-cap meaning
  (`bullet style 6` = 6-word cap, no bullet cap).
- Bullet cap counts top-level bullets and sub-bullets together.
- Apply word cap to every bullet and sub-bullet.
- Count code, filenames, dates, and numbers as words.
- Keep exact technical names even when they exceed cap.

## Shape

- Prefer top-level bullets for categories or conclusions.
- Use sub-bullets when details improve scan; one sub-level maximum unless
  requested.
- Do not force sub-bullets for simple lists.
- Keep each bullet one idea.
- Use fragments when clearer.
- Use tables only for numeric comparisons or status summaries.
- Preserve user-requested headings, ordering, and labels.

## Output Rules

- No intro unless context needs it.
- No outro unless next action matters.
- Remove filler, hedging, and repeated labels.
- Prefer verbs and concrete nouns.
- Keep warnings explicit.
- Keep code, commands, and quotes exact.

## Example

Status answer:

- `Ready`: send now.
  - Valid email present.
  - No blocking caution.
- `Verify`: hold.
  - Confirm routing first.
  - Use site if no email.
