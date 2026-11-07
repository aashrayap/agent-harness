# GLOSSARY.md Format

## Structure

```md
# {Context Name}

{One or two sentences describing what this context is and why it exists.}

## Language

**Order**:
{A one or two sentence definition}
_Avoid_: Purchase, transaction
```

Definitions say what a domain concept is, not how it is implemented. Include
only project-specific concepts, choose one canonical term, list misleading
synonyms under `_Avoid_`, and group terms only when natural clusters emerge.

## Single and multiple contexts

- A single-context repository uses one root `GLOSSARY.md`.
- A multi-context repository uses a root `GLOSSARY-MAP.md` that links each
  context's `GLOSSARY.md` and states the relationships between contexts.
- If neither file exists, create a root `GLOSSARY.md` only when the first term
  resolves. If `GLOSSARY-MAP.md` exists, use it to select the target glossary;
  ask one question when the target remains ambiguous.

Example map:

```md
# Glossary Map

## Contexts

- [Ordering](./src/ordering/GLOSSARY.md) — receives and tracks customer orders
- [Billing](./src/billing/GLOSSARY.md) — generates invoices and processes payment

## Relationships

- **Ordering → Billing**: Ordering emits `OrderPlaced`; Billing consumes it.
```
