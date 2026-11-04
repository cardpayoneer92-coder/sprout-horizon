# Adding products to Sprout

What the theme actually reads off a product, and what to put there.

## The fields that do something

| Field in Shopify | What the theme does with it |
| --- | --- |
| **Title** | Card, product page, cart, bundle, sticky bar. |
| **Handle** | Looks for a packaged shot at `assets/sp-<handle>-1.png` (and `-2.png` for the hover). A real photo always wins; the asset is only a stand-in. |
| **Media** | First image = card and gallery. **Second image = the hover image on cards.** Upload two and cards come alive. |
| **Type** | The small grey line under the card title. Keep it short — "Dog food", not "Gently cooked dog food 1.2kg". |
| **Tags** | Only `new` is read by the theme (it prints the "New" flag). Everything else feeds the collection filters. |
| **Price** | Card, product page, bundle, cart. |
| **Compare at price** | Shown struck through next to the price when it is higher. |
| **Inventory / availability** | Sold-out flag on the card, and the Add to bag button goes to "Sold out". |
| **Option 1 — name it `Size`** | Becomes the size pills on the product page. Price, compare-at and availability follow the pill you pick. |
| **Variants** | The one selected is what Add to bag and the sticky bar send. |

Not read at all: metafields, vendor, SKU, barcode, weight. Nothing breaks if they
are empty.

## The kinds of product the design is built for

The illustrations and the two product templates assume a pet shop with roughly
these shelves:

| Type | Example | Template |
| --- | --- | --- |
| Dog food | Chicken & pumpkin dinner | `product` |
| Cat food | Salmon pâté | `product` |
| Small pet food | Timothy hay bundle | `product` |
| Treats | Carrot crunch treats | `product` |
| Beds | Cloud bed | `product.gear` |
| Blankets | Waffle blanket | `product.gear` |
| Toys | Rope bone | `product.gear` |
| Bowls | Slow bowl | `product.gear` |
| Bundles | Puppy starter box | `product` |

**Pick the template on the product page**, under Theme template:

- `product` — food and treats. Eyebrow "Gently cooked · adult dog", the size
  finder is on, and the rows are Ingredients / Feeding guide / Delivery.
- `product.gear` — beds, blankets, toys, bowls. Eyebrow "Comfy things", no size
  finder, and the rows are Materials / Washing / Delivery.

Using the food template for a bed is the one mistake that looks wrong straight
away: it offers to work out a daily portion of bed.

## Tags worth using

The theme itself only needs `new`. The rest exist so the collection filters are
useful once Search & Discovery is set up:

- Pet: `dog`, `cat`, `puppy`, `small-pet`
- Shelf: `food`, `treats`, `beds`, `blankets`, `toys`, `bowls`, `bundles`
- Claims: `new`, `washable`, `non-toxic`, `bpa-free`, `single-protein`,
  `gently-cooked`

## Handles that already have artwork

These twelve have packaged shots sitting in `assets/`, so a product created with
the same handle shows a picture before anyone uploads one:

`beef-sweet-potato`, `carrot-crunch-treats`, `chicken-pate`,
`chicken-pumpkin-dinner`, `cloud-bed`, `hay-bundle`, `oat-herb-biscuits`,
`rope-bone`, `salmon-pate`, `slow-bowl`, `starter-box`, `waffle-blanket`

To add artwork for a new product, drop `sp-<handle>-1.png` and
`sp-<handle>-2.png` into `assets/` — 1200×1500, and the second one on a
different ground colour so the hover reads as a change.

## A sensible first product

```
Title              Chicken & Pumpkin Dinner
Handle             chicken-pumpkin-dinner
Type               Dog food
Tags               dog, food, new, gently-cooked
Option 1           Size → Small (1.2kg) / Medium (2.4kg) / Large (4kg)
Prices             18.00 / 32.00 / 48.00
Media              two images, pack shot first
Template           product
```
