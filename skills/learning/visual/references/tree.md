# Tree Mode

Use this for focused implementation tree plans, not full architecture diagrams.
The output is a pruned directory tree showing only relevant files and
directories. Every included path should help the user decide what will be added,
modified, inspected, generated, or intentionally ignored.

## Workflow

1. Identify the planned root directory from the user's request or repo context.
2. Read the smallest relevant layer of the repo before naming existing paths.
3. Prune unrelated siblings, caches, dependency folders, generated bulk output,
   and broad "maybe" paths.
4. Mark intended action in terse annotations:
   - `add:` new file, directory, ignore rule, generated artifact, or fixture.
   - `modify:` existing file to change.
   - `read:` existing file that informs the plan but should not change.
   - `ignore:` path pattern to exclude when that matters to the plan.
5. Use `...` only for repeated generated files or intentionally elided peer
   files. Do not hide required source files behind `...`.
6. Add no prose unless the user needs a short note after the tree.

## Output Shape

```text
<root>/
├── <existing-file>
│   └── modify: <terse reason>
├── <new-dir>/
│   ├── <new-file>
│   │   └── add: <terse reason>
│   └── <existing-file>
│       └── read: <terse reason>
└── <generated-dir>/
    └── ...
```

## Rules

- Keep annotations under one short line.
- Prefer concrete relative paths over categories.
- Do not include full repo trees unless the user explicitly asks.
- Do not invent files when existing repo conventions point to a better owner.
