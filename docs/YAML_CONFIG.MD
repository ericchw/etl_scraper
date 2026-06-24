# Marketplace mapping YAML (`configs/marketplaces/**/*.yaml`)

Rules in these files drive `map_product()` in `core/mapping/engine.py`. Each **field** under `fields:` is resolved by `_resolve_rule()`:

```
literal / from / sources / from_submission / …
  → when (optional)
  → transform (optional)
  → pipeline (optional)
  → template (optional)
  → format (type, default)
  → validate (allowed)
```

See also [PRODUCT_FLOW.md](./PRODUCT_FLOW.md) for scrape → internal → export flow.

---

## Unified `sources` (use this for all data lookups)

**Always use `sources:`** — not `source`, `sources_first`, or `sources_join` (those still work as legacy aliases but should not be used in new YAML).

Each entry in `sources` is one lookup. Supported entry shapes:

| Shape | Example | Resolves to |
|-------|---------|-------------|
| Internal path list | `["internal", "memory", "capacity_gb"]` | `internal.memory.capacity_gb` |
| Dot path (dict) | `path: software.platform` | `internal.software.platform` |
| Path list (dict) | `path: ["internal", "memory", "type"]` | same as list form |
| Retailer spec | `group: Processor` + `key: Model` | scraped spec table (CDW/B&H winner) |
| Legacy 2-list spec | `["Processor", "Model"]` | same as group/key |

Per-entry options (dict entries only):

- `suffix` / `prefix` — applied to that entry’s value before rule-level join
- `join` — when that entry’s value is a **list**, join items with this separator (e.g. `DDR5/DDR4`)

Rule-level options:

| Key | Purpose |
|-----|---------|
| `mode: first` | First non-empty entry wins (default when **no** `join`) |
| `join: "…"` | Join mode: combine all non-empty entries (if only one value, return it alone) |
| `list_join` | Join separator for **list field values** when `join` is used for multi-source (see ports example) |
| `suffix` / `prefix` | Applied to the **final** resolved string |
| `filter_include_keywords` | Keep list items / scalar text only if any keyword matches (case-insensitive) |
| `filter_exclude_keywords` | Drop list items / scalar text if any keyword matches |

### Empty values (skipped automatically)

`None`, `""`, `0`, `[]`, `{}` — treated as missing so the next source or join part is skipped.

---

## Patterns (from production fields)

### 1. First fallback (package → item dimensions)

Try package size first; if empty, use item size.

```yaml
Item Width:
  sources:
    - ["internal", "physical", "dimensions", "package", "width_in"]
    - ["internal", "physical", "dimensions", "item", "width_in"]
```

No `join` → `mode: first` (implicit).

### 2. Join multiple fields (`cells x chemistry`)

Join non-empty parts. Single part stays a plain string (no extra separator).

```yaml
_BatteryType_4662_CAT_1002_EN:
  sources:
    - ["internal", "power", "battery", "cells"]
    - ["internal", "power", "battery", "chemistry"]
  join: " x "
```

Examples: `6 x Lithium-ion` · `6` (only cells) · `Lithium-ion` (only chemistry).

### 3. List field + filter + join (other ports)

`ports` is a list on `internal`. Filter each item, then join survivors.

```yaml
_OtherInputorOutputPorts_24708_CAT_1002_EN:
  sources:
    - ["internal", "io", "ports"]
  filter_exclude_keywords:
    - hdmi
    - displayport
    - usb
    - ethernet
  join: ", "
```

Use `list_join` when you need a different separator for list items than for multi-source join:

```yaml
_WhatsintheBox_4667_CAT_1002_EN:
  sources:
    - ["internal", "included_items"]
  list_join: ";"
```

### 4. Per-entry suffix + join (memory speed)

```yaml
NBMemorySpeed:
  sources:
    - path: ["internal", "memory", "configuration_features"]
    - path: ["internal", "memory", "rated_speed_mhz"]
      suffix: " MHz"
    - path: ["internal", "memory", "type"]
      join: "/"
  join: " "
```

Result example: `Dual Channel 5600 MHz DDR5`.

### 5. Merge sources for `keyword_map` (software platform)

Combine all platform hints, then normalize and map.

```yaml
_Software_Platform_Category_Root_EN:
  sources:
    - path: software.platform
    - group: Product Information
      key: Platform Supported
    - group: Software
      key: Operating System Platform
  join: " "
  pipeline:
    - normalize_whitespace
    - uppercase
    - keyword_map:
        WINDOWS: [WINDOWS, WIN, MICROSOFT WINDOWS]
        ANDROID: [ANDROID, GOOGLE ANDROID]
        MAC: [MAC, MACOS, OSX]
  allowed: ["", "WINDOWS", "ANDROID", "MAC"]
```

### 6. Transform + pipeline (BB title)

Transform builds the title from context; pipeline edits the result.

```yaml
_Title_BB_Category_Root_EN:
  transform: bb_title
  pipeline:
    - replace:
        " - ": ", "
```

`bb_title` reads `context.title`, `context.mpn`, and `context.condition` (string or `{label, key}` dict).

### 7. Scalar source + suffix

```yaml
NBScreenSize:
  sources:
    - ["internal", "display", "size_in"]
  suffix: ' "'
```

### 8. Other rule types (no `sources`)

```yaml
shop_sku:
  from_submission: sku

_Brand_Name_Category_Root_EN:
  from: identity.brand

BBYCat:
  from_category:
    marketplace: bestbuy

_Activation Mark:
  literal: "TRUE"
```

---

## Pipeline steps

String steps: `uppercase`, `lowercase`, `trim`, `normalize_whitespace`

Dict steps:

- `replace: { "old": "new" }`
- `keyword_map: { CANONICAL: [alias, …] }`
- `join: ", "` (when current value is a list)
- `transform: some_transform` (named transform from `core/transforms.py`)
- `unit_convert: { from: cm, to: in }`

---

## Conditions (`when`)

```yaml
when:
  - field: submission.condition
    op: eq
    value: refurbished
    else: ""
```

`submission.condition` may be a string (`open_box`) or object (`{ "key": "open_box", "label": "Open Box" }`).

---

## Deprecated

- `source:` → use `sources:` with one entry
- `sources_first` / `sources_join` → use `sources` + `mode: first` or `join`
- `transform: join_specs` → use `sources` + `join: " "` (or another separator)

Implementation: `core/mapping/sources.py`
