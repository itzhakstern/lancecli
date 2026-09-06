from __future__ import annotations

from typing import Any, TextIO

from lancecli.render import emit_rows
from lancecli.scan import parse_columns, parse_order_by, tail_table


def run_tail(
    ds: Any,
    *,
    n: int,
    columns: str | None,
    filter_expr: str | None,
    order_by: str | None,
    fmt: str,
    full: bool,
    file: TextIO | None = None,
) -> None:
    table = tail_table(
        ds,
        n=n,
        columns=parse_columns(columns),
        filter_expr=filter_expr,
        order_by=parse_order_by(order_by),
    )
    emit_rows(table, fmt=fmt, full=full, file=file)
