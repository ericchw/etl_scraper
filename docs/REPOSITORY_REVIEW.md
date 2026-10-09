# Repository review - 2026-10-08

## Credential check

Scanned 132 local files (including ignored files, excluding `.git` internals)
and 223 unique file blobs reachable through local Git refs. The repository had
nine commits on HEAD at the time of review.

No candidates matched checks for credential assignments, common provider tokens,
private-key headers, URLs containing usernames/passwords, or JWTs.
Matches would have been reported by filename and line only, without secret values.
This was a custom pattern scan, not a guarantee: opaque credentials, encoded
secrets, binary content, unreachable Git objects, and remote-only branches may
not be covered. Dependency vulnerability auditing was not performed.

## Changes made

- Reject empty IDs, traversal paths, drive/stream syntax, invalid Windows
  characters, and reserved device names in product/cache/export filenames.
  Valid MPNs such as `9W3E2UA#ABL` remain supported.
- Close resources when browser startup fails, and stop Playwright even if
  browser closure fails during pipeline cleanup.
- Use default GUI settings when the settings JSON is malformed or unreadable.
- Remove the old commented-out exporter implementation and debug prints that
  dumped submission metadata, export context, and raw thermal-paste scrape data.
- Report YAML `allowed` value mismatches through export warnings; preserve the
  original exported value for review.
- Ignore additional environment files, private-key files, browser storage-state
  JSON, legacy cache output, and IDE metadata for future untracked files.
- Add setup/usage documentation and focused regression tests.

## Remaining cleanup and limitations

- Two generated product JSON files and `.idea` files are already tracked.
  `.gitignore` does not untrack existing files or remove them from history.
  Product files contain scraped data and may include business information;
  they were retained to avoid removing potentially useful samples.
- `core/merge.py` and `core/merge/` coexist. Imports resolve to the package;
  the former contains a legacy merge function. Decide whether it should become
  an explicit compatibility module or be removed after checking external users.
- Root `ehf.json` differs from `configs/ehf.json`; `sites/cdw/cdw.json` differs
  from `configs/scrapers/cdw.json`. Active loaders use the configs directory.
  Reconcile the contents before deleting the older copies.
- Some normalizers and transforms still print debug details; large blocks of
  commented code remain elsewhere. A broader logging cleanup would make GUI
  logs easier to read.
- `core/downloader.py` does not explicitly close streamed HTTP responses and
  leaves incomplete files on failed transfers. It should also validate its own
  filename prefix if used independently of the product pipeline.
- CLI inputs still lack price/date validation; invalid or nonfinite prices can
  cause errors. Product filename validation currently raises `ValueError`;
  some GUI/CLI callers could present that error more gracefully.
- Dependency versions in `requirements.txt` are unpinned. Establish and record
  a working dependency set after testing on supported 64-bit Python platforms.
- Marketplace CSV templates are not present in this checkout. Full export
  verification requires those local templates.

## Validation

Seven standard-library regression tests cover product/cache path safety,
settings fallback and preservation, and browser startup cleanup/success behavior.
All passed. Python source parses using Python 3.12 syntax rules, and all 20 JSON
files under `configs/` parsed successfully. `git diff --check` passed.

The installed Python runtimes are 32-bit and lack the application dependencies.
GUI launch, live scraping, and complete marketplace exports were not tested.
Browser tests use a mocked Playwright runtime.
