from __future__ import annotations

from typing import Any, TextIO

from lancecli.render import warn_if_huge_tty, write_jsonl
from lancecli.scan import iter_batches, normalize_limit, parse_columns, parse_order_by


def run_jsonl(
    ds: Any,
    *,
    n: int | None,
    columns: str | None,
    filter_expr: str | None,
    order_by: str | None,
    full: bool,
    file: TextIO | None = None,
) -> None:
    cols = parse_columns(columns)
    limit = normalize_limit(n)
    warn_if_huge_tty(ds, limit=limit, filter_expr=filter_expr)
    write_jsonl(
        iter_batches(
            ds,
            n=n,
            columns=cols,
            filter_expr=filter_expr,
            order_by=parse_order_by(order_by),
        ),
        full=full,
        file=file,
    )
