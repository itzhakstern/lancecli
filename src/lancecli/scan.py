from __future__ import annotations

import random
from collections.abc import Iterator
from typing import Any

import pyarrow as pa

from lancecli.dataset import LanceCliError


def parse_columns(columns: str | None) -> list[str] | None:
    if not columns:
        return None
    parts = [part.strip() for part in columns.split(",") if part.strip()]
    return parts or None


def parse_order_by(spec: str | None) -> list[Any] | None:
    """Parse ``age``, ``age:desc``, or ``age:desc,id`` into scanner orderings."""
    if not spec:
        return None
    from lance.dataset import ColumnOrdering

    orderings: list[Any] = []
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if ":" in part:
            name, direction = part.split(":", 1)
            name = name.strip()
            direction = direction.strip().lower()
            if not name:
                raise LanceCliError(f"Invalid --order-by {part!r}.")
            if direction in {"desc", "descending", "d"}:
                orderings.append(ColumnOrdering(name, ascending=False))
            elif direction in {"asc", "ascending", "a", ""}:
                orderings.append(ColumnOrdering(name, ascending=True))
            else:
                raise LanceCliError(
                    f"Invalid sort direction {direction!r} in {part!r}; use asc or desc."
                )
        else:
            orderings.append(part)
    return orderings or None


def order_by_sort_keys(orderings: list[Any] | None) -> list[tuple[str, str]]:
    if not orderings:
        return []
    keys: list[tuple[str, str]] = []
    for item in orderings:
        if isinstance(item, str):
            keys.append((item, "ascending"))
            continue
        name = getattr(item, "column_name", None)
        ascending = getattr(item, "ascending", True)
        if name:
            keys.append((name, "ascending" if ascending else "descending"))
    return keys


def sort_table(table: pa.Table, orderings: list[Any] | None) -> pa.Table:
    keys = order_by_sort_keys(orderings)
    if not keys:
        return table
    return table.sort_by(keys)


def normalize_limit(n: int | None) -> int | None:
    """Return a scanner limit, or ``None`` to read every matching row.

    Negative values mean "all rows" (parquet-tools used ``-1``).
    """
    if n is None or n < 0:
        return None
    return n


def scan_kwargs(
    *,
    columns: list[str] | None = None,
    filter_expr: str | None = None,
    limit: int | None = None,
    offset: int | None = None,
    order_by: list[Any] | None = None,
) -> dict[str, Any]:
    kwargs: dict[str, Any] = {}
    if columns:
        kwargs["columns"] = columns
    if filter_expr:
        kwargs["filter"] = filter_expr
    if limit is not None:
        kwargs["limit"] = limit
    if offset is not None:
        kwargs["offset"] = offset
    if order_by:
        kwargs["order_by"] = order_by
    return kwargs


def head_table(
    ds: Any,
    *,
    n: int | None,
    columns: list[str] | None = None,
    filter_expr: str | None = None,
    order_by: list[Any] | None = None,
) -> pa.Table:
    limit = normalize_limit(n)
    kwargs = scan_kwargs(columns=columns, filter_expr=filter_expr, order_by=order_by)
    if limit is None:
        return ds.to_table(**kwargs)
    return ds.head(limit, **kwargs)


def iter_batches(
    ds: Any,
    *,
    n: int | None,
    columns: list[str] | None = None,
    filter_expr: str | None = None,
    order_by: list[Any] | None = None,
) -> Iterator[pa.RecordBatch]:
    limit = normalize_limit(n)
    kwargs = scan_kwargs(columns=columns, filter_expr=filter_expr, limit=limit, order_by=order_by)
    yield from ds.to_batches(**kwargs)


def tail_table(
    ds: Any,
    *,
    n: int,
    columns: list[str] | None = None,
    filter_expr: str | None = None,
    order_by: list[Any] | None = None,
) -> pa.Table:
    total = ds.count_rows(filter=filter_expr) if filter_expr else ds.count_rows()
    take_n = min(max(n, 0), total)
    offset = max(0, total - take_n)
    kwargs = scan_kwargs(
        columns=columns,
        filter_expr=filter_expr,
        limit=take_n,
        offset=offset,
        order_by=order_by,
    )
    return ds.to_table(**kwargs)


def parse_indices(spec: str, n_rows: int) -> list[int]:
    """Parse arrs-style index lists: ``0,2:5,-1`` (Python slices, negatives)."""
    if n_rows < 0:
        raise LanceCliError("Dataset row count is negative.")
    spec = spec.strip()
    if not spec:
        raise LanceCliError("Provide --indices, e.g. 0,2:5,-1")
    out: list[int] = []
    for raw in spec.split(","):
        part = raw.strip()
        if not part:
            continue
        if ":" in part:
            out.extend(_slice_indices(part, n_rows))
        else:
            out.append(_resolve_index(part, n_rows))
    if not out:
        raise LanceCliError("Provide --indices, e.g. 0,2:5,-1")
    return out


def _resolve_index(token: str, n_rows: int) -> int:
    try:
        idx = int(token)
    except ValueError as exc:
        raise LanceCliError(f"Invalid row index {token!r}.") from exc
    if idx < 0:
        idx = n_rows + idx
    if idx < 0 or idx >= n_rows:
        raise LanceCliError(f"Row index {token} is out of range for {n_rows} rows.")
    return idx


def _slice_indices(part: str, n_rows: int) -> list[int]:
    bits = part.split(":")
    if len(bits) not in {2, 3}:
        raise LanceCliError(f"Invalid index slice {part!r}; use start:stop or start:stop:step.")

    def _parse_optional(token: str) -> int | None:
        token = token.strip()
        if token == "":
            return None
        try:
            return int(token)
        except ValueError as exc:
            raise LanceCliError(f"Invalid index slice {part!r}.") from exc

    start = _parse_optional(bits[0])
    stop = _parse_optional(bits[1])
    step = _parse_optional(bits[2]) if len(bits) == 3 else None
    sl = slice(start, stop, step)
    return list(range(n_rows)[sl])


def take_table(
    ds: Any,
    *,
    spec: str,
    columns: list[str] | None = None,
    order_by: list[Any] | None = None,
) -> pa.Table:
    n_rows = ds.count_rows()
    indices = parse_indices(spec, n_rows)
    table = ds.take(indices, columns=columns)
    return sort_table(table, order_by)


def sample_table(
    ds: Any,
    *,
    n: int,
    columns: list[str] | None = None,
    filter_expr: str | None = None,
    seed: int | None = None,
    order_by: list[Any] | None = None,
) -> pa.Table:
    if n < 0:
        raise LanceCliError("--head/-n must be >= 0")
    rng = random.Random(seed)
    if filter_expr:
        table = ds.to_table(columns=columns, filter=filter_expr)
        k = min(n, table.num_rows)
        if k == 0:
            return table.slice(0, 0)
        chosen = rng.sample(range(table.num_rows), k)
        table = table.take(chosen)
        return sort_table(table, order_by)
    total = ds.count_rows()
    k = min(n, total)
    if k == 0:
        return ds.take([], columns=columns)
    indices = rng.sample(range(total), k)
    table = ds.take(indices, columns=columns)
    return sort_table(table, order_by)
