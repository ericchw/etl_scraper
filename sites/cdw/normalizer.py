"""CDW raw scrape → partial internal (dispatched by product_code)."""

from __future__ import annotations

from core.schema.registry import DEFAULT_PRODUCT_CODE
from sites.cdw.normalize_mnt import normalize_cdw_mnt
from sites.cdw.normalize_nb import normalize_cdw_nb

_CDW_NORMALIZERS = {
    "NB": normalize_cdw_nb,
    "MNT": normalize_cdw_mnt,
}


def normalize_cdw_raw(raw: dict, product_code: str = DEFAULT_PRODUCT_CODE) -> dict:
    code = (product_code or DEFAULT_PRODUCT_CODE).strip().upper()
    fn = _CDW_NORMALIZERS.get(code)

    print("normalize_cdw_raw CDW product_code =", code)
    print("normalize_cdw_raw CDW normalizer =", fn.__name__)
    return fn(raw)
