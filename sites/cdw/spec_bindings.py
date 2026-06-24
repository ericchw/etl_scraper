"""CDW spec group/key → internal field paths (same site, multiple possible labels)."""

from __future__ import annotations

# Ordered paths: earlier = higher priority when keywords do not disambiguate.
PROCESSOR_CORES_PATHS = [
    ("Processor", "Cores"),
    ("Processor", "Number of Cores"),
]

PROCESSOR_THREADS_PATHS = [
    ("Processor", "Processor Main Features"),
    ("Processor", "Threads"),
    ("Processor", "Number of Threads"),
]

# prefer_keywords: when several paths match, pick raw text containing that word.
CDW_PROCESSOR_BINDINGS = {
    "cores": {
        "paths": PROCESSOR_CORES_PATHS,
        "parse": "number",
        "prefer_keywords": ["core"],
    },
    "threads": {
        "paths": PROCESSOR_THREADS_PATHS,
        "parse": "number",
        "prefer_keywords": ["thread"],
    },
}
