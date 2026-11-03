# Sprout — pet store theme

A Shopify theme on the **Horizon** base. Brand: cute, minimal, green and sweet.
Design canvas: the "Sprout — pet store" artifact (home, product, collection,
mobile, cart drawer, brand sheet).

## Conventions

- Everything we add is prefixed **`sp-`**; private blocks are `_sp-`.
  Nothing in this theme uses the `cc-` prefix (that is the Sera theme).
- Shared tokens live in `snippets/sp-base.liquid` — colours, fonts, radii,
  motion. Sections read them, they do not redefine them.
- Every section and block is editor-customizable: no hard-coded copy that a
  merchant would want to change.

## Brand tokens

| Token | Value |
| --- | --- |
| Cream (ground) | `#fbf7ef` |
| Mint (surface) | `#e7f0e2` |
| Leaf | `#6fa368` |
| Moss (primary) | `#3f6b4a` |
| Peach (accent) | `#f3c3a0` |
| Ink | `#27372b` |

Headings **Fredoka 500**, body **Nunito 400/700**. Corners stay round:
pills for buttons, 28px cards, blobs behind illustrations — never behind text.

## Before every push

```bash
python3 tools/sp_validate.py
```

It catches the schema mistakes Shopify's GitHub sync rejects **silently** — a
rejected file simply never appears in the theme, with no error anywhere:

- a section schema with `"tag": null` (that is a block-only thing)
- a `range` with fewer than 2 steps, e.g. `min 2, max 3, step 1` → use a `select`
- a `range` default that is off the step grid
- a `unit` that is not a short plain token (`/1000em` was rejected; `px`, `%`, `sec` are fine)
- the reserved setting id `per_page`
- malformed JSON in a template or section group

## Push order

Shopify syncs changed files only, and a template referring to a section that is
not in the theme yet is rejected. So:

1. `snippets/sp-base.liquid` and any new sections/blocks → push, **wait ~2 min**
2. `templates/*.json` → separate commit
3. `sections/*-group.json` (header, footer) → last

Section group files keep their generated `/* ... */` header, and must not name a
menu handle that does not exist in the store — that silently rejects the file.
