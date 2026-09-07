# lancecli

Inspect and dump [Lance](https://lance.org/) datasets from the command line.

Reads go through [pylance](https://pypi.org/project/pylance/) only. There is no DuckDB (or pandas) on the data path: column projection, SQL filters, sorts, and row limits are pushed into the Lance scanner. Random row access uses Lance `take`, not a full scan.

- [Install](#install)
- [Quick start](#quick-start)
- [Commands](#commands) — worked examples on `examples/events.lance`
- [Cloud storage](#cloud-storage) — env-only S3, then optional flags

## Install

```bash
pip install lancecli
```

That installs the `lancecli` command. From then on:

```bash
lancecli --help
lancecli stat /path/to/dataset.lance
```

```
lancecli <command> [flags] <URI>
```
The URI is a positional argument (local directory or `s3://`). Flags can go before or after it.
Every command also has `-h` / `--help` with the same flags.


## Quick start

After `pip install lancecli`, point it at **your** dataset:

```bash
lancecli stat /path/to/events.lance
lancecli show /path/to/events.lance -c id,name -n 10
```

The copy-paste examples below use `examples/events.lance` from a clone of this repository.

```bash
lancecli stat examples/events.lance
lancecli show examples/events.lance
lancecli take --indices 0,2:5,-1 -c id,name,age examples/events.lance
lancecli show -n 5 -c id,age --order-by age:desc examples/events.lance
```

---

## Commands

| Command | What it does |
|---|---|
| [`stat`](#stat) | One-screen health summary (rows, fragments, indexes, size). |
| [`show`](#show) | Pretty table of rows. **Default: first 10.** |
| [`tail`](#tail) | Last N rows (default 10). |
| [`take`](#take) | Rows by **index** (`--indices 0,2:5,-1`) via Lance random access. |
| [`sample`](#sample) | Random rows (`--seed` for reproducibility). |
| [`csv`](#csv--jsonl) | Stream CSV to stdout (default: all matching rows). |
| [`jsonl`](#csv--jsonl) | Stream JSON Lines (better for vectors and nested types). |
| [`schema`](#schema) | Arrow schema (`--physical` for the Lance-native schema). |
| [`inspect`](#inspect) | Verbose metadata dump including every column type. |
| [`count`](#count) | Row count (`--filter` uses the scanner). |
| [`freq`](#freq) | Value counts for one column. |
| [`versions`](#versions) | Time-travel version list. |
| [`fragments`](#fragments) | Physical layout (files, deletions). |
| [`indices`](#indices) | Vector / FTS / scalar indexes. |

---

### `stat`

First command to run on an unfamiliar dataset. Metadata only — no row scan. Prints rows, deleted, fragment sizes, on-disk data size, version, format, and indexes.

```bash
lancecli stat examples/events.lance
```

```
╭───────────────────────╮
│ examples/events.lance │
╰─── dataset summary ───╯

 rows        50
 deleted     0  (0.0%)
 columns     5
 fragments   1  (50 rows each)
 data size   3.8 KiB
 version     1  (latest 1)
 format      Lance 2.1
 versions    1
 indices     none
```

Machine-readable:

```bash
lancecli stat examples/events.lance --format json
```

`inspect` is the verbose sibling (full schema dump). Prefer `stat` for a health check.

---

### `show`

Human-readable preview. **Defaults to the first 10 rows.** Always combine with `-c` / `--columns` on wide tables, and `-n` if you want more than 10.

```bash
lancecli show examples/events.lance -c id,name,age,city
```

```
┏━━━━┳━━━━━━━━┳━━━━━┳━━━━━━┓
┃ id ┃ name   ┃ age ┃ city ┃
┡━━━━╇━━━━━━━━╇━━━━━╇━━━━━━┩
│ 0  │ user_0 │ 20  │ TLV  │
│ 1  │ user_1 │ 21  │ NYC  │
│ 2  │ user_2 │ 22  │ BER  │
│ 3  │ user_3 │ 23  │ LON  │
│ 4  │ user_4 │ 24  │ TLV  │
│ 5  │ user_5 │ 25  │ NYC  │
│ 6  │ user_6 │ 26  │ BER  │
│ 7  │ user_7 │ 27  │ LON  │
│ 8  │ user_8 │ 28  │ TLV  │
│ 9  │ user_9 │ 29  │ NYC  │
└────┴────────┴─────┴──────┘
```

Vectors and long strings are truncated. `--full` prints them whole:

```bash
lancecli show examples/events.lance -n 2 -c id,embedding
lancecli show examples/events.lance -n 1 -c id,embedding --full
```

```
┏━━━━┳━━━━━━━━━━━━━━━┓
┃ id ┃ embedding     ┃
┡━━━━╇━━━━━━━━━━━━━━━┩
│ 0  │ [0, 1, …] (4) │
│ 1  │ [4, 5, …] (4) │
└────┴───────────────┘

┏━━━━┳━━━━━━━━━━━━━━━━━━━━━━┓
┃ id ┃ embedding            ┃
┡━━━━╇━━━━━━━━━━━━━━━━━━━━━━┩
│ 0  │ [0.0, 1.0, 2.0, 3.0] │
└────┴──────────────────────┘
```

`--format` can be `table` (default), `csv`, `jsonl`, or `json`.

#### Filter (pushed into the scanner)

`--filter` is a SQL predicate. Lance evaluates it in the scanner; with a scalar index on that column it can skip fragments instead of reading every row.

```bash
lancecli show examples/events.lance -n 20 -c id,name --filter "age > 18"
lancecli show examples/events.lance -c id,city,age --filter "city = 'TLV'"
```

#### Sort (`--order-by`)

On `show` / `csv` / `jsonl` the sort is passed to the Lance scanner (`order_by=`), together with `--filter`, `-c`, and `-n`. The table is not loaded into Python and then sorted.

```
--order-by age              # ascending (default)
--order-by age:desc
--order-by age:desc,id      # age descending, then id ascending
```

Directions: `asc` / `ascending` / `a`, or `desc` / `descending` / `d`.

Five oldest ages in the demo file:

```bash
lancecli show examples/events.lance -n 5 -c id,name,age --order-by age:desc
```

```
┏━━━━┳━━━━━━━━━┳━━━━━┓
┃ id ┃ name    ┃ age ┃
┡━━━━╇━━━━━━━━━╇━━━━━┩
│ 39 │ user_39 │ 59  │
│ 38 │ user_38 │ 58  │
│ 37 │ user_37 │ 57  │
│ 36 │ user_36 │ 56  │
│ 35 │ user_35 │ 55  │
└────┴─────────┴─────┘
```

Filter first, then sort the matching rows (both still in the scanner):

```bash
lancecli show examples/events.lance -c id,city,age \
  --filter "city = 'TLV'" --order-by age:desc
```

```
┏━━━━┳━━━━━━┳━━━━━┓
┃ id ┃ city ┃ age ┃
┡━━━━╇━━━━━━╇━━━━━┩
│ 36 │ TLV  │ 56  │
│ 32 │ TLV  │ 52  │
│ 28 │ TLV  │ 48  │
│ 24 │ TLV  │ 44  │
│ 20 │ TLV  │ 40  │
│ 16 │ TLV  │ 36  │
│ 12 │ TLV  │ 32  │
│ 48 │ TLV  │ 28  │
│ 8  │ TLV  │ 28  │
│ 4  │ TLV  │ 24  │
└────┴──────┴─────┘
```

(Default `-n 10`, so this is the ten oldest TLV rows — not every TLV row.)

If `stat` / `indices` show a scalar or vector index on a column, `--filter` (and sometimes `--order-by`) on that column can use it instead of a full scan.

---

### `take`

Lance-native random access. `take` does **not** scan from the start of the file. It calls `ds.take(indices)`: positional **live-row** indexes in the opened version (`0` is the first live row, `-1` is the last).

That is the point versus a Parquet dump: jump to row 100_000 without reading the 99_999 before it.

`--indices` uses Python list/slice syntax (comma-separated):

| Spec | Meaning |
|---|---|
| `0` | First row |
| `-1` | Last row |
| `2:5` | Rows 2, 3, 4 (stop exclusive, like Python) |
| `0,10,20` | Three specific rows |
| `::10` | Every tenth row |
| `0,2:5,-1` | First, then 2–4, then last |

```bash
lancecli take --indices 0,2:5,-1 -c id,name,age examples/events.lance
```

```
┏━━━━┳━━━━━━━━━┳━━━━━┓
┃ id ┃ name    ┃ age ┃
┡━━━━╇━━━━━━━━━╇━━━━━┩
│ 0  │ user_0  │ 20  │
│ 2  │ user_2  │ 22  │
│ 3  │ user_3  │ 23  │
│ 4  │ user_4  │ 24  │
│ 49 │ user_49 │ 29  │
└────┴─────────┴─────┘
```

Every tenth row:

```bash
lancecli take --indices '::10' -c id,name,city examples/events.lance
```

```
┏━━━━┳━━━━━━━━━┳━━━━━━┓
┃ id ┃ name    ┃ city ┃
┡━━━━╇━━━━━━━━━╇━━━━━━┩
│ 0  │ user_0  │ TLV  │
│ 10 │ user_10 │ BER  │
│ 20 │ user_20 │ TLV  │
│ 30 │ user_30 │ BER  │
│ 40 │ user_40 │ TLV  │
└────┴─────────┴──────┘
```

`--order-by` on `take` sorts the **small table you already fetched**, not the whole dataset:

```bash
lancecli take --indices 0,10,20,30,40 -c id,age --order-by age:desc examples/events.lance
```

Indexes are live-row positions in the current version, not the `id` column. After deletes/compaction, “row 5” is the fifth surviving row, not necessarily `id == 5`.

---

### `sample`

Random live-row indexes, then `take`. Default 10 rows. `--seed` makes it reproducible.

```bash
lancecli sample examples/events.lance -n 3 --seed 42 -c id,name
```

```
┏━━━━┳━━━━━━━━━┓
┃ id ┃ name    ┃
┡━━━━╇━━━━━━━━━┩
│ 40 │ user_40 │
│ 7  │ user_7  │
│ 1  │ user_1  │
└────┴─────────┘
```

With `--filter`, matching rows are loaded then sampled (still column-projected). `--order-by` sorts the sample afterwards.

---

### `tail`

Last N rows (default 10). Uses `count_rows` plus a scanner `offset`, so it does not materialize the prefix.

```bash
lancecli tail examples/events.lance -n 3 -c id,name,age
```

```
┏━━━━┳━━━━━━━━━┳━━━━━┓
┃ id ┃ name    ┃ age ┃
┡━━━━╇━━━━━━━━━╇━━━━━┩
│ 47 │ user_47 │ 27  │
│ 48 │ user_48 │ 28  │
│ 49 │ user_49 │ 29  │
└────┴─────────┴─────┘
```

`--filter` applies first: `tail --filter "city = 'TLV'"` is the last N TLV rows in scan order, not the last N of the whole file.

---

### `csv` / `jsonl`

Stream Arrow record batches to stdout. They never load the whole table into memory. **Default is every matching row** (`-n` is optional). Prefer `jsonl` for vectors, lists, and nested types.

```bash
lancecli csv examples/events.lance -n 3 -c id,name,age,city
```

```
id,name,age,city
0,user_0,20,TLV
1,user_1,21,NYC
2,user_2,22,BER
```

```bash
lancecli jsonl examples/events.lance -n 2 -c id,name,embedding
lancecli jsonl examples/events.lance -n 1 -c id,embedding --full
```

```
{"id": 0, "name": "user_0", "embedding": [0.0, 1.0, "… (4 items)"]}
{"id": 1, "name": "user_1", "embedding": [4.0, 5.0, "… (4 items)"]}
{"id": 0, "embedding": [0.0, 1.0, 2.0, 3.0]}
```

Same scan flags as `show`: `-c`, `--filter`, `--order-by`, `-n`, `--full`.

---

### `schema`

Arrow schema of the opened version:

```bash
lancecli schema examples/events.lance
```

```
id: int64
name: string
age: int64
city: string
embedding: fixed_size_list<item: float>[4]
```

`--physical` prints the Lance-native physical schema (field ids, encodings). `--format json` is available.

---

### `inspect`

Verbose dump: URI, version, row counts, fragment count, index flag, then every column name and the full schema. Use when `stat` is not enough.

```bash
lancecli inspect examples/events.lance
```

```
############ dataset ############
uri: examples/events.lance
version: 1
latest_version: 1
num_rows: 50
num_deleted_rows: 0
num_fragments: 1
num_columns: 5
has_index: false
data_storage_version: 2.1

############ columns ############
id
name
age
city
embedding

############ schema ############
id: int64
name: string
age: int64
city: string
embedding: fixed_size_list<item: float>[4]
```

---

### `count`

Unfiltered count is metadata-only. `--filter` goes through the scanner (and can use a scalar index).

```bash
lancecli count examples/events.lance
lancecli count examples/events.lance --filter "age > 40"
```

```
50
19
```

---

### `freq`

Value counts for **one** column (`-c` / `--column` here is that column, not a projection list). Good for class balance / enum sanity. Default: top 20 values.

```bash
lancecli freq examples/events.lance -c city
```

```
city  ·  50 rows
┏━━━━━━━┳━━━━━━━┳━━━━━━━━━┓
┃ value ┃ count ┃ percent ┃
┡━━━━━━━╇━━━━━━━╇━━━━━━━━━┩
│ TLV   │    13 │   26.0% │
│ NYC   │    13 │   26.0% │
│ BER   │    12 │   24.0% │
│ LON   │    12 │   24.0% │
└───────┴───────┴─────────┘
```

`--filter` restricts the population first (`freq -c city --filter "age > 40"`). `-n` caps how many distinct values are printed.

---

### `versions`

Lance time travel. Each write creates a new version; `show --version N` opens that snapshot.

```bash
lancecli versions examples/events.lance
```

```
┏━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ version ┃ timestamp                  ┃ metadata                  ┃
┡━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ 1       │ 2026-09-03 09:48:02.207822 │ {'total_rows': '50', …}   │
└─────────┴────────────────────────────┴───────────────────────────┘
```

Then:

```bash
lancecli show examples/events.lance --version 1 -n 3 -c id,name
```

`--tag` and `--asof` are the other time-travel knobs (only one of `--version` / `--tag` / `--asof`).

---

### `fragments`

Physical layout: one row per fragment, with physical rows, deletions, live rows, and data-file names. Many tiny fragments or a high deleted % are a reason to compact; `stat` already hints at that.

```bash
lancecli fragments examples/events.lance
```

```
┏━━━━┳━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━┓
┃ id ┃ physical_rows ┃ num_deletions ┃ num_rows ┃ files                ┃
┡━━━━╇━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━┩
│ 0  │ 50            │ 0             │ 50       │ 1000001000001011011… │
└────┴───────────────┴───────────────┴──────────┴──────────────────────┘
```

---

### `indices`

Lists vector, full-text, and scalar indexes. The demo file has none:

```bash
lancecli indices examples/events.lance
```

```
(no indices)
```

When indexes exist, `stat` summarizes them on one line and suggests using `--filter` / `--order-by` on those columns.

---


### URI

Last positional argument (flags may sit before or after it).

| Form | Example |
|---|---|
| Local dataset directory | `examples/events.lance` |
| S3 / S3-compatible | `s3://bucket/path/events.lance` |

Must be the **dataset directory** (contains `_versions/` or `data/`), not a single `.lance` fragment file inside `data/`.

### Dataset (time travel)

Only **one** of these per invocation:

| Flag | Type | Meaning |
|---|---|---|
| `--version N` | int | Open dataset version `N`. |
| `--tag NAME` | str | Open the version that tag points at. |
| `--asof STAMP` | str | Latest version at or before this timestamp (ISO-8601 / RFC 3339, as accepted by pylance). |

Default: latest version. `versions` lists history; it does not take these flags.

### Scan

| Flag | Default | Meaning |
|---|---|---|
| `-c` / `--columns` | all columns | Comma-separated projection: `id,name,age`. Spaces around commas are ignored. **Required on wide tables.** On `freq` this flag is `--column` (one name), not a list. |
| `--filter EXPR` | none | SQL predicate pushed into the Lance scanner, e.g. `age > 40`, `city = 'TLV'`, `age > 18 AND city = 'NYC'`. Uses a scalar index when one exists on the column. |
| `--order-by SPEC` | scan order | `col`, `col:desc`, or `age:desc,id`. Directions: `asc` / `ascending` / `a` (default), `desc` / `descending` / `d`. On `show`/`csv`/`jsonl`/`tail` this is scanner `order_by`. On `take`/`sample` the already-fetched table is sorted. |
| `-n` / `--head` | see below | Max rows. **`show` / `sample` / `tail`: 10.** **`csv` / `jsonl`: all matching rows.** **`freq`: top 20 values.** Negative (e.g. `-n -1`) means all rows, matching parquet-tools. |
| `-i` / `--indices` | (required on `take`) | Live-row positions: `0`, `-1`, `2:5`, `0,10,20`, `::10`, `0,2:5,-1`. Python slices; stop is exclusive. Out of range is an error. Not the `id` column. |
| `--seed N` | random | `sample` only. Same seed ⇒ same rows. |

### Output

| Flag | Default | Meaning |
|---|---|---|
| `-f` / `--format` | command-dependent | See matrix below. |
| `--full` | off | Do not truncate vectors, lists, blobs, or long strings. |
| `--physical` | off | `schema` only: Lance-native physical schema (field ids, encodings). |

**`--format` values per command**

| Command | Default | Allowed |
|---|---|---|
| `show`, `take`, `sample`, `tail` | `table` | `table`, `csv`, `jsonl`, `json` |
| `csv` / `jsonl` | (implicit) | n/a — always that encoding |
| `stat`, `freq`, `versions`, `fragments`, `indices` | `table` | `table`, `json` (`text` accepted as an alias of `table`) |
| `schema`, `inspect` | `text` | `text`, `json` (`table` accepted as an alias of `text`) |

`json` for row commands is one JSON array of objects (loads the printed table). `jsonl` is one object per line and streams. `csv` writes a header then records; embeddings are stringified.

Truncation (unless `--full`): lists preview 2 items; strings longer than 80 characters are clipped; blobs become `<binary …>`.

Unbounded `csv`/`jsonl` to a TTY with more than 10,000 matching rows prints a stderr warning; pass `-n` or redirect.

### Storage flags (optional — env is enough)

| Flag | Meaning |
|---|---|
| `--endpoint-url URL` | S3-compatible endpoint. Overrides `AWS_ENDPOINT_URL` / `AWS_ENDPOINT` / `AWS_ENDPOINT_URL_S3`. `http://` implies `allow_http=true` unless you set `--storage-option allow_http=false`. |
| `--aws-profile NAME` | Sets `AWS_PROFILE` for this process. Not needed if `AWS_PROFILE` is already exported. Lance cannot take a profile via `storage_options`. |
| `--storage-option KEY=VALUE` | Repeatable. Highest priority object-store knob. Examples: `region=us-east-1`, `allow_http=true`, `virtual_hosted_style_request=true`. |

Common S3 `KEY`s (passed through to pylance / [object_store](https://docs.rs/object_store/)):

| Key | Typical use |
|---|---|
| `endpoint` | Same as `--endpoint-url` |
| `region` | S3 region (dummy `us-east-1` is fine on MinIO) |
| `allow_http` | `true` for `http://` endpoints |
| `virtual_hosted_style_request` | Path-style vs virtual-hosted buckets |
| `timeout` / `connect_timeout` | Request timeouts |

Do not put access keys on the command line; use environment variables.

### Environment variables

For an **`s3://` URI**, `lancecli` reads the process environment. **CLI flags override env.** Local paths ignore AWS connection env so `show ./events.lance` stays local.

**S3 and S3-compatible (MinIO, Ceph, …)** — set these and omit storage flags:

| Variable | Role |
|---|---|
| `AWS_ACCESS_KEY_ID` | Access key (object_store reads this natively) |
| `AWS_SECRET_ACCESS_KEY` | Secret |
| `AWS_SESSION_TOKEN` | Optional session token |
| `AWS_PROFILE` | Named profile (`~/.aws/credentials`) |
| `AWS_ENDPOINT_URL` | Custom endpoint (AWS CLI name). **This is enough; you do not need `--endpoint-url`.** Also accepted: `AWS_ENDPOINT`, `AWS_ENDPOINT_URL_S3` (highest of the three). |
| `AWS_ALLOW_HTTP` | `true` to allow `http://`. If the endpoint is `http://` and this is unset, `lancecli` sets `allow_http` for you. |
| `AWS_REGION` or `AWS_DEFAULT_REGION` | Region (`us-east-1` is a common dummy on-prem) |

Real AWS S3 (no custom endpoint) usually needs only credentials or an instance role — no `lancecli` flags.

---

## Cloud storage

Cloud usage documented here is **S3 and S3-compatible stores** (including AWS). Pass an `s3://` URI; do not download files first.

**Preferred: environment only** (no `--endpoint-url`, no `--storage-option`):

```bash
export AWS_ACCESS_KEY_ID=<AWS_ACCESS_KEY_ID>
export AWS_SECRET_ACCESS_KEY=<AWS_SECRET_ACCESS_KEY>
export AWS_ENDPOINT_URL=http://s3-compatible.example   # skip on real AWS
export AWS_DEFAULT_REGION=us-east-1                    # often required on-prem
# AWS_ALLOW_HTTP=true  # optional; inferred from http:// endpoints

lancecli stat s3://bucket/path/dataset.lance
lancecli show -n 20 -c id,name,score --order-by score:desc s3://bucket/path/dataset.lance
```

Flags still work and **override** env when you need a one-off:

```bash
lancecli stat s3://bucket/events.lance --endpoint-url http://localhost:9000
lancecli show -n 5 -c id,name s3://bucket/events.lance --storage-option region=us-east-1
```

On a wide remote table, always project columns (`-c`). `take` is cheaper than `show` when you need specific row indexes.
