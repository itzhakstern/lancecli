from __future__ import annotations

import json

from lancecli.cli import app
from tests.conftest import APPEND_ROWS, N_ROWS


def test_csv_header_and_row_count(runner, dataset_uri):
    result = runner.invoke(app, ["csv", "-c", "id,name", dataset_uri])
    assert result.exit_code == 0, result.output
    lines = [line for line in result.stdout.splitlines() if line]
    assert lines[0] == "id,name"
    assert len(lines) == 1 + N_ROWS + APPEND_ROWS
    assert lines[1].startswith("0,user_0")


def test_csv_head(runner, dataset_uri):
    result = runner.invoke(app, ["csv", "-n", "3", "-c", "id", dataset_uri])
    assert result.exit_code == 0, result.output
    lines = [line for line in result.stdout.splitlines() if line]
    assert lines[0] == "id"
    assert lines[1:] == ["0", "1", "2"]


def test_jsonl_head(runner, dataset_uri):
    result = runner.invoke(app, ["jsonl", "-n", "2", "-c", "id,name", dataset_uri])
    assert result.exit_code == 0, result.output
    rows = [json.loads(line) for line in result.stdout.splitlines() if line]
    assert rows == [{"id": 0, "name": "user_0"}, {"id": 1, "name": "user_1"}]


def test_csv_filter(runner, dataset_uri):
    result = runner.invoke(app, ["csv", "-c", "id", "--filter", "id >= 98", dataset_uri])
    assert result.exit_code == 0, result.output
    lines = [line for line in result.stdout.splitlines() if line]
    assert lines[0] == "id"
    assert "98" in lines
    assert "99" in lines
    assert "0" not in lines[1:]
