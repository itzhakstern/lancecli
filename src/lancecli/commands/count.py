from __future__ import annotations

from typing import Any, TextIO

from lancecli.scan import parse_columns


def run_count(
    ds: Any,
    *,
    filter_expr: str | None,
    columns: str | None = None,
    file: TextIO | None = None,
) -> None:
    # columns is accepted for flag consistency but does not affect the count
    parse_columns(columns)
    count = ds.count_rows(filter=filter_expr) if filter_expr else ds.count_rows()
    print(count, file=file)
