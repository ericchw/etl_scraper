"""Generate Best Buy / Newegg mapping YAML from template CSV (skip existing by default)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from core.categories import (
    bestbuy_category_id,
    load_categories,
    mapping_path,
    marketplace_code,
    newegg_suffix,
)
from core.marketplace_templates import (
    load_csv_headers,
    load_csv_preamble_row,
    resolve_template_csv,
    scaffold_yaml_dict,
    write_yaml,
)

ROOT = Path(__file__).resolve().parent.parent
BASELINE_BESTBUY_RULES = ROOT / "configs" / "marketplaces" / "bestbuy" / "CAT_1002.yaml"


@dataclass
class GenerateResult:
    category_key: str
    marketplace: str
    mapping_path: Path | None
    status: str  # created | skipped_exists | overwritten | error
    message: str
    field_count: int = 0


def _baseline_bestbuy_fields() -> dict:
    if not BASELINE_BESTBUY_RULES.exists():
        return {}
    with open(BASELINE_BESTBUY_RULES, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data.get("fields") or {}


def resolve_category_key(value: str, marketplace: str) -> str | None:
    """Resolve internal category key from key, Best Buy CAT id, or Newegg suffix/batch name."""
    needle = (value or "").strip()
    if not needle:
        return None

    cats = load_categories()
    if needle in cats:
        return needle

    marketplace = marketplace.strip().lower()
    if marketplace == "bestbuy":
        for key, entry in cats.items():
            if str(entry.get("bestbuy", "")).strip() == needle:
                return key

    if marketplace == "newegg":
        batch_prefix = "ComputerHardware_BatchItemCreation_"
        for key, entry in cats.items():
            suffix = str(entry.get("newegg", "")).strip()
            batch = marketplace_code(key, "newegg")
            if needle in {suffix, batch, f"{batch_prefix}{suffix}"}:
                return key

    return None


def generate_mapping_yaml(
    category_key: str,
    marketplace: str,
    *,
    overwrite: bool = False,
    use_bestbuy_baseline: bool = True,
) -> GenerateResult:
    marketplace = marketplace.strip().lower()
    mapping = mapping_path(category_key, marketplace)
    template_csv = resolve_template_csv(category_key, marketplace)

    if not mapping:
        return GenerateResult(
            category_key=category_key,
            marketplace=marketplace,
            mapping_path=None,
            status="error",
            message=f"No mapping path for category {category_key!r} / {marketplace}",
        )

    if not template_csv or not template_csv.exists():
        return GenerateResult(
            category_key=category_key,
            marketplace=marketplace,
            mapping_path=mapping,
            status="error",
            message=f"Template CSV missing: {template_csv}",
        )

    existed = mapping.exists()
    if existed and not overwrite:
        return GenerateResult(
            category_key=category_key,
            marketplace=marketplace,
            mapping_path=mapping,
            status="skipped_exists",
            message=f"Already exists (not replaced): {mapping.name}",
        )

    headers = load_csv_headers(template_csv, marketplace=marketplace)
    if not headers:
        return GenerateResult(
            category_key=category_key,
            marketplace=marketplace,
            mapping_path=mapping,
            status="error",
            message=f"No headers in template: {template_csv.name}",
        )

    baseline = {}
    if marketplace == "bestbuy" and use_bestbuy_baseline:
        cat_id = bestbuy_category_id(category_key)
        if cat_id == "CAT_1002":
            baseline = _baseline_bestbuy_fields()

    fields: dict = {}
    for name in headers:
        fields[name] = baseline.get(name, {"literal": ""})

    rel_headers = f"../../../templates/{marketplace}/{template_csv.name}"
    preamble = (
        load_csv_preamble_row(template_csv)
        if marketplace == "newegg"
        else None
    )
    name = mapping.stem
    if marketplace == "newegg" and not name:
        name = newegg_suffix(category_key)

    data = scaffold_yaml_dict(
        marketplace=marketplace,
        name=name,
        headers=headers,
        headers_file=rel_headers,
        csv_preamble_row=preamble or None,
    )
    data["fields"] = fields

    write_yaml(mapping, data)
    status = "overwritten" if existed else "created"
    return GenerateResult(
        category_key=category_key,
        marketplace=marketplace,
        mapping_path=mapping,
        status=status,
        message=f"Wrote {len(headers)} fields → {mapping.name}",
        field_count=len(headers),
    )


def generate_all_missing(
    marketplace: str,
    *,
    overwrite: bool = False,
) -> list[GenerateResult]:
    results: list[GenerateResult] = []
    for category_key in load_categories():
        results.append(
            generate_mapping_yaml(category_key, marketplace, overwrite=overwrite)
        )
    return results
