def merge_products(*products):

    merged = {

        "title": "",
        "brand": "",
        "mpn": "",
        "description": "",

        "features": [],
        "images": [],
        "specs": {}
    }

    for product in products:

        if not product:
            continue

        for key, value in product.items():

            if not value:
                continue

            # lists
            if isinstance(value, list):

                merged[key] = list(
                    dict.fromkeys(
                        merged.get(key, []) + value
                    )
                )

            # dict
            elif isinstance(value, dict):

                if key not in merged:
                    merged[key] = {}

                def is_valid(v):
                    return v not in (None, "", [], {})

                for k, v in value.items():

                    # if k not in merged[key]:
                    #     merged[key][k] = v

                    if not is_valid(v):
                        continue

                    old = merged[key].get(k)

                    if not is_valid(old):
                        merged[key][k] = v


            else:

                if not merged.get(key):
                    merged[key] = value

    return merged