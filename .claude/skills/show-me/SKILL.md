---
name: show-me
description: Explain the current topic on explicit request with the smallest useful inline diagram, code-shape sketch, or diff.
disable-model-invocation: true
---

# Show Me

Use this skill only for `$show-me` or `/show-me`. Help the user understand the
current topic visually. Skip the preamble, keep prose brief, and pick the
smallest view that makes the key point clear.

Use `explain` for a deeper structured explanation. Use `visual` when the user
wants a durable or editable artifact. `show-me` is the fast, lightweight path
for making the current discussion concrete.

- Show logic or an algorithm as pseudocode:

```text
on(save)
  if content is unchanged
    return cached result
  write new content
  return fresh result
```

- Show runtime control flow as a call tree:

```text
submitForm
  createSession
    persistPrompt
    launchAgent
  navigateToSession
```

- Show UI structure as a component tree, including only state and module
  boundaries that matter:

```tsx
<SessionPage> (apps/example/src/routes/session.tsx)
  useSessionEvents()
  <SessionToolbar>
    <RunSkillButton> (packages/ui)
```

- Show file responsibility or a broad refactor as a shallow file tree:

```text
src/
├── commands/       # parses user actions
├── sessions/       # owns session state
└── transport/      # sends API requests
```

- Show component interaction, control flow, or data flow as a rendered inline
  diagram where the client supports it (show_widget in the Claude desktop
  app), otherwise a labeled text tree:

```text
User ── choose command ──▶ UI
UI ── send expanded prompt ──▶ Daemon
Daemon ── stream result ──▶ UI
```

- Use a `diff` when the point is what changes and the surrounding shape already
  exists. Match the diff shape to the topic:

```diff
 <SessionPage>
   useSessionEvents()
   <SessionToolbar>
+    <RunSkillButton />
   <SessionTimeline>
+    <SkillResultCard />
```

```diff
 on(save)
-  write content
+  if content is unchanged
+    return cached result
+  write new content
+  invalidate cache
```

- Show the whole block when most of it is new, omitted context would hide
  ownership or order, or the user needs a copyable target shape:

```ts
function expandSkill(command: string): string {
  const skillName = command.slice(1)
  return `use the ${skillName} skill`
}
```

- If the topic is too dense for an inline view, stop and suggest the exact
  `$visual` invocation the user can run next. Do not create an HTML or durable
  artifact from `show-me`; `visual` owns that separate user-invoked workflow.

Place each visual next to the short text it supports. Keep only the calls,
files, props, states, and boundaries needed for the current question. Use one
or several formats as needed, but do not overwhelm the user.
