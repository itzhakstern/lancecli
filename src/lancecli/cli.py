from __future__ import annotations

from typing import Annotated

import typer

from lancecli import __version__
from lancecli.commands.count import run_count
from lancecli.commands.csv import run_csv
from lancecli.commands.fragments import run_fragments
from lancecli.commands.freq import run_freq
from lancecli.commands.indices import run_indices
from lancecli.commands.inspect import run_inspect
from lancecli.commands.jsonl import run_jsonl
from lancecli.commands.sample import run_sample
from lancecli.commands.schema import run_schema
from lancecli.commands.show import run_show
from lancecli.commands.stat import run_stat
from lancecli.commands.tail import run_tail
from lancecli.commands.take import run_take
from lancecli.commands.versions import run_versions
from lancecli.dataset import LanceCliError, OpenOptions, open_dataset

app = typer.Typer(
    name="lancecli",
    help=(
        "Inspect and dump Lance datasets from the command line "
        f"(lancecli {__version__}). Reads via pylance only — no DuckDB required.\n\n"
        "Examples:\n"
        "  lancecli show ./events.lance\n"
        "  lancecli stat s3://bucket/events.lance\n"
        "  lancecli take --indices 0,2:5,-1 -c id,name ./events.lance\n"
        "  lancecli show -n 20 -c id,score --order-by score:desc ./events.lance"
    ),
    no_args_is_help=False,
    add_completion=False,
    rich_markup_mode="rich",
    context_settings={"help_option_names": ["-h", "--help"]},
)


@app.callback(invoke_without_command=True)
def _root(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())
        raise typer.Exit(0)


UriArg = Annotated[
    str,
    typer.Argument(help="Lance dataset URI (local path, s3://, gs://, or az://)."),
]
VersionOpt = Annotated[
    int | None,
    typer.Option("--version", help="Open this dataset version.", rich_help_panel="Dataset"),
]
TagOpt = Annotated[
    str | None,
    typer.Option(
        "--tag",
        help="Open the version pointed at by this tag.",
        rich_help_panel="Dataset",
    ),
]
AsofOpt = Annotated[
    str | None,
    typer.Option(
        "--asof",
        help="Open the latest version at or before this timestamp.",
        rich_help_panel="Dataset",
    ),
]
ColumnsOpt = Annotated[
    str | None,
    typer.Option(
        "--columns",
        "-c",
        help="Comma-separated columns to project, e.g. id,name.",
        rich_help_panel="Scan",
    ),
]
FilterOpt = Annotated[
    str | None,
    typer.Option(
        "--filter",
        help="SQL predicate pushed into the Lance scanner.",
        rich_help_panel="Scan",
    ),
]
OrderByOpt = Annotated[
    str | None,
    typer.Option(
        "--order-by",
        help="Sort, e.g. age or age:desc,id. Pushed into the Lance scanner when possible.",
        rich_help_panel="Scan",
    ),
]
FormatOpt = Annotated[
    str,
    typer.Option(
        "--format",
        "-f",
        help="Output format.",
        rich_help_panel="Output",
    ),
]
FullOpt = Annotated[
    bool,
    typer.Option(
        "--full",
        help="Do not truncate vectors, blobs, or long strings.",
        rich_help_panel="Output",
    ),
]
EndpointOpt = Annotated[
    str | None,
    typer.Option(
        "--endpoint-url",
        help=(
            "S3-compatible endpoint. Overrides AWS_ENDPOINT_URL / AWS_ENDPOINT. "
            "Not required when those env vars are set."
        ),
        rich_help_panel="Storage",
    ),
]
ProfileOpt = Annotated[
    str | None,
    typer.Option(
        "--aws-profile",
        help="AWS profile name (sets AWS_PROFILE). Not required if AWS_PROFILE is already set.",
        rich_help_panel="Storage",
    ),
]
StorageOpt = Annotated[
    list[str] | None,
    typer.Option(
        "--storage-option",
        help="Object-store option KEY=VALUE (e.g. region=us-east-1). Repeatable. Overrides env.",
        rich_help_panel="Storage",
    ),
]
ShowHeadOpt = Annotated[
    int,
    typer.Option("--head", "-n", help="Max rows to print (default: 10).", rich_help_panel="Scan"),
]
DumpHeadOpt = Annotated[
    int | None,
    typer.Option(
        "--head",
        "-n",
        help="Max rows to print (default: all rows).",
        rich_help_panel="Scan",
    ),
]


def _open(
    uri: str,
    version: int | None,
    tag: str | None,
    asof: str | None,
    endpoint_url: str | None,
    aws_profile: str | None,
    storage_option: list[str] | None,
) -> object:
    try:
        return open_dataset(
            OpenOptions(
                uri=uri,
                version=version,
                tag=tag,
                asof=asof,
                endpoint_url=endpoint_url,
                aws_profile=aws_profile,
                storage_option=tuple(storage_option or ()),
            )
        )
    except LanceCliError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from None
    except Exception as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(code=2) from None


def _run(action) -> None:
    try:
        action()
    except LanceCliError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from None
    except typer.Exit:
        raise
    except Exception as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(code=2) from None


def _check_format(fmt: str, allowed: set[str]) -> str:
    if fmt not in allowed:
        allowed_s = ", ".join(sorted(allowed))
        typer.echo(f"error: unsupported --format {fmt!r}; expected one of: {allowed_s}", err=True)
        raise typer.Exit(code=1)
    return fmt


@app.command()
def show(
    n: ShowHeadOpt = 10,
    columns: ColumnsOpt = None,
    filter_expr: FilterOpt = None,
    order_by: OrderByOpt = None,
    fmt: FormatOpt = "table",
    full: FullOpt = False,
    version: VersionOpt = None,
    tag: TagOpt = None,
    asof: AsofOpt = None,
    endpoint_url: EndpointOpt = None,
    aws_profile: ProfileOpt = None,
    storage_option: StorageOpt = None,
    uri: UriArg = ...,
) -> None:
    """Show a human-readable preview of rows (default: first 10)."""
    fmt = _check_format(fmt, {"table", "csv", "jsonl", "json"})
    ds = _open(uri, version, tag, asof, endpoint_url, aws_profile, storage_option)
    _run(
        lambda: run_show(
            ds,
            n=n,
            columns=columns,
            filter_expr=filter_expr,
            order_by=order_by,
            fmt=fmt,
            full=full,
        )
    )


@app.command("csv")
def csv_cmd(
    n: DumpHeadOpt = None,
    columns: ColumnsOpt = None,
    filter_expr: FilterOpt = None,
    order_by: OrderByOpt = None,
    full: FullOpt = False,
    version: VersionOpt = None,
    tag: TagOpt = None,
    asof: AsofOpt = None,
    endpoint_url: EndpointOpt = None,
    aws_profile: ProfileOpt = None,
    storage_option: StorageOpt = None,
    uri: UriArg = ...,
) -> None:
    """Stream rows as CSV (header + records). Default: every matching row."""
    ds = _open(uri, version, tag, asof, endpoint_url, aws_profile, storage_option)
    _run(
        lambda: run_csv(
            ds, n=n, columns=columns, filter_expr=filter_expr, order_by=order_by, full=full
        )
    )


@app.command()
def jsonl(
    n: DumpHeadOpt = None,
    columns: ColumnsOpt = None,
    filter_expr: FilterOpt = None,
    order_by: OrderByOpt = None,
    full: FullOpt = False,
    version: VersionOpt = None,
    tag: TagOpt = None,
    asof: AsofOpt = None,
    endpoint_url: EndpointOpt = None,
    aws_profile: ProfileOpt = None,
    storage_option: StorageOpt = None,
    uri: UriArg = ...,
) -> None:
    """Stream rows as JSON Lines. Default: every matching row."""
    ds = _open(uri, version, tag, asof, endpoint_url, aws_profile, storage_option)
    _run(
        lambda: run_jsonl(
            ds, n=n, columns=columns, filter_expr=filter_expr, order_by=order_by, full=full
        )
    )


@app.command("schema")
def schema_cmd(
    physical: Annotated[
        bool,
        typer.Option("--physical", help="Print the Lance-native physical schema."),
    ] = False,
    fmt: FormatOpt = "text",
    version: VersionOpt = None,
    tag: TagOpt = None,
    asof: AsofOpt = None,
    endpoint_url: EndpointOpt = None,
    aws_profile: ProfileOpt = None,
    storage_option: StorageOpt = None,
    uri: UriArg = ...,
) -> None:
    """Print the dataset schema."""
    fmt = _check_format(fmt, {"text", "json", "table"})
    if fmt == "table":
        fmt = "text"
    ds = _open(uri, version, tag, asof, endpoint_url, aws_profile, storage_option)
    _run(lambda: run_schema(ds, physical=physical, fmt=fmt))


@app.command()
def inspect(
    fmt: FormatOpt = "text",
    version: VersionOpt = None,
    tag: TagOpt = None,
    asof: AsofOpt = None,
    endpoint_url: EndpointOpt = None,
    aws_profile: ProfileOpt = None,
    storage_option: StorageOpt = None,
    uri: UriArg = ...,
) -> None:
    """Inspect dataset metadata (version, rows, fragments, schema)."""
    fmt = _check_format(fmt, {"text", "json", "table"})
    if fmt == "table":
        fmt = "text"
    ds = _open(uri, version, tag, asof, endpoint_url, aws_profile, storage_option)
    _run(lambda: run_inspect(ds, uri, fmt=fmt))


@app.command()
def stat(
    fmt: FormatOpt = "table",
    version: VersionOpt = None,
    tag: TagOpt = None,
    asof: AsofOpt = None,
    endpoint_url: EndpointOpt = None,
    aws_profile: ProfileOpt = None,
    storage_option: StorageOpt = None,
    uri: UriArg = ...,
) -> None:
    """One-screen dataset health summary (rows, fragments, indexes, size)."""
    fmt = _check_format(fmt, {"table", "json", "text"})
    if fmt == "text":
        fmt = "table"
    ds = _open(uri, version, tag, asof, endpoint_url, aws_profile, storage_option)
    _run(lambda: run_stat(ds, uri, fmt=fmt))


@app.command()
def count(
    filter_expr: FilterOpt = None,
    version: VersionOpt = None,
    tag: TagOpt = None,
    asof: AsofOpt = None,
    endpoint_url: EndpointOpt = None,
    aws_profile: ProfileOpt = None,
    storage_option: StorageOpt = None,
    uri: UriArg = ...,
) -> None:
    """Print the number of rows (metadata-only unless --filter is set)."""
    ds = _open(uri, version, tag, asof, endpoint_url, aws_profile, storage_option)
    _run(lambda: run_count(ds, filter_expr=filter_expr))


@app.command()
def versions(
    fmt: FormatOpt = "table",
    endpoint_url: EndpointOpt = None,
    aws_profile: ProfileOpt = None,
    storage_option: StorageOpt = None,
    uri: UriArg = ...,
) -> None:
    """List dataset versions."""
    fmt = _check_format(fmt, {"table", "json", "text"})
    if fmt == "text":
        fmt = "table"
    ds = _open(uri, None, None, None, endpoint_url, aws_profile, storage_option)
    _run(lambda: run_versions(ds, fmt=fmt))


@app.command()
def fragments(
    fmt: FormatOpt = "table",
    version: VersionOpt = None,
    tag: TagOpt = None,
    asof: AsofOpt = None,
    endpoint_url: EndpointOpt = None,
    aws_profile: ProfileOpt = None,
    storage_option: StorageOpt = None,
    uri: UriArg = ...,
) -> None:
    """List fragments (physical files, row counts, deletions)."""
    fmt = _check_format(fmt, {"table", "json", "text"})
    if fmt == "text":
        fmt = "table"
    ds = _open(uri, version, tag, asof, endpoint_url, aws_profile, storage_option)
    _run(lambda: run_fragments(ds, fmt=fmt))


@app.command()
def indices(
    fmt: FormatOpt = "table",
    version: VersionOpt = None,
    tag: TagOpt = None,
    asof: AsofOpt = None,
    endpoint_url: EndpointOpt = None,
    aws_profile: ProfileOpt = None,
    storage_option: StorageOpt = None,
    uri: UriArg = ...,
) -> None:
    """List vector, full-text, and scalar indexes."""
    fmt = _check_format(fmt, {"table", "json", "text"})
    if fmt == "text":
        fmt = "table"
    ds = _open(uri, version, tag, asof, endpoint_url, aws_profile, storage_option)
    _run(lambda: run_indices(ds, fmt=fmt))


@app.command()
def take(
    indices: Annotated[
        str,
        typer.Option(
            "--indices",
            "-i",
            help="Row indexes: 0,2:5,-1 (Python slices; negatives from the end).",
            rich_help_panel="Scan",
        ),
    ],
    columns: ColumnsOpt = None,
    order_by: OrderByOpt = None,
    fmt: FormatOpt = "table",
    full: FullOpt = False,
    version: VersionOpt = None,
    tag: TagOpt = None,
    asof: AsofOpt = None,
    endpoint_url: EndpointOpt = None,
    aws_profile: ProfileOpt = None,
    storage_option: StorageOpt = None,
    uri: UriArg = ...,
) -> None:
    """Fetch specific rows by position using Lance random access (not a scan)."""
    fmt = _check_format(fmt, {"table", "csv", "jsonl", "json"})
    ds = _open(uri, version, tag, asof, endpoint_url, aws_profile, storage_option)
    _run(
        lambda: run_take(
            ds, indices=indices, columns=columns, order_by=order_by, fmt=fmt, full=full
        )
    )


@app.command()
def sample(
    n: ShowHeadOpt = 10,
    columns: ColumnsOpt = None,
    filter_expr: FilterOpt = None,
    seed: Annotated[
        int | None,
        typer.Option("--seed", help="RNG seed for a reproducible sample.", rich_help_panel="Scan"),
    ] = None,
    order_by: OrderByOpt = None,
    fmt: FormatOpt = "table",
    full: FullOpt = False,
    version: VersionOpt = None,
    tag: TagOpt = None,
    asof: AsofOpt = None,
    endpoint_url: EndpointOpt = None,
    aws_profile: ProfileOpt = None,
    storage_option: StorageOpt = None,
    uri: UriArg = ...,
) -> None:
    """Random sample of rows (Lance take on random indexes; default 10)."""
    fmt = _check_format(fmt, {"table", "csv", "jsonl", "json"})
    ds = _open(uri, version, tag, asof, endpoint_url, aws_profile, storage_option)
    _run(
        lambda: run_sample(
            ds,
            n=n,
            columns=columns,
            filter_expr=filter_expr,
            seed=seed,
            order_by=order_by,
            fmt=fmt,
            full=full,
        )
    )


@app.command()
def tail(
    n: ShowHeadOpt = 10,
    columns: ColumnsOpt = None,
    filter_expr: FilterOpt = None,
    order_by: OrderByOpt = None,
    fmt: FormatOpt = "table",
    full: FullOpt = False,
    version: VersionOpt = None,
    tag: TagOpt = None,
    asof: AsofOpt = None,
    endpoint_url: EndpointOpt = None,
    aws_profile: ProfileOpt = None,
    storage_option: StorageOpt = None,
    uri: UriArg = ...,
) -> None:
    """Show the last N rows (default: 10)."""
    fmt = _check_format(fmt, {"table", "csv", "jsonl", "json"})
    ds = _open(uri, version, tag, asof, endpoint_url, aws_profile, storage_option)
    _run(
        lambda: run_tail(
            ds, n=n, columns=columns, filter_expr=filter_expr, order_by=order_by, fmt=fmt, full=full
        )
    )


@app.command()
def freq(
    column: Annotated[
        str,
        typer.Option("--column", "-c", help="Column to count distinct values of."),
    ],
    n: Annotated[
        int,
        typer.Option("--head", "-n", help="How many top values to print (default: 20)."),
    ] = 20,
    filter_expr: FilterOpt = None,
    fmt: FormatOpt = "table",
    version: VersionOpt = None,
    tag: TagOpt = None,
    asof: AsofOpt = None,
    endpoint_url: EndpointOpt = None,
    aws_profile: ProfileOpt = None,
    storage_option: StorageOpt = None,
    uri: UriArg = ...,
) -> None:
    """Value counts for one column (class balance / enum sanity check)."""
    fmt = _check_format(fmt, {"table", "json", "text"})
    if fmt == "text":
        fmt = "table"
    ds = _open(uri, version, tag, asof, endpoint_url, aws_profile, storage_option)
    _run(lambda: run_freq(ds, column=column, n=n, filter_expr=filter_expr, fmt=fmt))


def main() -> None:
    app()


if __name__ == "__main__":
    main()
