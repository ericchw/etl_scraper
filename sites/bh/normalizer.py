"""B&H raw scrape → partial internal (dispatched by product_code)."""

from __future__ import annotations

from core.schema.registry import DEFAULT_PRODUCT_CODE
from sites.bh.normalize_mnt import normalize_bh_mnt
from sites.bh.normalize_nb import normalize_bh_nb

_BH_NORMALIZERS = {
    "NB": normalize_bh_nb,
    "MNT": normalize_bh_mnt,
}


def normalize_bh_raw(raw: dict, product_code: str = DEFAULT_PRODUCT_CODE) -> dict:
    code = (product_code or DEFAULT_PRODUCT_CODE).strip().upper()
    fn = _BH_NORMALIZERS.get(code, normalize_bh_nb)

    print("normalize_bh_raw BH product_code =", code)
    print("normalize_bh_raw BH normalizer =", fn.__name__)
    return fn(raw)
