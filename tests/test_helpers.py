from __future__ import annotations

import os

from lancecli.dataset import parse_storage_options
from lancecli.render import format_cell, human_size
from lancecli.scan import normalize_limit, parse_columns, parse_indices, parse_order_by


def test_parse_columns():
    assert parse_columns(None) is None
    assert parse_columns("") is None
    assert parse_columns("id, name") == ["id", "name"]


def test_normalize_limit():
    assert normalize_limit(None) is None
    assert normalize_limit(-1) is None
    assert normalize_limit(10) == 10
    assert normalize_limit(0) == 0


def test_parse_storage_options_endpoint(monkeypatch):
    for name in (
        "AWS_PROFILE",
        "AWS_ENDPOINT_URL",
        "AWS_ENDPOINT",
        "AWS_ENDPOINT_URL_S3",
        "AWS_REGION",
        "AWS_DEFAULT_REGION",
        "AWS_ALLOW_HTTP",
    ):
        monkeypatch.delenv(name, raising=False)
    opts = parse_storage_options(
        endpoint_url="http://localhost:9000",
        aws_profile="dev",
        storage_option=["region=us-east-1"],
        inherit_env=False,
    )
    assert opts["endpoint"] == "http://localhost:9000"
    assert opts["allow_http"] == "true"
    assert opts["region"] == "us-east-1"
    assert os.environ["AWS_PROFILE"] == "dev"


def test_parse_storage_options_from_env(monkeypatch):
    monkeypatch.setenv("AWS_ENDPOINT_URL", "http://minio.example")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    monkeypatch.delenv("AWS_ALLOW_HTTP", raising=False)
    monkeypatch.delenv("AWS_ENDPOINT", raising=False)
    monkeypatch.delenv("AWS_ENDPOINT_URL_S3", raising=False)
    monkeypatch.delenv("AWS_REGION", raising=False)
    opts = parse_storage_options(inherit_env=True)
    assert opts["endpoint"] == "http://minio.example"
    assert opts["region"] == "us-east-1"
    assert opts["allow_http"] == "true"


def test_parse_storage_options_cli_overrides_env(monkeypatch):
    monkeypatch.setenv("AWS_ENDPOINT_URL", "http://from-env")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    opts = parse_storage_options(
        endpoint_url="https://from-flag",
        storage_option=["region=eu-west-1"],
        inherit_env=True,
    )
    assert opts["endpoint"] == "https://from-flag"
    assert opts["region"] == "eu-west-1"
    assert "allow_http" not in opts


def test_parse_storage_options_local_ignores_env(monkeypatch):
    monkeypatch.setenv("AWS_ENDPOINT_URL", "http://should-not-apply")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    opts = parse_storage_options(inherit_env=False)
    assert opts == {}


def test_format_cell_truncates_vectors():
    values = [0.1, 0.2, 0.3, 0.4]
    text = format_cell(values, full=False)
    assert "…" in text or "..." in text or "(" in text
    assert "4" in text
    full = format_cell(values, full=True)
    assert "0.3" in full


def test_human_size():
    assert human_size(512) == "512 B"
    assert "KiB" in human_size(2048)


def test_parse_indices():
    assert parse_indices("0,2", 10) == [0, 2]
    assert parse_indices("-1", 10) == [9]
    assert parse_indices("2:5", 10) == [2, 3, 4]
    assert parse_indices("0:3,-1", 10) == [0, 1, 2, 9]


def test_parse_order_by_desc():
    orderings = parse_order_by("id:desc,name")
    assert orderings is not None
    assert len(orderings) == 2
    assert getattr(orderings[0], "column_name", None) == "id"
    assert getattr(orderings[0], "ascending") is False
    assert orderings[1] == "name"
