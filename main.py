import argparse
from pprint import pprint

from core.exporter import export_bestbuy_laptop, export_newegg
from core.marketplace_defaults import bestbuy_discount_dates
from core.pipeline import run_product_pipeline
from core.pricing import bestbuy_list_price_from_discount
from core.utils import load_json


def build_submission(args: argparse.Namespace) -> dict:
    discount = round(args.price, 2) if args.price is not None else None
    list_price = bestbuy_list_price_from_discount(discount) if discount else None
    discount_start, discount_end = bestbuy_discount_dates()
    if args.discount_start_date:
        discount_start = args.discount_start_date
    if args.discount_end_date:
        discount_end = args.discount_end_date
    return {
        "category": args.category or "",
        "manufacturer": args.manufacturer or "",
        "price": discount,
        "condition": args.condition,
        "marketplaces": {
            "newegg": {
                "condition": args.condition,
                "enabled": True,
                "shipping_type": args.newegg_shipping_type,
            },
            "bestbuy": {
                "enabled": True,
                "condition": args.condition,
                "package_size": args.bestbuy_package_size,
                "list_price": list_price,
                "discount_price": discount,
                "discount_start_date": discount_start,
                "discount_end_date": discount_end,
                "ehf_profile": args.ehf_profile,
            },
        },
    }


def main_cli(args: argparse.Namespace) -> None:
    submission = build_submission(args)

    if args.export_bestbuy or args.export_newegg:
        from core.cache import resolve_product_json_path

        json_path = resolve_product_json_path(args.mpn)
        if not json_path:
            raise SystemExit(f"No product JSON for MPN {args.mpn}")

        product = load_json(str(json_path))
        product["submission"] = submission

        if args.export_bestbuy:
            path, warnings = export_bestbuy_laptop(product)
            print(f"Best Buy → {path}")
            for w in warnings:
                print(f"WARN: {w}")

        if args.export_newegg:
            path, warnings = export_newegg(product)
            print(f"Newegg → {path}")
            for w in warnings:
                print(f"WARN: {w}")

        return

    result = run_product_pipeline(args.mpn, submission=submission)
    product = result["normalized"]
    submission = result["submission"]
    if result.get("success") and result.get("normalized"):
        pprint(result["normalized"])
    elif not result.get("success"):
        raise SystemExit(1)


def main_gui() -> None:
    from gui.main_window import run_app

    run_app()


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Marketplace prep: CDW scrape + submission metadata.")
    p.add_argument("--cli", action="store_true", help="Script mode (no PyQt window).")
    # p.add_argument("--open-box", action="store_true", help="Open Box title/description formatting.")
    p.add_argument("--export-bestbuy", action="store_true", help="Export Best Buy CSV from existing JSON (no scrape).")
    p.add_argument("--export-newegg", action="store_true", help="Export Newegg CSV from existing JSON (no scrape).")
    p.add_argument("--mpn", default="")
    p.add_argument("--category", default="")
    p.add_argument("--manufacturer", default="")
    p.add_argument("--price", type=float, default=None, help="Shared Newegg / Best Buy discount price.")
    p.add_argument("--condition", default="")
    p.add_argument(
        "--newegg-shipping-type",
        choices=["Free", "Default"],
        default="Free",
    )
    p.add_argument("--bestbuy-package-size", choices=["LETTER", "MED", "LARGE"], default="MED")
    p.add_argument("--discount-start-date", default="")
    p.add_argument("--discount-end-date", default="")
    p.add_argument("--ehf-profile", default="SYS")
    return p


if __name__ == "__main__":
    parser = build_parser()
    ns = parser.parse_args()
    if ns.cli or ns.export_bestbuy or ns.export_newegg:
        main_cli(ns)
    else:
        main_gui()
