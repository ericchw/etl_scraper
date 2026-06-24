import json
from pathlib import Path


def load_json(path):

    try:
        with open(path, "r", encoding="utf-8") as f:
            print(f"LOADED -> {path}")
            return json.load(f)
    except Exception as e:
        print(e)
        return {}


def save_json(data, path, log=print):

    Path(path).parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with open(path, "w", encoding="utf-8") as f:

        json.dump(
            data,
            f,
            indent=2,
            ensure_ascii=False
        )

    log(f"SAVED -> {path}")