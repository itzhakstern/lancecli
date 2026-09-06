from __future__ import annotations

import json

from lancecli.cli import app
from tests.conftest import APPEND_ROWS, N_ROWS


def test_inspect_text(runner, dataset_uri):
    result = runner.invoke(app, ["inspect", dataset_uri])
    assert result.exit_code == 0, result.output
    assert "############ dataset ############" in result.stdout
    assert f"num_rows: {N_ROWS + APPEND_ROWS}" in result.stdout
    assert "version:" in result.stdout
    assert "num_fragments:" in result.stdout
    assert "id: int64" in result.stdout
    assert "embedding:" in result.stdout


def test_inspect_json(runner, dataset_uri):
    result = runner.invoke(app, ["inspect", "--format", "json", dataset_uri])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload["num_rows"] == N_ROWS + APPEND_ROWS
    assert payload["version"] >= 2
    names = [field["name"] for field in payload["schema"]]
    assert names == ["id", "name", "age", "embedding"]


def test_schema_text(runner, dataset_uri):
    result = runner.invoke(app, ["schema", dataset_uri])
    assert result.exit_code == 0, result.output
    assert "id: int64" in result.stdout
    assert "name:" in result.stdout


def test_schema_json(runner, dataset_uri):
    result = runner.invoke(app, ["schema", "--format", "json", dataset_uri])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload[0]["name"] == "id"
