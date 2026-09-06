from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import lance


class LanceCliError(Exception):
    """User-facing error (missing path, bad flags, not a dataset)."""


_CLOUD_SCHEMES = ("s3://", "gs://", "az://", "abfs://", "abfss://", "hf://")


@dataclass(frozen=True)
class OpenOptions:
    uri: str
    version: int | None = None
    tag: str | None = None
    asof: str | None = None
    endpoint_url: str | None = None
    aws_profile: str | None = None
    storage_option: tuple[str, ...] = ()


def _env_first(*names: str) -> str | None:
    for name in names:
        value = os.environ.get(name)
        if value:
            return value
    return None


def parse_storage_options(
    *,
    endpoint_url: str | None = None,
    aws_profile: str | None = None,
    storage_option: list[str] | tuple[str, ...] | None = None,
    inherit_env: bool = True,
) -> dict[str, str]:
    """Build pylance ``storage_options`` from CLI flags and (optionally) env.

    Credentials (``AWS_ACCESS_KEY_ID``, ``AWS_SECRET_ACCESS_KEY``, …) are left
    in the environment — object_store reads them natively. This function only
    copies connection knobs that are easy to miss, especially ``AWS_ENDPOINT_URL``
    (AWS CLI name) which older object_store builds may not map.

    Priority, high to low: ``--storage-option`` → ``--endpoint-url`` → env.
    ``--aws-profile`` cannot go through storage_options; it sets ``AWS_PROFILE``.
    """
    opts: dict[str, str] = {}
    if inherit_env:
        endpoint = _env_first("AWS_ENDPOINT_URL_S3", "AWS_ENDPOINT_URL", "AWS_ENDPOINT")
        region = _env_first("AWS_REGION", "AWS_DEFAULT_REGION")
        allow_http = os.environ.get("AWS_ALLOW_HTTP")
        if endpoint:
            opts["endpoint"] = endpoint
        if region:
            opts["region"] = region
        if allow_http:
            opts["allow_http"] = allow_http
    if endpoint_url:
        opts["endpoint"] = endpoint_url
    for item in storage_option or ():
        if "=" not in item:
            raise LanceCliError(f"Invalid --storage-option {item!r}; expected KEY=VALUE.")
        key, value = item.split("=", 1)
        key = key.strip()
        if not key:
            raise LanceCliError(f"Invalid --storage-option {item!r}; expected KEY=VALUE.")
        opts[key] = value
    endpoint = opts.get("endpoint", "")
    if endpoint.startswith("http://") and "allow_http" not in opts:
        opts["allow_http"] = "true"
    if aws_profile:
        os.environ["AWS_PROFILE"] = aws_profile
    return opts


def _is_remote(uri: str) -> bool:
    return uri.startswith(_CLOUD_SCHEMES) or urlparse(uri).scheme in {
        "s3",
        "gs",
        "az",
        "abfs",
        "abfss",
        "hf",
        "file",
    }


def _preflight_local(uri: str) -> None:
    path = Path(uri)
    if path.is_file() and path.suffix == ".lance":
        dataset_dir = path.parent.parent if path.parent.name == "data" else None
        hint = (
            f" Pass the dataset directory instead (e.g. {dataset_dir})."
            if dataset_dir is not None
            else " Pass the dataset directory, not a fragment file."
        )
        raise LanceCliError(f"{uri} looks like a Lance data file, not a dataset.{hint}")
    if not path.exists():
        raise LanceCliError(f"Dataset not found: {uri}")


def _checkout_ref(opts: OpenOptions) -> tuple[int | str | None, str | None]:
    specified = [
        name
        for name, value in (
            ("--version", opts.version),
            ("--tag", opts.tag),
            ("--asof", opts.asof),
        )
        if value is not None
    ]
    if len(specified) > 1:
        raise LanceCliError("Specify only one of --version, --tag, or --asof.")
    if opts.tag is not None:
        return opts.tag, None
    return opts.version, opts.asof


def open_dataset(opts: OpenOptions) -> Any:
    """Open a Lance dataset, mapping failures to :class:`LanceCliError`."""
    if not _is_remote(opts.uri):
        _preflight_local(opts.uri)

    version, asof = _checkout_ref(opts)
    storage_options = parse_storage_options(
        endpoint_url=opts.endpoint_url,
        aws_profile=opts.aws_profile,
        storage_option=opts.storage_option,
        inherit_env=_is_remote(opts.uri),
    )
    kwargs: dict[str, Any] = {}
    if version is not None:
        kwargs["version"] = version
    if asof is not None:
        kwargs["asof"] = asof
    if storage_options:
        kwargs["storage_options"] = storage_options

    try:
        return lance.dataset(opts.uri, **kwargs)
    except LanceCliError:
        raise
    except Exception as exc:
        raise LanceCliError(_friendly_open_error(opts.uri, exc)) from exc


def _friendly_open_error(uri: str, exc: Exception) -> str:
    path = Path(uri)
    if path.is_dir() and not (path / "_versions").exists() and not (path / "data").exists():
        return (
            f"{uri} is not a Lance dataset (expected a directory with _versions/ or data/). {exc}"
        )
    return f"Failed to open Lance dataset {uri}: {exc}"
