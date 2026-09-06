from __future__ import annotations

from typing import Any, TextIO

from lancecli.render import warn_if_huge_tty, write_csv
from lancecli.scan import iter_batches, normalize_limit, parse_columns, parse_order_by


def run_csv(
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
    header_names = cols or list(ds.schema.names)
    write_csv(
        iter_batches(
            ds,
            n=n,
            columns=cols,
            filter_expr=filter_expr,
            order_by=parse_order_by(order_by),
        ),
        header_names=header_names,
        full=full,
        file=file,
    )
