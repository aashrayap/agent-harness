# Phrase + Echo

Use this explicit `$teach` mode for one 3–7 minute, chat-native language lesson.
It is a focused execution loop, not a curriculum database, scheduler, or
morning-planning surface.

## State and ownership

- Keep lesson content, compact receipts, and the owner's paired result replies
  in the focused learning task's conversation. Do not create `MISSION.md`,
  lessons, cards, scores, progress files, or another learning database for this
  mode.
- Another chat may send an explicit `$teach` request here. It does not
  run the lesson, retain learning history, or choose curriculum.
- Automations are outside the loop. Add a commitment, date, or
  recurring prompt only after the owner separately asks through its owning
  workflow.

## Deterministic envelope

Number sessions consecutively as `S1`, `S2`, and so on. Give each introduced
phrase its own consecutive ID, `P1`, `P2`, and so on. A remediation session may
introduce no phrase. A missed calendar day creates no backlog and no catch-up
lesson.

1. Read prior lesson receipts and paired owner results. At the start of a new
   session, emit one finalized line for the preceding session by combining its
   pending receipt with the owner's result. If the result is unavailable, mark
   it `unknown`; never infer success or failure. When earlier evidence is needed,
   request the receipt and its immediately following owner result together.
2. Build recall prompts in this order, removing duplicates and stopping at
   three: phrase IDs identified as missed in the latest result, then phrases
   introduced in sessions `S-1`, `S-3`, and `S-7`. Skip session indices below 1,
   absent history, and sessions whose receipt says `new: none`.
3. Ask for productive recall from a situation before showing the target
   language. Use a one-message self-check: put answers in a collapsed Markdown
   `<details>` block when supported; otherwise place them after a clear
   `Reveal` divider. If the owner instead types an answer, correct it before
   continuing.
4. The reveal is the immediate correction. If the latest result reports two or
   more misses, use the next lesson to correct and apply those phrases; add no
   new phrase.
5. Otherwise introduce at most one new phrase. Require an audible echo once
   while looking and once from memory, then finish with one tiny spoken action.
   Keep the content plausibly completable in about four minutes and within the
   seven-minute scope; do not claim measured elapsed time.
6. Invite only a terse, paired self-report used as a next-session selection
   signal, not verified mastery: `Result: session S · recalled X/Y · missed
   {phrase IDs} · used`, `Result: session S · recalled X/Y · missed {phrase IDs}
   · practiced`, or `Result: session S · skipped`. Omit the `missed` field when
   none were missed.

The `S-1/S-3/S-7` rule is fixed light spacing, not individualized spaced
repetition. Do not claim adaptive scheduling or mastery.

## Intelligent content selection

Use judgment only inside that deterministic envelope:

- Teach a useful phrase anchored by one word, not an isolated word.
- Prefer everyday repair, politeness, food, transport, self-introduction and
  autobiographical phrases that recombine in other situations.
- When the owner can use the language that day, select a phrase they can
  plausibly attempt in real conversation. Otherwise make the action a voice
  note, role-play, or spoken description (the spoken fallback). If
  location is unknown, give both action variants without asking a setup
  question.
- Vary situations while revisiting weak forms. Do not randomize unrelated words
  merely to call the lesson interleaved.
- Verify uncertain wording, register, grammar, pronunciation, or frequency
  against a trustworthy dictionary, grammar, or corpus. Do not browse routinely
  for settled beginner phrases.

## Target-language delivery

For Phrase + Echo lessons:

- Show standard target-language spelling and a natural English meaning.
- Mark stress by capitalizing the stressed syllable and give one useful sound
  cue. Avoid elaborate English respellings. In text or transcription, assess
  recall, spelling, and word choice; never claim to have evaluated the owner's
  accent or pronunciation.
- Teach one surface-form contrast inside its phrase. Do not lead with grammar
  tables.
- Use the formal register appropriately with strangers and explain it when it
  appears.
- Keep explanation subordinate to saying the phrase from memory.

## Output

```markdown
### {Language} · Session S · about 4 minutes

`Finalized: session {S-1} · new: {phrase ID or none} · result: {owner result or unknown}`

**Recall before opening**
1. {English situation prompt}

<details><summary>Reveal and check</summary>
{Correct sentence, then one concise correction if needed.}
</details>

**Today's anchor:** `{word}` — {meaning}

**Useful sentence:** `{Target-language sentence}`\
*{Natural English meaning}*

**Say it:** {stress guide and one sound cue}

**Echo:** Say it once while looking, then once from memory.

**Pattern:** {one inflection or register contrast}

**Do:** {one real-conversation action, or a spoken fallback}

`Receipt: session S · new: {phrase ID + phrase, or none} · reviewed: {actual phrase IDs or none} · result: pending`
```

On the first session, omit the finalized line, use a simple cold-start recall
such as an everyday greeting, and omit unavailable review indices. Treat that
warm-up as unscored and keep it out of the missed-phrase queue; the first result
uses `recalled 0/0`. Do not turn the receipts into a dashboard.
