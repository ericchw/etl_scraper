"""Generate Best Buy mapping YAML from category template CSV."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.categories import bestbuy_category_id, load_categories
from core.marketplace_templates import (
    ensure_mapping_yaml,
    load_csv_headers,
    migrate_legacy_templates,
    resolve_template_csv,
    write_yaml,
)

# Rich field rules maintained for CAT_1002 (laptops). Other categories get literal scaffold.
BASELINE_RULES_PATH = ROOT / "configs" / "marketplaces" / "bestbuy" / "CAT_1002.yaml"


def _baseline_fields() -> dict:
    if not BASELINE_RULES_PATH.exists():
        return {}
    with open(BASELINE_RULES_PATH, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data.get("fields") or {}


def generate_for_category(category_key: str, *, overwrite: bool = False) -> Path | None:
    # migrate_legacy_templates()
    cat_id = bestbuy_category_id(category_key)
    if not cat_id:
        print(f"Unknown category: {category_key}")
        return None

    template = resolve_template_csv(category_key, "bestbuy")
    if not template or not template.exists():
        print(f"Template missing: {template}")
        return None

    mapping = ROOT / "configs" / "marketplaces" / "bestbuy" / f"{cat_id}.yaml"
    if mapping.exists() and not overwrite:
        print(f"Exists (use --overwrite): {mapping}")
        return mapping

    headers = load_csv_headers(template, marketplace="bestbuy")
    if not headers:
        print(f"No headers in {template}")
        return None

    baseline = _baseline_fields() if cat_id == "CAT_1002" else {}
    fields: dict = {}
    for name in headers:
        fields[name] = baseline.get(name, {"literal": ""})

    rel_headers = f"../../../templates/bestbuy/{template.name}"
    data = {
        "marketplace": "bestbuy",
        "name": cat_id,
        "headers_file": rel_headers,
        "fields": fields,
    }
    write_yaml(mapping, data)
    print(f"wrote {len(headers)} fields → {mapping}")
    return mapping


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Best Buy YAML from template CSV")
    parser.add_argument(
        "--category",
        default="gaming_laptop",
        help="Internal category key from categories.json",
    )
    parser.add_argument("--all", action="store_true", help="Generate for all categories")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument(
        "--ensure-only",
        action="store_true",
        help="Only create if missing (literal scaffold)",
    )
    args = parser.parse_args()

    if args.ensure_only:
        keys = load_categories().keys() if args.all else [args.category]
        for key in keys:
            ensure_mapping_yaml(key, "bestbuy")
        return

    if args.all:
        for key in load_categories():
            generate_for_category(key, overwrite=args.overwrite)
    else:
        generate_for_category(args.category, overwrite=args.overwrite)


if __name__ == "__main__":
    main()
