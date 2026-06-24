# ETL Scraper — data flow and user guide

## Overview

```
GUI / CLI
   │
   ▼
Scrape (Playwright) ──► per-source raw blobs
   │
   ▼
Normalize per source (CDW / B&H / manufacturer)
   │
   ▼
Merge (field policies + winner per group) ──► internal schema
   │
   ▼
products/{MPN}.json   { mpn, scraped_data, internal, merge_report }
   │
   ▼
map_product(YAML) ──► output/exports/*.csv
```

**Canonical product file:** `products/{MPN}.json`

| Key | Purpose |
|-----|---------|
| `mpn` | Top-level MPN (from `internal.identity.mpn`) |
| `product_code` | Product family: `NB`, `MNT` (from category `code`; drives schema + normalizers) |
| `scraped_data` | Full per-site raw scrape blobs (`cdw`, `bh`, …). **Keep this** — you can rebuild `internal` without re-scraping. |
| `internal` | Normalized + merge-adjusted **default schema only** (no raw retailer spec tables). |
| `merge_report` | Which source won each group (`spec`, `content.features`, …). |

**Not stored in product JSON (by design):**

- `submission` — marketplace SKU, category, open box, etc. GUI/CLI panel at export time only.
- `internal.legacy_specs` — raw CDW/B&H group/key tables stay in `scraped_data.{source}.specs` only.
- `cache/` folder — not used by the pipeline; optional legacy copies only.

---

## Why `internal` was all null

Three issues (now fixed):

1. **Merge spec winner** — `_partial_has_spec` looked for `processor.cpu.model` (old shape). CDW partial uses `processor.model`, so spec winner was `"none"` and structured blocks were never copied.
2. **CDW normalizer** — threads used `Cores` instead of `Processor Main Features` + number extract (fixed).
3. **Stale internal** — loading an old `products/*.json` without rebuilding left empty `internal` even when `scraped_data.cdw.specs` was full.

**Fix:** Always rebuild with `build_product_document(scraped_data)` (GUI “use existing” and pipeline after scrape). Do not trust a saved `internal` block unless you just merged.

---

## Rebuild `internal` from `scraped_data` (recommended)

```python
from core.normalizer import build_product_document

product = load_json("products/58JKH.json")
doc = build_product_document(product["scraped_data"])
# doc["internal"] is fresh; doc["scraped_data"] unchanged
```

GUI: **Use existing scrape** → rebuilds from `products/{MPN}.json` → `scraped_data` only.

**internal vs scraped_data:** `scraped_data` is the source of truth for raw site JSON. `internal` is derived (normalize + priority merge into `core/schema/product.py`). Re-run `build_product_document(scraped_data)` after normalizer changes.

---

## Multi-path spec keys (same site, different labels)

Example: thread count on CDW:

| Spec path | Raw | Parsed |
|-----------|-----|--------|
| `Processor` → `Processor Main Features` | `22 Threads` | `22` |
| `Processor` → `Processor Main Features` | `14 Threads, Intel Smart Cache` | `14` |

Configured in `sites/cdw/spec_bindings.py` + `core/spec_lookup.resolve_spec_field()`:

- Several CDW group/key paths per internal field (e.g. threads).
- `prefer_keywords` (e.g. `"thread"`) picks the right path when more than one path has a number.
- Otherwise earlier path in the list wins.
- Resolved value only — nothing like `_field_sources` is stored in product JSON.

For export YAML that uses retailer `group`/`key`, `get_spec` reads `scraped_data` (CDW first, then B&H, manufacturer) — not `internal`.

---

## Where to edit what

| Goal | File |
|------|------|
| Scrape order / skip rules | `configs/merge_sources.json`, `core/merge_policy.py` |
| Merge priority (drag-drop in GUI) | `configs/merge_sources.json` — keys: `spec`, `packing`, `photo`, `features`, `design` |
| Download photos after scrape | Settings (⚙) → **Download product photos** → `configs/app_settings.json` |
| CDW → internal fields | `sites/cdw/normalizer.py` |
| B&H → internal fields | `sites/bh/normalizer.py` |
| Merge winners | `core/merge/field_merge.py` |
| Internal schema shape | `core/schema/product.py` |
| Best Buy / Newegg column mapping | `configs/marketplaces/{bestbuy,newegg}/*.yaml` |
| Category → YAML file | `configs/categories/categories.json` |
| CSV template + skip rows | `templates/{marketplace}`, `configs/marketplace_templates.json` |
| Marketplace export transforms | `core/transforms.py`, `core/mapping/engine.py` |

---

## Merge priorities (`configs/merge_sources.json`)

Example:

```json
{
  "spec": ["cdw", "bh", "manufacturer"],
  "packing": ["bh", "cdw", "manufacturer"],
  "photo": ["cdw", "bh", "manufacturer"],
  "features": ["bh", "cdw", "manufacturer"],
  "design": ["bh", "cdw", "manufacturer"]
}
```

- **spec** — One source wins the whole structured block (`processor`, `memory`, `display`, dimensions item, …). No union of CDW + B&H spec tables.
- **features** — Bullet list for short description export.
- **design** — Long `content.description` (B&H prose); heading added at export via YAML `design_heading`.
- **packing** — Package dimensions / weight.
- **photo** — First source with image URLs.

---

## Product JSON sample

```json
{
  "mpn": "58JKH",
  "scraped_data": {
    "cdw": { "source": "cdw", "mpn": "58JKH", "title": "...", "specs": { "Processor": { ... } } },
    "bh": { "source": "bh", "specs": { ... }, "description": "..." }
  },
  "internal": {
    "identity": { "brand": "Dell", "mpn": "58JKH", "model": "..." },
    "processor": { "threads": "22", "cores": "16", "model": "..." },
    "content": { "description": "...", "features": ["..."], "images": ["https://..."] }
  },
  "merge_report": {
    "spec": "cdw",
    "content.features": "bh",
    "content.description": "bh"
  }
}
```

---

## YAML field rules (samples)

Path: `configs/marketplaces/bestbuy/CAT_1002.yaml`

### From internal schema

```yaml
_Brand_Name_Category_Root_EN:
  from: identity.brand

_Model_Number_Category_Root_EN:
  from: identity.model
```

### From submission (GUI only at export)

```yaml
shop_sku:
  from_submission: sku

_Primary_UPC_Category_Root_EN:
  from_submission: upc
```

### From retailer spec table (`scraped_data` / CDW groups)

```yaml
_ProcessorType_3885_CAT_1002_EN:
  source:
    - group: Processor
      key: Processor Type
  transform: join_specs
  sources:
    - group: Processor
      key: Processor Number
```

`join_specs` needs `sources` in the rule (engine passes them into the transform).

### Internal path + spec fallback chain

```yaml
_Software_Platform_Category_Root_EN:
  sources:
    - path: software.platform
    - group: Product Information
      key: Platform Supported
    - group: Software
      key: Operating System Platform
```

### Transforms (features / design / images)

```yaml
_Short_Description_BB_Category_Root_EN:
  transform: export_features_bullets

_Long_Description_BB_Category_Root_EN:
  transform: long_description_bb
  design_heading: "Feature & Design:"

_MP_Source_Image_URL_01_Category_Root_EN:
  transform: scraped_image_url
  image_index: 1
```

### Category-driven YAML pick

```yaml
BBYCat:
  from_category:
    marketplace: bestbuy
```

Maps `submission.category` → `configs/categories/categories.json` → YAML filename.

---

## GUI workflow

1. Open **Settings (⚙)** — set source priority; optionally enable **Download product photos after scrape** (saves to `output/images/{MPN}/`).
2. Add row(s) in scrape queue (MPN, manufacturer, category, marketplaces).
3. **Run scrape** — writes cache + `products/{MPN}.json` with `scraped_data` + merged `internal`.
4. **Use existing** — rebuilds `internal` from `scraped_data` (or cache if no scraped_data); does not download photos.
5. **Export** — reads `products/{MPN}.json`, attaches panel `submission`, runs `map_product` per enabled marketplace.

Duplicate MPN rows: scrape once; export can run per row with different submission (e.g. open box).

---

## Commands (development)

```bash
# Rebuild one product from existing JSON
python -c "
from core.utils import load_json, save_json
from core.normalizer import build_product_document
p = load_json('products/58JKH.json')
doc = build_product_document(p['scraped_data'])
save_json(doc, 'products/58JKH.json')
print(doc['internal']['processor'])
"
```

---

## Design choice: scraped_data vs internal

| Layer | Role |
|-------|------|
| **`scraped_data`** | Raw per-site scrape (`specs`, `title`, `images`, …). Source of truth for rescrape-skip and YAML `get_spec`. |
| **`internal`** | Normalized default schema + merge winners only. Rebuilt from `scraped_data`. |
| **`submission`** | Never in product JSON; GUI row / CLI at export only. |

Old `cache/` copies can be deleted if `products/{MPN}.json` already has `scraped_data`.

---

## Long-term architecture (長遠)

Three layers — only the middle layer varies by **product family**, not by every UI label.

```
┌─────────────────────────────────────────────────────────────┐
│  scraped_data          NEVER category-specific              │
│  cdw / bh / manufacturer — full raw specs + content         │
│  (one scrape; fix normalizer later without re-scraping)     │
└──────────────────────────────┬──────────────────────────────┘
                               │ normalize + merge (product_code)
                               ▼
┌─────────────────────────────────────────────────────────────┐
│  internal              BY product_code (NB, MNT, …)         │
│  empty_internal(code) + site normalizer profiles            │
└──────────────────────────────┬──────────────────────────────┘
                               │ map_product (category_key)
                               ▼
┌─────────────────────────────────────────────────────────────┐
│  CSV export            BY marketplace + category_key          │
│  CAT_1002 vs CAT_1006 YAML; submission from GUI row only    │
└─────────────────────────────────────────────────────────────┘
```

### Two kinds of “category”

| Concept | Where | Examples | Changes when you add… |
|---------|--------|----------|---------------------|
| **`product_code`** | `categories.json` → `"code"` | `NB`, `MNT` | New **product type** (laptop vs monitor) |
| **`category_key`** | GUI combo `userData` | `gaming_laptop`, `monitor` | New **listing** on same BB/Newegg template |

- `gaming_laptop` + `business_laptop` → both `NB` → **same** `internal` schema, **same** CDW normalizer profile, **same** `CAT_1002.yaml`.
- `monitor` → `MNT` → **different** schema + normalizer + `CAT_1006.yaml`.

Do **not** fork scrape or `empty_internal` per `gaming_laptop` / `business_laptop`.

### What to store in `products/{MPN}.json`

| Field | Long-term |
|-------|-----------|
| `scraped_data` | Always; source of truth |
| `internal` | Derived; rebuilt with `product_code` |
| `product_code` | Recommended (`NB` / `MNT`) so rebuild does not need GUI |
| `merge_report` | Keep |
| `submission` | Never |
| `cache/` | Not used |

### Normalizers (long-term layout)

```
sites/cdw/
  spec_bindings.py      # path lists + prefer_keywords (per family)
  normalize_nb.py       # laptop profile  → internal
  normalize_mnt.py      # monitor profile → internal
  __init__.py           # normalize_cdw_raw(raw, product_code="NB")

sites/bh/
  normalize_nb.py       # packing + content for laptops
  normalize_mnt.py      # display/packaging for monitors (when needed)
```

- **Scrape JS/API** stays one per site; it always pulls full `specs`.
- **Normalize** chooses which spec groups map into `internal` for that `product_code`.

### UI flow (target)

1. User picks **Category** on the row (as now).
2. **Run scrape** → resolve `product_code` from `categories.json` → normalize with that code → save JSON with `product_code`.
3. **Export** → same row’s `category_key` → YAML + submission (price, open box, SKU).

Changing only export settings (open box, price) never requires rescrape.

### Phased rollout

| Phase | Status |
|-------|--------|
| `product_code` on product JSON + `configs/schemas/{NB,MNT}.json` | **Done** |
| `normalize_cdw_raw` / `normalize_bh_raw(..., product_code)` | **Done** (NB + MNT profiles) |
| GUI job passes `product_code` from category `code` | **Done** |
| `CAT_1006.yaml` monitor export mapping | Later |
| GUI schema preview on category change | Later |

### Adding a new product family (e.g. `DSK` desktop)

1. Add `categories.json` entry with `"code": "DSK"`.
2. Add `configs/schemas/DSK.json`.
3. Add `sites/cdw/normalize_dsk.py` + `spec_bindings`.
4. Register in `build_product_document(..., product_code=...)`.
5. Add marketplace YAML/templates when export is ready.

Scrape code unchanged until a **new retailer page shape** appears — that is rare compared to new internal fields.

---

## Adding a new internal field

1. Add default in `core/schema/product.py` → `empty_internal()`.
2. Map it in `sites/cdw/normalizer.py` (and B&H if needed).
3. Ensure `field_merge._apply_spec_block` copies the dict key (top-level dict blocks on spec winner are copied automatically).
4. Reference in marketplace YAML via `from: path.to.field` or `source: group/key`.

---

## Troubleshooting

| Symptom | Check |
|---------|--------|
| Export spec column empty | `scraped_data.cdw.specs` (or B&H); YAML `source` group/key names |
| `internal.processor` empty | Run rebuild; confirm `merge_report.spec` is `cdw` not `none` |
| Wrong thread count | `Processor Main Features` path list in CDW normalizer |
| Long description missing heading | YAML `design_heading` on long-description field only |
| Images wrong source | `merge_report["content.images"]` vs `merge_sources.json` `photo` order |
