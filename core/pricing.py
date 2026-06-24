"""Best Buy list-price rules derived from the shared discount price."""

from __future__ import annotations

import math


def bestbuy_list_price_from_discount(discount_price: float) -> float:
    """
    Shared discount price → Best Buy regular ``price`` column.

    discount + 10; +100 when >= 1000; round up to next hundred; end .99
    """
    if discount_price <= 0:
        return 0.0

    value = discount_price + 10
    if value >= 1000:
        value += 100

    hundreds = math.ceil(value / 100) * 100
    return round(hundreds - 0.01, 2)
