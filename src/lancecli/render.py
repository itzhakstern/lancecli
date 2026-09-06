from __future__ import annotations

import csv
import json
import sys
from collections.abc import Iterable
from datetime import date, datetime
from typing import Any, TextIO

import pyarrow as pa
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

MAX_STR = 80
MAX_LIST_PREVIEW = 2
HUGE_TTY_ROWS = 10_000


def console(*, file: TextIO | None = None) -> Console:
    return Console(file=file or sys.stdout, highlight=False, soft_wrap=True)


def human_int(n: int) -> str:
    return f"{n:,}"


def human_size(n: int) -> str:
    step = 1024.0
    units = ["B", "KiB", "MiB", "GiB", "TiB"]
    size = float(n)
    for unit in units:
        if size < step or unit == units[-1]:
            if unit == "B":
                return f"{int(size)} {unit}"
            return f"{size:.1f} {unit}"
        size /= step
    return f"{n} B"


def _fmt_scalar(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.4g}"
    return str(value)


def format_cell(value: Any, *, full: bool = False) -> str:
    """Stringify a value for tables and CSV, truncating wide cells by default."""
    if value is None:
        return ""
    if isinstance(value, bytes):
        if full:
            return value.hex()
        return f"<binary {human_size(len(value))}>"
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, (list, tuple)):
        if full:
            return json.dumps(to_jsonable(value, full=True), default=str)
        preview = value[:MAX_LIST_PREVIEW]
        preview_s = ", ".join(_fmt_scalar(item) for item in preview)
        if len(value) > MAX_LIST_PREVIEW:
            return f"[{preview_s}, …] ({len(value)})"
        return f"[{preview_s}]"
    if isinstance(value, dict):
        dumped = json.dumps(to_jsonable(value, full=full), default=str)
        if not full and len(dumped) > MAX_STR:
            return dumped[: MAX_STR - 1] + "…"
        return dumped
    if isinstance(value, str):
        if not full and len(value) > MAX_STR:
            return value[: MAX_STR - 1] + "…"
        return value
    return str(value)


def to_jsonable(value: Any, *, full: bool = False) -> Any:
    if value is None:
        return None
    if isinstance(value, bytes):
        if full:
            import base64

            return {"$binary": base64.b64encode(value).decode("ascii")}
        return f"<binary {human_size(len(value))}>"
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(k): to_jsonable(v, full=full) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        if full or len(value) <= MAX_LIST_PREVIEW:
            return [to_jsonable(v, full=full) for v in value]
        preview = [to_jsonable(v, full=full) for v in value[:MAX_LIST_PREVIEW]]
        preview.append(f"… ({len(value)} items)")
        return preview
    if isinstance(value, (set, frozenset)):
        return [to_jsonable(v, full=full) for v in value]
    if isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def json_ready(obj: Any) -> Any:
    """Recursively convert metadata objects into JSON-serializable values."""
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, bytes):
        return obj.hex()
    if isinstance(obj, dict):
        return {str(k): json_ready(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set, frozenset)):
        return [json_ready(v) for v in obj]
    if hasattr(obj, "isoformat"):
        try:
            return obj.isoformat()
        except Exception:
            pass
    return str(obj)


def dumps_json(obj: Any) -> str:
    return json.dumps(json_ready(obj), indent=2, ensure_ascii=False)


def print_json(obj: Any, *, file: TextIO | None = None) -> None:
    print(dumps_json(obj), file=file or sys.stdout)


def render_arrow_table(
    table: pa.Table,
    *,
    full: bool = False,
    file: TextIO | None = None,
) -> None:
    out = console(file=file)
    if table.num_rows == 0:
        out.print("(no rows)")
        return
    rich_table = Table(show_header=True, header_style="bold")
    for name in table.column_names:
        rich_table.add_column(name)
    for rec in table.to_pylist():
        rich_table.add_row(*[format_cell(rec.get(name), full=full) for name in table.column_names])
    out.print(rich_table)


def emit_rows(
    table: pa.Table,
    *,
    fmt: str,
    full: bool = False,
    file: TextIO | None = None,
) -> None:
    if fmt == "json":
        rows = [{name: rec.get(name) for name in table.column_names} for rec in table.to_pylist()]
        print_json(rows, file=file)
        return
    if fmt == "csv":
        write_csv(table.to_batches(), header_names=list(table.column_names), full=full, file=file)
        return
    if fmt == "jsonl":
        write_jsonl(table.to_batches(), full=full, file=file)
        return
    render_arrow_table(table, full=full, file=file)


def kv_table(rows: list[tuple[str, str]], *, file: TextIO | None = None) -> None:
    out = console(file=file)
    table = Table(show_header=False, box=box.SIMPLE, pad_edge=False, expand=False)
    table.add_column("metric", style="bold cyan", no_wrap=True)
    table.add_column("value")
    for key, value in rows:
        table.add_row(key, value)
    out.print(table)


def panel_title(title: str, subtitle: str | None = None, *, file: TextIO | None = None) -> None:
    out = console(file=file)
    out.print(Panel(title, subtitle=subtitle, expand=False, border_style="cyan"))


def write_csv(
    batches: Iterable[pa.RecordBatch],
    *,
    header_names: list[str] | None = None,
    full: bool = False,
    file: TextIO | None = None,
) -> None:
    out = file or sys.stdout
    writer = csv.writer(out, lineterminator="\n")
    wrote_header = False
    for batch in batches:
        if not wrote_header:
            writer.writerow(list(batch.schema.names))
            wrote_header = True
        names = list(batch.schema.names)
        for rec in batch.to_pylist():
            writer.writerow([format_cell(rec.get(name), full=full) for name in names])
    if not wrote_header:
        writer.writerow(header_names or [])


def write_jsonl(
    batches: Iterable[pa.RecordBatch],
    *,
    full: bool = False,
    file: TextIO | None = None,
) -> None:
    out = file or sys.stdout
    for batch in batches:
        names = list(batch.schema.names)
        for rec in batch.to_pylist():
            payload = {name: to_jsonable(rec.get(name), full=full) for name in names}
            print(json.dumps(payload, ensure_ascii=False, default=str), file=out)


def warn_if_huge_tty(ds: Any, *, limit: int | None, filter_expr: str | None) -> None:
    """Warn when dumping an unbounded result set to a terminal."""
    if limit is not None:
        return
    if not sys.stdout.isatty():
        return
    try:
        count = ds.count_rows(filter=filter_expr) if filter_expr else ds.count_rows()
    except Exception:
        return
    if count > HUGE_TTY_ROWS:
        print(
            f"warning: dumping {count} rows to the terminal; pass -n to limit or redirect stdout",
            file=sys.stderr,
        )


def schema_fields(schema: pa.Schema) -> list[dict[str, Any]]:
    return [
        {"name": field.name, "type": str(field.type), "nullable": field.nullable}
        for field in schema
    ]


def format_schema(schema: pa.Schema) -> str:
    return "\n".join(f"{field.name}: {field.type}" for field in schema)
