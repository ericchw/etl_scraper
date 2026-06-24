"""Scaffold marketplace YAML from template headers."""

from __future__ import annotations

from pathlib import Path

import yaml

from core.marketplace_templates import load_csv_headers

ROOT = Path(__file__).resolve().parent.parent


def load_template_headers(path: Path, *, marketplace: str) -> list[str]:
    return load_csv_headers(path, marketplace=marketplace)


def scaffold_mapping(
    *,
    marketplace: str,
    name: str,
    headers: list[str],
    headers_file: str,
) -> dict:
    fields = {h: {"literal": ""} for h in headers}
    return {
        "marketplace": marketplace,
        "name": name,
        "headers_file": headers_file,
        "fields": fields,
    }


def write_mapping_if_missing(
    path: Path,
    *,
    marketplace: str,
    name: str,
    template_csv: Path,
) -> tuple[Path, bool]:
    """Return (path, created)."""
    if path.exists():
        return path, False
    headers = load_template_headers(template_csv, marketplace=marketplace)
    data = scaffold_mapping(
        marketplace=marketplace,
        name=name,
        headers=headers,
        headers_file=template_csv.name,
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True)
    return path, True


def diff_template_vs_yaml(template_headers: list[str], yaml_fields: dict) -> dict:
    yaml_keys = set(yaml_fields.keys())
    template_set = set(template_headers)
    return {
        "missing_in_yaml": sorted(template_set - yaml_keys),
        "extra_in_yaml": sorted(yaml_keys - template_set),
    }
