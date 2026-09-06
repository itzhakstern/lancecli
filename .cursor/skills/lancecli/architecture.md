# lancecli internals (agent reference)

Request path:

```
argv → Typer (cli.py) → open_dataset (dataset.py) → run_* (commands/) → stdout
                              │
                              ├─ row I/O: scan.py  (head / batches / take / sample / tail)
                              └─ print:   render.py
```

## `cli.py`

- Typer app, `no_args_is_help` false: bare `lancecli` prints help and exits 0.
- Shared option types (`UriArg`, `ColumnsOpt`, `FilterOpt`, `OrderByOpt`, storage, time-travel). URI is the last parameter so it is positional.
- `_open` builds `OpenOptions` and catches errors.
- `_run` wraps `run_*`. `LanceCliError` → stderr + exit 1; other exceptions → `error: …` + exit 2.
- `_check_format` per command; `table`/`text` are aliased on some metadata commands.

## `dataset.py`

- `OpenOptions` frozen dataclass.
- Local preflight: missing path; `.lance` **file** (fragment) vs dataset **directory**.
- Only one of `--version` / `--tag` / `--asof`. Tag is passed as `version=` to `lance.dataset`.
- `lance.dataset(uri, version=…, asof=…, storage_options=…)`.
- Remote URIs inherit `AWS_ENDPOINT_URL` / `AWS_ENDPOINT` / region / `AWS_ALLOW_HTTP` into `storage_options`. CLI flags override. `http://` ⇒ `allow_http=true` if unset. Local URIs do not inherit AWS connection env.

## `scan.py`

| Helper | Pylance API | Used by |
|---|---|---|
| `head_table` | `ds.head` / `to_table` | `show` |
| `iter_batches` | `ds.to_batches` | `csv`, `jsonl` |
| `tail_table` | `count_rows` + `to_table(offset, limit)` | `tail` |
| `take_table` | `parse_indices` + `ds.take` | `take` |
| `sample_table` | RNG + `ds.take` (or load filtered table then sample) | `sample` |
| `parse_order_by` | `lance.dataset.ColumnOrdering` | scan kwargs |
| `sort_table` | PyArrow `Table.sort_by` | `take`, `sample` after fetch |
| `scan_kwargs` | columns, filter, limit, offset, order_by | all scanners |

`parse_indices`: `0,2:5,-1` — Python slices, negatives from `n_rows`. Out of range → `LanceCliError`.

`normalize_limit`: `None` or negative ⇒ no limit (parquet-tools `-1` convention).

## Commands

Thin: parse CLI strings → scan helper or dataset metadata → render.

**Row commands** (`show`, `tail`, `take`, `sample`): `emit_rows`.
**Stream dumps** (`csv`, `jsonl`): `iter_batches` + `write_csv` / `write_jsonl`; `warn_if_huge_tty` if unbounded and stdout is a TTY (>10k rows).
**Metadata:** `schema`, `inspect`, `stat`, `count`, `versions`, `fragments`, `indices`.
**`freq`:** `to_batches(columns=[col])` + `Counter` in Python (necessary for value counts).

`stat` vs `inspect`: `stat` is the one-screen health dashboard (hints for compaction / indexes). `inspect` is the verbose schema dump.

## `render.py`

- `emit_rows`: json (whole table as list), csv, jsonl, or Rich table.
- Truncation unless `--full` (`MAX_LIST_PREVIEW=2`, `MAX_STR=80`).
- `kv_table` + `panel_title` for `stat`.
- Commands accept `file=` for tests.

## Tests

`tests/conftest.py`: 100-row write + 10-row append + `create_scalar_index("age", "BTREE")`.
Invoke: `runner.invoke(app, ["show", "-n", "3", "-c", "id", dataset_uri])`.
Helper unit tests: `parse_indices`, `parse_order_by` in `tests/test_helpers.py`.
New arrs-style commands: `tests/test_arrs_commands.py`.
