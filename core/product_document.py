"""Product JSON on disk — shape and cleanup."""

from __future__ import annotations

import copy
from typing import Any


def finalize_product_document(doc: dict[str, Any]) -> dict[str, Any]:
    """
    Strip fields that must not be persisted in products/{MPN}.json.

    - submission: GUI/CLI only at export time
    - internal.legacy_specs: raw retailer tables live under scraped_data
    - internal._field_sources: debug-only; resolution lives in normalizer bindings
    """
    out = copy.deepcopy(doc)
    out.pop("submission", None)
    internal = out.get("internal")
    if isinstance(internal, dict):
        internal.pop("legacy_specs", None)
        internal.pop("_field_sources", None)
    return out
