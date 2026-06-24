import json
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONDITIONS_PATH = ROOT / "configs" / "conditions.json"


@lru_cache(maxsize=1)
def load_conditions() -> dict:
    if not CONDITIONS_PATH.exists():
        return {}

    with open(CONDITIONS_PATH, encoding="utf-8") as f:
        data = json.load(f)

    return data if isinstance(data, dict) else {}


def resolve_condition(key: str) -> dict:
    if not key:
        return {}

    cond = load_conditions().get(key)

    if not isinstance(cond, dict):
        return {}

    return {
        "key": key,
        "label": cond.get("label") or "",
        "suffix": cond.get("suffix") or []
    }

if __name__ == "__main__":
    ROOT = Path(__file__).resolve().parent.parent
    print(ROOT)
    print(resolve_condition("open_box"))
