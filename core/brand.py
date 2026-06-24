import json
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BRANDS_PATH = ROOT / "configs" / "manufacturers.json"


@lru_cache(maxsize=1)
def load_brands() -> dict:
    if not BRANDS_PATH.exists():
        return {}

    with open(BRANDS_PATH, encoding="utf-8") as f:
        data = json.load(f)

    return data if isinstance(data, dict) else {}

def resolve_brand(key: str) -> dict:
    if not key:
        return {}

    cond = load_brands().get(key)

    if not isinstance(cond, dict):
        return {}

    return {
        "key": key,
        "label": cond.get("label") or "",
        "google_search": cond.get("google_search") or False,
        "google_cite": cond.get("google_cite") or "",
        "search_url": cond.get("search_url") or "",
        "redirect": cond.get("redirect") or False,
        "enabled": cond.get("enabled") or False,
    }

if __name__ == "__main__":
    ROOT = Path(__file__).resolve().parent.parent
    print(ROOT)
    print(BRANDS_PATH)
    print(resolve_brand("hp"))