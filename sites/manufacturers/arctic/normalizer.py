"""Arctic manufacturer normalizer dispatch (by sub_code)."""

from __future__ import annotations

from typing import Callable

from sites.manufacturers.arctic.normalize_arctic_hdd_ssd_cool import normalize_arctic_hdd_ssd_cool
from sites.manufacturers.arctic.normalize_cpu_aio import normalize_arctic_cpu_aio
from sites.manufacturers.arctic.normalize_cpu_air_cool import normalize_arctic_cpu_air_cool
from sites.manufacturers.arctic.normalize_case_fan import normalize_arctic_case_fan
from sites.manufacturers.arctic.normalize_thermal_paste import normalize_arctic_thermal_paste


_ARCTIC_NORMALIZERS: dict[str, Callable] = {
    "CPU-AIO": normalize_arctic_cpu_aio,
    "HDD-SSD-COOL": normalize_arctic_hdd_ssd_cool,
    "CPU-AIR-COOL": normalize_arctic_cpu_air_cool,
    "CASE-FAN": normalize_arctic_case_fan,
    "THERMAL-PASTE": normalize_arctic_thermal_paste,
}

def normalize_arctic_raw(
    raw: dict,
    *,
    product_code: str,
    sub_code: str,
) -> dict:
    norm_key = (sub_code or product_code or "").strip().upper()
    fn = _ARCTIC_NORMALIZERS.get(norm_key)
    if fn:
        return fn(raw, product_code=product_code, sub_code=norm_key)

    raise ValueError(
        f"No Arctic normalizer registered for sub_code {norm_key!r}. "
        f"Known: {', '.join(sorted(_ARCTIC_NORMALIZERS))}"
    )

__all__ = [
    "normalize_arctic_raw",
    "normalize_arctic_cpu_aio",
    "normalize_arctic_hdd_ssd_cool",
    "normalize_arctic_cpu_air_cool",
    "normalize_arctic_case_fan",
    "normalize_arctic_thermal_paste",
]
