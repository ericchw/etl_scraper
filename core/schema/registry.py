"""Product-family internal schemas (NB, MNT, …) loaded from configs/schemas/."""

from __future__ import annotations

import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
SCHEMAS_DIR = ROOT / "configs" / "schemas"
DEFAULT_PRODUCT_CODE = "NB"


def _schema_path(product_code: str) -> Path:
    code = (product_code or DEFAULT_PRODUCT_CODE).strip().upper()
    return SCHEMAS_DIR / f"{code}.json"


def list_product_codes() -> list[str]:
    if not SCHEMAS_DIR.exists():
        return [DEFAULT_PRODUCT_CODE]
    return sorted(p.stem.upper() for p in SCHEMAS_DIR.glob("*.json"))


def load_schema_template(product_code: str) -> dict:
    path = _schema_path(product_code)
    if not path.exists():
        path = _schema_path(DEFAULT_PRODUCT_CODE)
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return copy.deepcopy(data) if isinstance(data, dict) else {}


def empty_internal(product_code: str = DEFAULT_PRODUCT_CODE) -> dict:
    return load_schema_template(product_code)
