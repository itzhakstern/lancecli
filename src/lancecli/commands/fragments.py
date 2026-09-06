from __future__ import annotations

from typing import Any, TextIO

from rich.table import Table

from lancecli.render import console, print_json


def _file_dict(data_file: Any) -> dict[str, Any]:
    return {
        "path": str(data_file.path),
        "fields": list(getattr(data_file, "fields", []) or []),
        "size_bytes": getattr(data_file, "file_size_bytes", None),
    }


def fragment_to_dict(frag: Any) -> dict[str, Any]:
    meta = frag.metadata
    files = [_file_dict(data_file) for data_file in meta.files]
    physical = int(frag.physical_rows)
    deletions = int(frag.num_deletions)
    return {
        "id": frag.fragment_id,
        "physical_rows": physical,
        "num_deletions": deletions,
        "num_rows": physical - deletions,
        "files": files,
    }


def run_fragments(ds: Any, *, fmt: str, file: TextIO | None = None) -> None:
    rows = [fragment_to_dict(frag) for frag in ds.get_fragments()]
    if fmt == "json":
        print_json(rows, file=file)
        return

    out = console(file=file)
    if not rows:
        out.print("(no fragments)")
        return
    table = Table(show_header=True, header_style="bold")
    table.add_column("id")
    table.add_column("physical_rows")
    table.add_column("num_deletions")
    table.add_column("num_rows")
    table.add_column("files")
    for row in rows:
        paths = ", ".join(f["path"] for f in row["files"])
        table.add_row(
            str(row["id"]),
            str(row["physical_rows"]),
            str(row["num_deletions"]),
            str(row["num_rows"]),
            paths,
        )
    out.print(table)
