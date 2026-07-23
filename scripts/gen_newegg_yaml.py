"""Generate Newegg mapping YAML from category template CSV."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.categories import mapping_path
from core.yaml_generator import generate_all_missing, generate_mapping_yaml, resolve_category_key


def _prompt_overwrite(path: Path) -> bool:
    answer = input(f"{path.name} exists. Replace? [y/N]: ").strip().lower()
    return answer in {"y", "yes"}


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Newegg YAML from template CSV")
    parser.add_argument(
        "--category",
        help="Internal category key or Newegg suffix (e.g. monitor or MonitorLCDFlatPanel)",
    )
    parser.add_argument("--all", action="store_true", help="Generate for all categories")
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace existing YAML (otherwise skip)",
    )
    parser.add_argument(
        "--ensure-only",
        action="store_true",
        help="Only create if missing (same as default without --overwrite)",
    )
    args = parser.parse_args()

    overwrite = args.overwrite and not args.ensure_only

    if args.all:
        results = generate_all_missing("newegg", overwrite=overwrite)
        for result in results:
            print(f"{result.category_key}: {result.status} — {result.message}")
        return

    category_input = args.category
    if not category_input:
        category_input = input("Category key or Newegg suffix: ").strip()

    category_key = resolve_category_key(category_input, "newegg")
    if not category_key:
        print(f"Unknown category: {category_input!r}")
        sys.exit(1)

    target = mapping_path(category_key, "newegg")
    do_overwrite = overwrite
    if target and target.exists() and not do_overwrite:
        if sys.stdin.isatty():
            do_overwrite = _prompt_overwrite(target)
        if not do_overwrite:
            result = generate_mapping_yaml(category_key, "newegg", overwrite=False)
            print(result.message)
            return

    result = generate_mapping_yaml(category_key, "newegg", overwrite=do_overwrite)
    print(f"{result.status}: {result.message}")


if __name__ == "__main__":
    main()
