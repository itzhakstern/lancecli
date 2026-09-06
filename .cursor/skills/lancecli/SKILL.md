---
name: lancecli
description: Develop and extend the lancecli Python CLI (Lance dataset inspector, parquet-tools equivalent). Use when adding or changing commands, scan/take/order-by behavior, storage/open options, rendering, tests, README, or MAP.md in the lance-tools / lancecli repo.
---

# lancecli development

Read-only CLI for **Lance datasets** via **pylance only**. No DuckDB, no pandas on the data path. Package/console script is `lancecli` (not `lance-tools` — that name belongs to pylance file tools).

Human architecture map (repo root): `MAP.md`. User-facing examples: `README.md`. Deeper file/API notes: [architecture.md](architecture.md).

## Before changing code

1. Identify the layer (do not skip or merge them):
   - flags / wiring → `src/lancecli/cli.py`
   - open URI / storage / time-travel → `src/lancecli/dataset.py`
   - row access (scanner, take, sample, sort parse) → `src/lancecli/scan.py`
   - one command's payload + print → `src/lancecli/commands/<name>.py`
   - tables / csv / jsonl / truncation → `src/lancecli/render.py`
2. Prefer pylance pushdown (`columns`, `filter`, `limit`, `offset`, `order_by`, `ds.take`) over loading tables into Python.
3. After edits: `uv run ruff check --fix src tests && uv run ruff format src tests && uv run pytest -q`
4. If the command is user-visible, add a README example against `examples/events.lance` using the `lancecli` command (not `uv run`). Regenerate the demo with `python examples/make_events.py`.

## Invariants

- **pylance only** for data. Do not add duckdb/pandas/polars as dependencies or on the read path.
- **URI last positional** on every command. Shared flags are the `Annotated` aliases in `cli.py` (`ColumnsOpt`, `FilterOpt`, `OrderByOpt`, …). Reuse them.
- **`LanceCliError`** for user mistakes (bad URI, bad `--indices`, bad `--order-by`). `cli.py` maps it to exit **1**; unexpected exceptions to exit **2**.
- **`freq -c`** is a **single column to count**, not `--columns` projection. Do not reuse `ColumnsOpt` there.
- **`--order-by`**: scanner pushdown on `show` / `csv` / `jsonl` / `tail`. Post-sort of an already-fetched Arrow table on `take` / `sample` (`sort_table`).
- **Indexes are live-row positions** in the opened version, not the `id` column.
- Do not `show` / `SELECT *` all columns on wide remote datasets in docs or tests. Always project with `-c`.
- Do not commit, push, or publish to PyPI unless the user asks.
- Line length 100, Ruff `E,F,I,UP`, Python ≥ 3.10. Keep `__version__` in `src/lancecli/__init__.py` in sync with `pyproject.toml`.

## Adding a command

1. `src/lancecli/commands/<name>.py` — `run_<name>(ds, *, …, file=None)`. Commands take an **already-open** dataset; they never call `lance.dataset` themselves.
2. Register in `cli.py`: `_open(...)` then `_run(lambda: run_<name>(...))`. Validate `--format` with `_check_format`.
3. New row-access pattern → helper in `scan.py`, not inside the command module.
4. Tests: `typer.testing.CliRunner` against the `dataset_uri` fixture (`tests/conftest.py`: 100 rows + 10 append + BTREE on `age`). Prefer `--format json` for assertions.
5. Document in README with copy-paste against `examples/events.lance`. Update `MAP.md` if the data flow changed.

## Tests and demo data

| | Fixture `dataset_uri` | `examples/events.lance` |
|---|---|---|
| Rows | 110 (100 + 10 append) | 50 |
| Extra | BTREE index on `age` | no indexes |
| Cities | none | TLV/NYC/BER/LON |

Do not assume fixture ids/cities match the example file.

## Cloud / object store

Remote URIs inherit AWS/GCS/Azure env vars. **Flags are optional.** `parse_storage_options(inherit_env=True)` copies `AWS_ENDPOINT_URL` / `AWS_ENDPOINT` / `AWS_ENDPOINT_URL_S3`, `AWS_REGION` / `AWS_DEFAULT_REGION`, and `AWS_ALLOW_HTTP`. Credentials stay in the environment (object_store reads them). `http://` endpoints set `allow_http=true` if unset. CLI `--storage-option` > `--endpoint-url` > env. Local URIs use `inherit_env=False`. Never put access keys in the repo, README, or skill files.
