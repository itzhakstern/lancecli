from __future__ import annotations

from statistics import median
from typing import Any, TextIO

from lancecli.commands.fragments import fragment_to_dict
from lancecli.commands.indices import describe_indices
from lancecli.render import human_int, human_size, kv_table, panel_title, print_json


def _data_size_bytes(fragments: list[dict[str, Any]]) -> int | None:
    total = 0
    any_known = False
    for frag in fragments:
        for data_file in frag.get("files") or []:
            size = data_file.get("size_bytes")
            if size is None:
                continue
            any_known = True
            total += int(size)
    return total if any_known else None


def _index_summary(indices: list[dict[str, Any]]) -> str:
    if not indices:
        return "none"
    parts: list[str] = []
    for row in indices:
        kind = row.get("index_type") or row.get("type") or "index"
        fields = row.get("field_names") or row.get("fields") or []
        if isinstance(fields, str):
            field_s = fields
        else:
            field_s = ", ".join(str(f) for f in fields)
        name = row.get("name") or ""
        label = f"{kind} on {field_s}" if field_s else str(kind)
        if name:
            label = f"{name} ({label})"
        parts.append(label)
    return f"{len(indices)} · " + "; ".join(parts)


def stat_payload(ds: Any, uri: str) -> dict[str, Any]:
    fragments = [fragment_to_dict(frag) for frag in ds.get_fragments()]
    live_rows = [int(f["num_rows"]) for f in fragments]
    deleted = sum(int(f["num_deletions"]) for f in fragments)
    physical = sum(int(f["physical_rows"]) for f in fragments)
    indices = describe_indices(ds)
    try:
        versions = list(ds.versions())
    except Exception:
        versions = []
    size = _data_size_bytes(fragments)
    num_rows = ds.count_rows()
    schema = ds.schema
    try:
        data_storage_version = ds.data_storage_version
    except Exception:
        data_storage_version = None
    return {
        "uri": uri,
        "version": ds.version,
        "latest_version": getattr(ds, "latest_version", ds.version),
        "num_rows": num_rows,
        "num_deleted_rows": deleted,
        "num_physical_rows": physical,
        "deleted_pct": (100.0 * deleted / physical) if physical else 0.0,
        "num_columns": len(schema.names),
        "num_fragments": len(fragments),
        "fragment_rows_min": min(live_rows) if live_rows else 0,
        "fragment_rows_max": max(live_rows) if live_rows else 0,
        "fragment_rows_median": int(median(live_rows)) if live_rows else 0,
        "data_size_bytes": size,
        "num_versions": len(versions),
        "data_storage_version": data_storage_version,
        "indices": indices,
        "index_summary": _index_summary(indices),
        "columns": list(schema.names),
    }


def _fragment_phrase(payload: dict[str, Any]) -> str:
    n = payload["num_fragments"]
    if n == 0:
        return "0"
    if payload["fragment_rows_min"] == payload["fragment_rows_max"]:
        return f"{human_int(n)}  ({human_int(payload['fragment_rows_min'])} rows each)"
    return (
        f"{human_int(n)}  (min {human_int(payload['fragment_rows_min'])}, "
        f"max {human_int(payload['fragment_rows_max'])}, "
        f"median {human_int(payload['fragment_rows_median'])})"
    )


def _hints(payload: dict[str, Any]) -> list[str]:
    hints: list[str] = []
    if payload["num_deleted_rows"] and payload["deleted_pct"] >= 10:
        hints.append(
            f"{payload['deleted_pct']:.0f}% of physical rows are deleted — "
            "compaction would reclaim space."
        )
    if payload["num_fragments"] >= 8:
        hints.append(
            f"{payload['num_fragments']} fragments — many small files slow scans; consider compact."
        )
    indexed = payload.get("indices") or []
    if indexed:
        fields: list[str] = []
        for row in indexed:
            raw = row.get("field_names") or row.get("fields") or []
            if isinstance(raw, str):
                fields.append(raw)
            else:
                fields.extend(str(f) for f in raw)
        if fields:
            joined = ", ".join(dict.fromkeys(fields))
            hints.append(
                f"Scalar/vector indexes on {joined}: --filter and --order-by on those "
                "columns can use them instead of a full scan."
            )
    elif payload["num_rows"] >= 100_000:
        hints.append(
            "No indexes. create_scalar_index / vector index will speed filters and search."
        )
    return hints


def run_stat(ds: Any, uri: str, *, fmt: str, file: TextIO | None = None) -> None:
    payload = stat_payload(ds, uri)
    if fmt == "json":
        print_json(payload, file=file)
        return

    size = payload["data_size_bytes"]
    size_s = human_size(size) if size is not None else "unknown"
    deleted_s = f"{human_int(payload['num_deleted_rows'])}  ({payload['deleted_pct']:.1f}%)"
    version_s = f"{payload['version']}  (latest {payload['latest_version']})"
    format_s = (
        f"Lance {payload['data_storage_version']}" if payload["data_storage_version"] else "Lance"
    )

    panel_title(payload["uri"], subtitle="dataset summary", file=file)
    kv_table(
        [
            ("rows", human_int(payload["num_rows"])),
            ("deleted", deleted_s),
            ("columns", human_int(payload["num_columns"])),
            ("fragments", _fragment_phrase(payload)),
            ("data size", size_s),
            ("version", version_s),
            ("format", format_s),
            ("versions", human_int(payload["num_versions"])),
            ("indices", payload["index_summary"]),
        ],
        file=file,
    )
    hints = _hints(payload)
    if hints:
        from lancecli.render import console

        out = console(file=file)
        for hint in hints:
            out.print(f"[dim]{hint}[/dim]")
