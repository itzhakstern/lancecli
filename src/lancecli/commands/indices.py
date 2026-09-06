from __future__ import annotations

from typing import Any, TextIO

from rich.table import Table

from lancecli.render import console, print_json


def _index_to_dict(desc: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "name": getattr(desc, "name", None),
        "index_type": getattr(desc, "index_type", None),
        "field_names": list(getattr(desc, "field_names", []) or []),
    }
    segments = getattr(desc, "segments", None)
    if segments:
        payload["segments"] = [
            {
                "uuid": getattr(segment, "uuid", None),
                "dataset_version_at_last_update": getattr(
                    segment, "dataset_version_at_last_update", None
                ),
                "fragment_ids": sorted(getattr(segment, "fragment_ids", []) or []),
            }
            for segment in segments
        ]
    return payload


def describe_indices(ds: Any) -> list[dict[str, Any]]:
    try:
        return [_index_to_dict(desc) for desc in ds.describe_indices()]
    except Exception:
        try:
            return list(ds.list_indices())
        except Exception:
            return []


def run_indices(ds: Any, *, fmt: str, file: TextIO | None = None) -> None:
    rows = describe_indices(ds)
    if fmt == "json":
        print_json(rows, file=file)
        return

    out = console(file=file)
    if not rows:
        out.print("(no indices)")
        return
    table = Table(show_header=True, header_style="bold")
    table.add_column("name")
    table.add_column("index_type")
    table.add_column("field_names")
    for row in rows:
        fields = row.get("field_names") or row.get("fields") or []
        if isinstance(fields, str):
            field_s = fields
        else:
            field_s = ", ".join(str(f) for f in fields)
        table.add_row(
            str(row.get("name", "")),
            str(row.get("index_type") or row.get("type") or ""),
            field_s,
        )
    out.print(table)
