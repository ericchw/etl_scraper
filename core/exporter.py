"""Write marketplace CSV exports."""

from __future__ import annotations

import csv
from pathlib import Path

from core.marketplace_templates import ensure_mapping_yaml
from core.mapper import map_product
from core.conditions import resolve_condition
from core.paths import safe_path_component

ROOT = Path(__file__).resolve().parent.parent


# ------------------------------------------------------------
# Condition handling
# ------------------------------------------------------------

def condition_suffix(submission: dict) -> str:
    key = submission.get("condition")

    cond = resolve_condition(key)

    suffix_list = cond.get("suffix") or []
    return suffix_list[0] if suffix_list else ""

# ------------------------------------------------------------
# Output path
# ------------------------------------------------------------

def export_output_path(
    marketplace: str,
    mpn_key: str,
    *,
    submission: dict,
) -> Path:
    marketplace = safe_path_component(marketplace)
    mpn_key = safe_path_component(mpn_key)
    name = f"{marketplace}_{mpn_key}.csv"

    suffix = condition_suffix(submission)

    if suffix:
        stem = name.removesuffix(".csv")
        name = f"{stem}{suffix}.csv"

    return ROOT / "output" / "exports" / safe_path_component(name)


# ------------------------------------------------------------
# CSV helpers
# ------------------------------------------------------------

def load_headers(headers_path: Path, *, marketplace: str) -> list[str]:
    from core.marketplace_templates import load_csv_headers
    return load_csv_headers(headers_path, marketplace=marketplace)


def export_csv(
    product: dict,
    *,
    mapping_path: Path,
    headers_path: Path,
    output_path: Path,
    marketplace: str,
) -> tuple[Path, list[str]]:

    row, warnings = map_product(product, mapping_path)

    headers = load_headers(headers_path, marketplace=marketplace)

    from core.marketplace_templates import resolve_csv_preamble_row

    preamble = resolve_csv_preamble_row(
        mapping_path, headers_path, marketplace,
    )
    if preamble is not None and len(preamble) < len(headers):
        preamble = preamble + [""] * (len(headers) - len(preamble))

    output_path.parent.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------
    # 🔥 ONLY inject EHF for BestBuy
    # ------------------------------------------------------------
    if marketplace in ["bestbuy"]:
        for k in row.keys():
            if k.startswith("ehf-amount-") and k not in headers:
                headers.append(k)

    # ------------------------------------------------------------
    # IMPORTANT: DO NOT reorder existing headers
    # ------------------------------------------------------------

    # with open(output_path, "w", encoding="utf-8-sig", newline="") as f:
    if marketplace == "newegg":
        encoding = "utf-8"
    else:
        encoding = "utf-8-sig"

    with open(output_path, "w", encoding=encoding, newline="") as f:
        if preamble is not None:
            csv.writer(f).writerow(preamble)

        writer = csv.DictWriter(
            f,
            fieldnames=headers,
            extrasaction="ignore",
        )

        writer.writeheader()
        writer.writerow(row)

    return output_path, warnings


# ------------------------------------------------------------
# BestBuy export
# ------------------------------------------------------------

def resolve_bestbuy_paths(product: dict, *, log=print) -> tuple[Path, Path]:
    submission = product.get("submission") or {}
    category_key = submission.get("category") or "gaming_laptop"

    mapping, template_csv, _ = ensure_mapping_yaml(category_key, "bestbuy", log=log)

    if not mapping or not template_csv:
        raise FileNotFoundError(
            f"Missing Best Buy mapping/template for category {category_key!r}"
        )

    if not template_csv.exists():
        raise FileNotFoundError(f"Template CSV not found: {template_csv}")

    return mapping, template_csv


def export_bestbuy_laptop(
    product: dict,
    *,
    log=print,
) -> tuple[Path, list[str]]:
    mpn_key = (product.get("mpn") or "product").strip()
    submission = product.get("submission") or {}

    output_path = export_output_path(
        "bestbuy",
        mpn_key,
        submission=submission,
    )

    mapping, headers = resolve_bestbuy_paths(product, log=log)

    return export_csv(
        product,
        mapping_path=mapping,
        headers_path=headers,
        output_path=output_path,
        marketplace="bestbuy",
    )


# ------------------------------------------------------------
# Newegg export
# ------------------------------------------------------------

def resolve_newegg_paths(product: dict, *, log=print) -> tuple[Path, Path]:
    submission = product.get("submission") or {}
    category_key = submission.get("category") or "gaming_laptop"

    mapping, template_csv, _ = ensure_mapping_yaml(category_key, "newegg", log=log)

    if not mapping or not template_csv:
        raise FileNotFoundError(
            f"Missing Newegg mapping/template for category {category_key!r}"
        )

    if not template_csv.exists():
        raise FileNotFoundError(f"Template CSV not found: {template_csv}")

    return mapping, template_csv


def export_newegg(
    product: dict,
    *,
    log=print,
) -> tuple[Path, list[str]]:
    mpn_key = (product.get("mpn") or "product").strip()
    submission = product.get("submission") or {}

    output_path = export_output_path(
        "newegg",
        mpn_key,
        submission=submission,
    )

    mapping, headers = resolve_newegg_paths(product, log=log)

    return export_csv(
        product,
        mapping_path=mapping,
        headers_path=headers,
        output_path=output_path,
        marketplace="newegg",
    )
