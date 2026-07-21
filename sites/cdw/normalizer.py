"""CDW raw scrape → partial internal (dispatched by product_code)."""

from __future__ import annotations

# from core.schema.registry import DEFAULT_PRODUCT_CODE
# from sites.cdw.normalize_mnt import normalize_cdw_mnt
# from sites.cdw.normalize_nb import normalize_cdw_nb
# from sites.cdw.normalize_sys import normalize_cdw_sys
#
# _CDW_NORMALIZERS = {
#     "NB": normalize_cdw_nb,
#     "MNT": normalize_cdw_mnt,
#     "SYS": normalize_cdw_sys
# }
#
#
# def normalize_cdw_raw(raw: dict, product_code: str = DEFAULT_PRODUCT_CODE) -> dict:
#     code = (product_code or DEFAULT_PRODUCT_CODE).strip().upper()
#     fn = _CDW_NORMALIZERS.get(code)
#
#     print("normalize_cdw_raw CDW product_code =", code)
#     print("normalize_cdw_raw CDW normalizer =", fn.__ne__)
#     return fn(raw)


"""CDW raw scrape → partial internal (dispatched by product_code)."""
import importlib
from core.schema.registry import DEFAULT_PRODUCT_CODE


# All supported CDW codes (single source of truth)
_CDW_CODES = ["nb", "mnt", "sys"]


# Build registry dynamically at import time
_CDW_NORMALIZERS: dict[str, callable] = {}

for code in _CDW_CODES:
    module = importlib.import_module(f"sites.cdw.normalize_{code}")
    fn = getattr(module, f"normalize_cdw_{code}")
    _CDW_NORMALIZERS[code.upper()] = fn


def normalize_cdw_raw(raw: dict, product_code: str = DEFAULT_PRODUCT_CODE) -> dict:
    code = (product_code or DEFAULT_PRODUCT_CODE).strip().upper()

    fn = _CDW_NORMALIZERS.get(code)

    if not fn:
        raise ValueError(f"Unsupported CDW product_code: {code}")

    print("normalize_cdw_raw CDW product_code =", code)
    print("normalize_cdw_raw CDW normalizer =", fn)

    return fn(raw)