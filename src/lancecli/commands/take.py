from __future__ import annotations

from typing import Any, TextIO

from lancecli.render import emit_rows
from lancecli.scan import parse_columns, parse_order_by, take_table


def run_take(
    ds: Any,
    *,
    indices: str,
    columns: str | None,
    order_by: str | None,
    fmt: str,
    full: bool,
    file: TextIO | None = None,
) -> None:
    table = take_table(
        ds,
        spec=indices,
        columns=parse_columns(columns),
        order_by=parse_order_by(order_by),
    )
    emit_rows(table, fmt=fmt, full=full, file=file)
