from __future__ import annotations

from typing import Any, TextIO

from lancecli.render import format_schema, print_json, schema_fields


def run_schema(
    ds: Any,
    *,
    physical: bool,
    fmt: str,
    file: TextIO | None = None,
) -> None:
    if physical:
        payload: Any
        try:
            text = str(ds.lance_schema)
            payload = {"physical": text}
        except Exception as exc:
            payload = {"error": f"physical schema unavailable: {exc}"}
            text = payload["error"]
        if fmt == "json":
            print_json(payload, file=file)
        else:
            print(text, file=file)
        return

    schema = ds.schema
    if fmt == "json":
        print_json(schema_fields(schema), file=file)
        return
    print(format_schema(schema), file=file)
