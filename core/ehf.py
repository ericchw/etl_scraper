"""Load EHF profiles from configs/ehf.json (flat key → province amounts)."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EHF_PATH = ROOT / "configs" / "ehf.json"

# ehf.json province keys → Best Buy CSV column suffix (ehf-amount-{suffix})
EHF_TO_BBY = {
    "AB": "ab",
    "BC": "bc",
    "MB": "mb",
    "NB": "nb",
    "NL": "nl",
    "NS": "ns",
    "NT": "nt",
    "NU": "nu",
    "ON": "on",
    "PE": "pe",
    "QC": "qc",
    "SK": "sk",
    "YK": "yt",
}

BBY_EHF_COLUMNS = tuple(f"ehf-amount-{suffix}" for suffix in EHF_TO_BBY.values())


def load_ehf_profiles() -> dict:
    if not EHF_PATH.exists():
        return {}
    with open(EHF_PATH, encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, dict) else {}


def profile_amounts_for_bestbuy(profile_key: str) -> dict[str, float]:
    """
    Map ehf.json profile (e.g. ``SYS``, ``NB``) to Best Buy ``ehf-amount-*`` keys.

    ehf.json uses uppercase provinces (``AB``, ``YK``); Best Buy CSV uses lowercase
    suffixes (``ab``, ``yt``).
    """
    profile = load_ehf_profiles().get(profile_key) or {}
    if not isinstance(profile, dict):
        return {}

    amounts: dict[str, float] = {}
    for province, value in profile.items():
        suffix = EHF_TO_BBY.get(str(province).upper())
        if suffix is None:
            continue

        try:
            amounts[suffix] = round(float(value), 2)
        except (TypeError, ValueError):
            amounts[suffix] = 0.00
    return amounts
