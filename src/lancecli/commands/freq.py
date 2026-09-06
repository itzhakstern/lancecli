from __future__ import annotations

from collections import Counter
from typing import Any, TextIO

from rich.table import Table

from lancecli.dataset import LanceCliError
from lancecli.render import console, human_int, print_json
from lancecli.scan import parse_columns


def run_freq(
    ds: Any,
    *,
    column: str,
    n: int,
    filter_expr: str | None,
    fmt: str,
    file: TextIO | None = None,
) -> None:
    column = column.strip()
    if not column:
        raise LanceCliError("Provide --column / -c with a single column name.")
    names = set(ds.schema.names)
    if column not in names:
        raise LanceCliError(f"Unknown column {column!r}.")
    # parse_columns kept for consistency if someone passes extras
    parse_columns(column)

    counts: Counter[Any] = Counter()
    total = 0
    for batch in ds.to_batches(columns=[column], filter=filter_expr):
        for value in batch.column(0).to_pylist():
            counts[value] += 1
            total += 1

    ranked = counts.most_common(n if n > 0 else None)
    rows = []
    for value, count in ranked:
        pct = (100.0 * count / total) if total else 0.0
        rows.append({"value": value, "count": count, "percent": pct})

    payload = {"column": column, "distinct": len(counts), "rows": total, "top": rows}
    if fmt == "json":
        print_json(payload, file=file)
        return

    out = console(file=file)
    if not rows:
        out.print("(no values)")
        return
    table = Table(
        show_header=True,
        header_style="bold",
        title=f"{column}  ·  {human_int(total)} rows",
    )
    table.add_column("value")
    table.add_column("count", justify="right")
    table.add_column("percent", justify="right")
    for row in rows:
        label = "null" if row["value"] is None else str(row["value"])
        table.add_row(label, human_int(row["count"]), f"{row['percent']:.1f}%")
    if n > 0 and len(counts) > n:
        table.caption = f"showing top {n} of {human_int(len(counts))} distinct values"
    out.print(table)
