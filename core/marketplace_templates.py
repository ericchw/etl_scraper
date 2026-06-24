"""Resolve marketplace CSV/Excel templates and auto-generate YAML mappings."""

from __future__ import annotations

import csv
import json
import shutil
from pathlib import Path

import yaml

from core.categories import (
    bestbuy_category_id,
    mapping_path,
    marketplace_code,
    newegg_suffix,
)

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_CONFIG_PATH = ROOT / "configs" / "marketplace_templates.json"

_DEFAULT_TEMPLATE_CFG: dict[str, dict] = {
    "bestbuy": {"csv_skip_rows": 0},
    "newegg": {"csv_skip_rows": 1},
}


def load_marketplace_template_config() -> dict[str, dict]:
    if not TEMPLATE_CONFIG_PATH.exists():
        return dict(_DEFAULT_TEMPLATE_CFG)
    with open(TEMPLATE_CONFIG_PATH, encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        return dict(_DEFAULT_TEMPLATE_CFG)
    merged = dict(_DEFAULT_TEMPLATE_CFG)
    for key, value in data.items():
        if isinstance(value, dict):
            merged[key] = {**merged.get(key, {}), **value}
    return merged


def template_csv_skip_rows(marketplace: str) -> int:
    """Rows to skip before the header row (0-based index of header = skip_rows)."""
    entry = load_marketplace_template_config().get(marketplace, {})
    try:
        return max(0, int(entry.get("csv_skip_rows", 0)))
    except (TypeError, ValueError):
        return 0


def templates_root(marketplace: str, kind: str = "csv") -> Path:
    return ROOT / "templates" / marketplace / kind


def resolve_template_csv(category_key: str, marketplace: str) -> Path | None:
    if marketplace == "bestbuy":
        cat_id = bestbuy_category_id(category_key)
        if not cat_id:
            return None
        candidates = [
            templates_root("bestbuy", "csv") / f"{cat_id}.csv",
            ROOT / "templates" / "bestbuy" / f"{cat_id}.csv",
            ROOT / "templates" / "bestbuy" / f"{cat_id}-example.csv",
        ]
        for path in candidates:
            if path.exists():
                return path
        return candidates[0]

    if marketplace == "newegg":
        batch_name = marketplace_code(category_key, "newegg")
        if not batch_name:
            return None
        candidates = [
            templates_root("newegg", "csv") / f"{batch_name}.csv",
            ROOT / "templates" / "newegg" / f"{batch_name}.csv",
            templates_root("newegg", "csv") / f"{newegg_suffix(category_key)}.csv",
        ]
        for path in candidates:
            if path.exists():
                return path
        return candidates[0]

    return None


def resolve_template_excel(category_key: str, marketplace: str) -> Path | None:
    if marketplace == "bestbuy":
        cat_id = bestbuy_category_id(category_key)
        if cat_id:
            path = templates_root("bestbuy", "excel") / f"{cat_id}.xlsx"
            if path.exists():
                return path
    if marketplace == "newegg":
        batch_name = marketplace_code(category_key, "newegg")
        if batch_name:
            path = templates_root("newegg", "excel") / f"{batch_name}.xlsx"
            if path.exists():
                return path
    return None


def _marketplace_from_path(path: Path) -> str | None:
    parts = {p.lower() for p in path.parts}
    if "newegg" in parts:
        return "newegg"
    if "bestbuy" in parts:
        return "bestbuy"
    return None


def load_csv_preamble_row(path: Path) -> list[str]:
    """First CSV row (e.g. Newegg Version/SubCategoryID); trims trailing empty cells."""
    if not path.exists():
        return []
    with open(path, encoding="utf-8", newline="") as f:
        row = next(csv.reader(f), None)
    if not row:
        return []
    cells = list(row)
    while cells and cells[-1] == "":
        cells.pop()
    return cells


def resolve_csv_preamble_row(
    mapping_path: Path,
    headers_path: Path,
    marketplace: str,
) -> list[str] | None:
    """Preamble from mapping YAML, else from template CSV for Newegg."""
    if mapping_path.exists():
        with open(mapping_path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        raw = data.get("csv_preamble_row")
        if isinstance(raw, list) and raw:
            return ["" if c is None else str(c) for c in raw]
    if marketplace == "newegg":
        cells = load_csv_preamble_row(headers_path)
        return cells if cells else None
    return None


def load_csv_headers(
    path: Path,
    *,
    marketplace: str | None = None,
    skip_rows: int | None = None,
) -> list[str]:
    """Read column headers; skip_rows from config when not passed (see marketplace_templates.json)."""
    if not path.exists():
        return []
    marketplace = marketplace or _marketplace_from_path(path)
    if skip_rows is None:
        skip_rows = template_csv_skip_rows(marketplace) if marketplace else 0

    # with open(path, encoding="utf-8-sig", newline="") as f:
    with open(path, encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        for row_index, row in enumerate(reader):
            if row_index < skip_rows:
                continue
            cells = [c.strip() for c in row if c.strip()]
            if not cells:
                continue
            return [c for c in cells if not c.startswith("ehf-amount-")]
    return []


def scaffold_yaml_dict(
    *,
    marketplace: str,
    name: str,
    headers: list[str],
    headers_file: str,
    csv_preamble_row: list[str] | None = None,
) -> dict:
    data: dict = {
        "marketplace": marketplace,
        "name": name,
        "headers_file": headers_file,
    }
    if csv_preamble_row:
        data["csv_preamble_row"] = csv_preamble_row
    data["fields"] = {h: {"literal": ""} for h in headers}
    return data


def write_yaml(path: Path, data: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True)
    return path


def ensure_mapping_yaml(
    category_key: str,
    marketplace: str,
    *,
    log=print,
) -> tuple[Path | None, Path | None, bool]:
    """
    Ensure configs/marketplaces/{m}/{id}.yaml exists.

    Returns (mapping_path, template_csv_path, created_yaml).
    """
    mapping = mapping_path(category_key, marketplace)
    template_csv = resolve_template_csv(category_key, marketplace)
    if not mapping or not template_csv:
        return mapping, template_csv, False

    if mapping.exists():
        return mapping, template_csv, False

    headers = load_csv_headers(template_csv, marketplace=marketplace)
    if not headers:
        log(f"No template headers at {template_csv} — cannot generate YAML")
        return mapping, template_csv, False

    name = mapping.stem
    rel_headers = f"../../../templates/{marketplace}/{template_csv.name}"
    preamble = (
        load_csv_preamble_row(template_csv)
        if marketplace == "newegg"
        else None
    )
    data = scaffold_yaml_dict(
        marketplace=marketplace,
        name=name,
        headers=headers,
        headers_file=rel_headers,
        csv_preamble_row=preamble or None,
    )
    write_yaml(mapping, data)
    log(f"Generated mapping -> {mapping}")
    return mapping, template_csv, True


def save_downloaded_template(
    source_path: Path,
    *,
    marketplace: str,
    filename: str | None = None,
    kind: str | None = None,
) -> Path:
    """
    Store a downloaded marketplace template under templates/{marketplace}/{csv|excel}/.

    kind is inferred from extension when omitted (.csv → csv, .xlsx/.xls → excel).
    """
    source_path = Path(source_path)
    ext = source_path.suffix.lower()
    if kind is None:
        kind = "excel" if ext in (".xlsx", ".xls") else "csv"
    name = filename or source_path.name
    dest_dir = templates_root(marketplace, kind)
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / name
    shutil.copy2(source_path, dest)
    return dest


def migrate_legacy_templates() -> None:
    """Copy legacy flat templates into templates/{marketplace}/csv/ if missing."""
    for src in (ROOT / "templates" / "bestbuy").glob("*.csv"):
        dest = templates_root("bestbuy", "csv") / src.name.replace("-example", "")
        if not dest.exists():
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
    ne_src = ROOT / "templates" / "newegg"
    if ne_src.is_dir():
        for src in ne_src.glob("*.csv"):
            dest = templates_root("newegg", "csv") / src.name
            if not dest.exists():
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dest)

if __name__ == "__main__":
    category_key = input("Category key: ").strip()
    marketplace = input("Marketplace (bestbuy/newegg): ").strip().lower()

    mapping, template, created = ensure_mapping_yaml(
        category_key,
        marketplace,
    )

    print(f"Template: {template}")
    print(f"Mapping: {mapping}")
    print(f"Created: {created}")