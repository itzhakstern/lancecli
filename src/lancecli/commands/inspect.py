from __future__ import annotations

from typing import Any, TextIO

from lancecli.render import format_schema, print_json, schema_fields


def _deleted_and_fragments(ds: Any) -> tuple[int, int]:
    fragments = ds.get_fragments()
    deleted = sum(int(frag.num_deletions) for frag in fragments)
    return deleted, len(fragments)


def inspect_payload(ds: Any, uri: str) -> dict[str, Any]:
    deleted, num_fragments = _deleted_and_fragments(ds)
    schema = ds.schema
    try:
        has_index = bool(ds.has_index)
    except Exception:
        has_index = False
    try:
        data_storage_version = ds.data_storage_version
    except Exception:
        data_storage_version = None
    return {
        "uri": uri,
        "version": ds.version,
        "latest_version": getattr(ds, "latest_version", ds.version),
        "num_rows": ds.count_rows(),
        "num_deleted_rows": deleted,
        "num_fragments": num_fragments,
        "num_columns": len(schema.names),
        "has_index": has_index,
        "data_storage_version": data_storage_version,
        "schema": schema_fields(schema),
    }


def run_inspect(ds: Any, uri: str, *, fmt: str, file: TextIO | None = None) -> None:
    payload = inspect_payload(ds, uri)
    if fmt == "json":
        print_json(payload, file=file)
        return

    schema_text = format_schema(ds.schema)
    columns = "\n".join(ds.schema.names)
    text = f"""############ dataset ############
uri: {payload["uri"]}
version: {payload["version"]}
latest_version: {payload["latest_version"]}
num_rows: {payload["num_rows"]}
num_deleted_rows: {payload["num_deleted_rows"]}
num_fragments: {payload["num_fragments"]}
num_columns: {payload["num_columns"]}
has_index: {str(payload["has_index"]).lower()}
data_storage_version: {payload["data_storage_version"]}

############ columns ############
{columns}

############ schema ############
{schema_text}
"""
    print(text, end="" if text.endswith("\n") else "\n", file=file)
