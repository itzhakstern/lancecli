from __future__ import annotations

from typing import Any, TextIO

from rich.table import Table

from lancecli.render import console, print_json


def run_versions(ds: Any, *, fmt: str, file: TextIO | None = None) -> None:
    versions = list(ds.versions())
    if fmt == "json":
        print_json(versions, file=file)
        return

    out = console(file=file)
    if not versions:
        out.print("(no versions)")
        return
    table = Table(show_header=True, header_style="bold")
    keys = list(versions[0].keys())
    for key in keys:
        table.add_column(str(key))
    for version in versions:
        table.add_row(*[str(version.get(key, "")) for key in keys])
    out.print(table)
