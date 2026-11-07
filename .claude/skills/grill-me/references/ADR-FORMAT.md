# ADR Format

ADRs live in `docs/adr/` unless the repository already declares another
location. When `GLOSSARY-MAP.md` declares multiple contexts, put system-wide
decisions in the root `docs/adr/` and context-specific decisions in the local
`docs/adr/` beside that context's `GLOSSARY.md`. Number ADRs sequentially as
`NNNN-slug.md`; create the directory only when the first qualifying decision
resolves.

## Minimal template

```md
# {Short decision title}

{In one to three sentences: the context, decision, and why.}
```

Optional status, alternatives, or consequences sections belong only when they
add material information.

## Qualification gate

Offer an ADR only when all three are true:

1. Reversing the decision later would be meaningfully costly.
2. A future reader would find the choice surprising without context.
3. The choice resolved a real tradeoff among credible alternatives.

Typical qualifying decisions include architectural shape, integration
boundaries, high-lock-in technology, ownership boundaries, deliberate
deviations from an obvious path, non-code constraints, and non-obvious rejected
alternatives. Skip easy-to-reverse or self-evident choices.
