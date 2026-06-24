"""Build merged internal product from per-source scraped_data blobs."""

from __future__ import annotations

from sites.bh.normalizer import normalize_bh_raw
from sites.cdw.normalizer import normalize_cdw_raw

from core.categories import product_code as product_code_from_category
from core.merge.field_merge import merge_internals
from core.product_document import finalize_product_document
from core.schema.product import envelope_from_internal
from core.schema.registry import DEFAULT_PRODUCT_CODE

NORMALIZERS = {
    "cdw": normalize_cdw_raw,
    "bh": normalize_bh_raw,
    "manufacturer": normalize_cdw_raw,
}


def resolve_product_code(
    *,
    explicit: str | None = None,
    submission: dict | None = None,
    existing_doc: dict | None = None,
) -> str:
    if explicit:
        return explicit.strip().upper()
    if isinstance(existing_doc, dict) and existing_doc.get("product_code"):
        return str(existing_doc["product_code"]).strip().upper()
    category = (submission or {}).get("category")
    if category:
        return product_code_from_category(category)
    return DEFAULT_PRODUCT_CODE


def normalize_source_raw(
    source: str,
    raw: dict,
    *,
    product_code: str = DEFAULT_PRODUCT_CODE,
) -> dict:
    fn = NORMALIZERS.get(source)
    if not fn:
        return normalize_cdw_raw(raw, product_code=product_code)
    return fn(raw, product_code=product_code)


def build_product_document(
    raw_by_source: dict[str, dict],
    *,
    product_code: str = DEFAULT_PRODUCT_CODE,
) -> dict:
    code = (product_code or DEFAULT_PRODUCT_CODE).strip().upper()

    partials = {
        source: normalize_source_raw(source, raw, product_code=code)
        for source, raw in raw_by_source.items()
        if raw
    }

    merged, merge_report = merge_internals(partials, product_code=code)

    if not (merged.get("identity") or {}).get("mpn"):
        for raw in raw_by_source.values():
            mpn = str(raw.get("mpn") or "").strip().upper()
            if mpn:
                merged.setdefault("identity", {})["mpn"] = mpn
                break

    doc = envelope_from_internal(merged, product_code=code)
    doc["scraped_data"] = raw_by_source
    doc["merge_report"] = merge_report

    return finalize_product_document(doc)
