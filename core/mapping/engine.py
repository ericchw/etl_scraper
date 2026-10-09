"""Marketplace field mapping: internal schema + YAML rules (v2 pipeline)."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from core.categories import marketplace_code
from core.ehf import profile_amounts_for_bestbuy
from core.mapping.sources import has_source_rule, resolve_sources
from core.schema.product import ensure_internal, get_path
from core.transforms import (
    TRANSFORMS,
    build_specs_text,
    design_body_from_context,
    format_features_bullets,
)

ROOT = Path(__file__).resolve().parent.parent.parent

_RULE_META_KEYS = frozenset({
    "transform",
    "type",
    "allowed",
    "default",
    "decimals",
    "pipeline",
    "from",
    "source",
    "sources",
    "sources_first",
    "sources_join",
    "mode",
    "join",
    "list_join",
    "suffix",
    "prefix",
    "template",
    "apply_template_after",
    "literal",
    "when",
    "from_category",
    "from_submission",
    "source_field",
    "filter_include_keywords",
    "filter_exclude_keywords",
})


def _load_yaml(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data if isinstance(data, dict) else {}


def _get_nested(data: dict | None, path: str) -> Any:
    return get_path(data, path.replace("/", "."))


def _format_value(value: Any, rule: dict) -> str:
    if value is None:
        value = rule.get("default", "")

    if value == "" or value is None:
        return ""

    field_type = rule.get("type")

    if field_type == "integer":
        try:
            result = str(int(float(value)))
        except (TypeError, ValueError):
            return ""

    elif field_type == "decimal":
        decimals = int(rule.get("decimals", 2))
        try:
            result = f"{float(value):.{decimals}f}"
        except (TypeError, ValueError):
            return ""

    else:
        result = str(value)

    # if result:
    #     suffix = rule.get("suffix", "")
    #     if suffix == '"':
    #         return f"{result}"
    #     result = f"{rule.get('prefix', '')}{result}{suffix}"

    return result


def _validate(value: str, rule: dict, field_name: str, warnings: list[str]) -> str:
    allowed = rule.get("allowed")
    if allowed and value and value not in allowed:
        warnings.append(f"{field_name}: value {value!r} is not in the allowed values")
    return value


def _apply_pipeline_string_step(current: Any, step: str) -> Any:
    if step == "uppercase":
        return str(current or "").upper()
    if step == "lowercase":
        return str(current or "").lower()
    if step == "trim":
        return str(current or "").strip()
    if step == "normalize_whitespace":
        return re.sub(r"\s+", " ", str(current or "")).strip()
    return current


def _run_pipeline(value: Any, steps: list, context: dict, warnings: list[str], field_name: str) -> Any:
    current = value
    for step in steps or []:
        if isinstance(step, str):
            if step in ("uppercase", "lowercase", "trim", "normalize_whitespace"):
                current = _apply_pipeline_string_step(current, step)
                continue
            transform = TRANSFORMS.get(step)
            if transform:
                current = transform(current, context=context)
            else:
                warnings.append(f"{field_name}: unknown pipeline step {step!r}")
            continue
        if not isinstance(step, dict):
            continue
        if "uppercase" in step:
            current = str(current or "").upper()
        elif "lowercase" in step:
            current = str(current or "").lower()
        elif "trim" in step:
            current = str(current or "").strip()
        elif "normalize_whitespace" in step:
            current = re.sub(r"\s+", " ", str(current or "")).strip()
        elif "join" in step:
            sep = step.get("join", "; ")
            if isinstance(current, list):
                current = sep.join(str(x) for x in current if str(x).strip())
        elif "prepend" in step:
            current = f"{step['prepend']}{current or ''}"
        elif "append" in step:
            current = f"{current or ''}{step['append']}"
        elif "replace" in step:
            for old, new in step["replace"].items():
                current = str(current or "").replace(old, new)
        elif "keyword_map" in step:
            text = str(current or "").upper()
            for canonical, aliases in step["keyword_map"].items():
                keys = [canonical, *(aliases or [])]
                if any(k.upper() in text for k in keys):
                    current = canonical
                    break
        elif "transform" in step:
            transform = TRANSFORMS.get(step["transform"])
            if transform:
                kwargs = {k: v for k, v in step.items() if k != "transform"}
                current = transform(current, context=context, **kwargs)
        elif step.get("unit_convert"):
            from core.units import length_to_in, weight_to_lb

            uc = step["unit_convert"]
            if uc.get("to") in ("in", "inch"):
                current = length_to_in(current, uc.get("from", ""))
            elif uc.get("to") in ("lb", "pound"):
                current = weight_to_lb(current, uc.get("from", ""))
    return current


def _render_template(template: str, context: dict) -> str:
    vars_map = context.get("vars") or {}
    replacements = {
        "title": str(context.get("title", "")),
        "mpn": str(vars_map.get("mpn", context.get("mpn", ""))),
        "brand": str(vars_map.get("brand", "")),
        "model": str(vars_map.get("model", "")),
        "description": str(context.get("description", "")),
        "features": str(context.get("features_text", "")),
        "specs_text": str(context.get("specs_text", "")),
        "value": str(context.get("_template_value", "")),
        "included_items": str(context.get("_template_value", "")),
    }
    result = template
    for key, val in replacements.items():
        result = result.replace("{" + key + "}", val)
    return result


def _resolve_rule(
    field_name: str,
    rule: dict,
    *,
    product: dict,
    context: dict,
    warnings: list[str],
) -> str:
    raw: Any = ""

    if "literal" in rule:
        raw = rule["literal"]
    elif "from" in rule:
        raw = get_path(context["internal"], rule["from"])
    elif "source_field" in rule:
        raw = product.get(rule["source_field"], "")
    elif has_source_rule(rule):
        raw = resolve_sources(rule, context)
    elif "from_category" in rule:
        marketplace = rule["from_category"].get("marketplace", "bestbuy")
        category_key = _get_nested(product, "submission.category") or "gaming_laptop"
        raw = marketplace_code(category_key, marketplace)
    elif "from_submission" in rule:
        raw = _get_nested(product, f"submission.{rule['from_submission']}")

    if rule.get("when"):
        for cond in rule["when"]:
            field = cond.get("field", "")
            op = cond.get("op", "eq")
            expected = cond.get("value")
            actual = get_path(context["internal"], field) or _get_nested(product, field)
            if op == "eq" and actual != expected:
                raw = cond.get("else", "")
                break
            if op == "neq" and actual == expected:
                raw = cond.get("else", "")
                break

    transform_name = rule.get("transform")
    if transform_name:
        transform = TRANSFORMS.get(transform_name)
        if transform:
            kwargs = {k: v for k, v in rule.items() if k not in _RULE_META_KEYS}
            raw = transform(raw, context=context, **kwargs)
        else:
            warnings.append(f"{field_name}: unknown transform {transform_name!r}")

    pipeline = rule.get("pipeline")
    if pipeline:
        raw = _run_pipeline(raw, pipeline, context, warnings, field_name)

    if "template" in rule:
        context["_template_value"] = raw
        raw = _render_template(rule["template"], context)

    result = _validate(
        _format_value(raw, rule),
        rule,
        field_name,
        warnings,
    )

    return result


def _retailer_specs_for_export(product: dict) -> dict:
    scraped = product.get("scraped_data") or {}
    for source in ("cdw", "bh", "manufacturer"):
        block = scraped.get(source) or {}
        site_specs = block.get("specs")
        if isinstance(site_specs, dict) and site_specs:
            return site_specs
    legacy = product.get("specs")
    return legacy if isinstance(legacy, dict) else {}


def _build_context(product: dict) -> dict:
    internal = ensure_internal(product)
    legacy_specs = _retailer_specs_for_export(product)
    identity = internal.get("identity") or {}
    content = internal.get("content") or {}

    from core.spec_lookup import spec_value

    def get_spec(group: str, key: str) -> str:
        return spec_value(legacy_specs, group, key)

    condition = _get_nested(product, "submission.condition")
    if not condition:
        condition = _get_nested(product, "submission.marketplaces.bestbuy.condition")

    return {
        "product": product,
        "internal": internal,
        "legacy_specs": legacy_specs,
        "mpn": identity.get("mpn") or product.get("mpn", ""),
        "title": content.get("title") or identity.get("title") or product.get("title", ""),
        "description": design_body_from_context({"internal": internal, "product": product}),
        "design_text": design_body_from_context({"internal": internal, "product": product}),
        "features_text": format_features_bullets(
            (internal.get("content") or {}).get("features") or product.get("features")
        ),
        "specs_text": build_specs_text(legacy_specs),
        "images": (internal.get("content") or {}).get("images")
        or product.get("scraped_image_urls")
        or product.get("images")
        or [],
        "condition": condition,
        "get_spec": get_spec,
        "vars": {
            "mpn": identity.get("mpn") or product.get("mpn", ""),
            "brand": identity.get("brand", ""),
            "model": identity.get("model", ""),
        },
    }


def map_product(product: dict, mapping_path: Path | str) -> tuple[dict[str, str], list[str]]:
    mapping_path = Path(mapping_path)
    config = _load_yaml(mapping_path)
    fields: dict = config.get("fields") or {}
    warnings: list[str] = []
    context = _build_context(product)

    row: dict[str, str] = {}
    for field_name, rule in fields.items():
        if not isinstance(rule, dict):
            continue
        row[field_name] = _resolve_rule(field_name, rule, product=product, context=context, warnings=warnings)

    submission = product.get("submission") or {}
    ehf_amounts = _get_nested(submission, "marketplaces.bestbuy.ehf_amounts")
    if not ehf_amounts:
        profile_key = _get_nested(submission, "marketplaces.bestbuy.ehf_profile") or "SYS"
        ehf_amounts = profile_amounts_for_bestbuy(str(profile_key))

    if isinstance(ehf_amounts, dict):
        for suffix, amount in ehf_amounts.items():
            col = f"ehf-amount-{suffix}"
            row[col] = _format_value(amount, {"type": "decimal", "decimals": 2})

    return row, warnings


def mapping_config_path(marketplace: str, name: str) -> Path:
    return ROOT / "configs" / "marketplaces" / marketplace / f"{name}.yaml"
