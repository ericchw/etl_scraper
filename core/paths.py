"""Validate identifiers before using them as filesystem components."""

import re


_RESERVED_NAME = re.compile(r"^(?:CON|PRN|AUX|NUL|CONIN\$|CONOUT\$|COM[1-9¹²³]|LPT[1-9¹²³])$", re.IGNORECASE)


def safe_path_component(value: str) -> str:
    """Preserve valid identifiers (including #), rejecting unsafe filenames."""
    value = value.strip()
    if (
        not value
        or any(char in '<>:"/\\|?*' or ord(char) < 32 for char in value)
        or value.endswith((".", " "))
        or _RESERVED_NAME.fullmatch(value.split(".", 1)[0].rstrip())
    ):
        raise ValueError("Identifier must be a non-empty, valid filename component")
    return value
