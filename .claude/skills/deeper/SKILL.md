---
name: deeper
description: Turn a prompt into a deeper version of the same task, not a bigger one, by asking what a top professional would do, start from, use and check against. Invoke explicitly with $deeper or /deeper.
disable-model-invocation: true
---

# Deeper

Use this skill only for `$deeper` or `/deeper`. The input is a prompt: the
text after the command, or the last request in the conversation when none is
given. Make the task deeper, not bigger: same goal, same scope, better
practice.

Before rewriting the prompt, answer four questions about it:

1. **Missing practice.** What would a top professional in this field do here
   that the prompt does not ask for?
2. **Raw material.** What is the rawest material they would start from,
   instead of what has already been digested? Name the actual source: the
   data, the primary document, the log, the original code.
3. **Methods and tools.** Which specific methods and tools would they use?
4. **Outside proof.** What, other than the agent or the user, would show the
   result is right? Name a check, measurement, test, reviewer or source that
   could disagree.

Then interview the owner before rewriting: ask 2-3 short questions about the
decisions only they can make, such as goal, scope, tradeoffs or who judges the
result (AskUserQuestion in Claude Code; plain chat elsewhere), and wait for
their answers. Offer your recommended answer first. Rewrite the prompt from their answers so it asks for
exactly that, and open it with: "Before starting, ask me 2-3 questions about
decisions only I can make."

## Reply

- One short line per question, specific to this task. No generic advice.
- Ask the interview before showing the rewritten prompt.
- The rewritten prompt in a fenced `text` block, ready to paste.
- Do not run the rewritten prompt. The owner decides whether to send it.
- If the prompt is already deep, say so in one line, still interview the owner,
  and add only the opening line.
