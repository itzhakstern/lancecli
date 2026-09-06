from __future__ import annotations

import json

from lancecli.cli import app
from tests.conftest import APPEND_ROWS, N_ROWS


def test_stat_table(runner, dataset_uri):
    result = runner.invoke(app, ["stat", dataset_uri])
    assert result.exit_code == 0, result.output
    assert "rows" in result.stdout.lower()
    assert str(N_ROWS + APPEND_ROWS) in result.stdout.replace(",", "")
    assert "indices" in result.stdout.lower()
    assert "fragments" in result.stdout.lower()


def test_stat_json(runner, dataset_uri):
    result = runner.invoke(app, ["stat", "--format", "json", dataset_uri])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload["num_rows"] == N_ROWS + APPEND_ROWS
    assert payload["num_fragments"] >= 1
    assert payload["indices"]


def test_take_indices(runner, dataset_uri):
    result = runner.invoke(
        app, ["take", "--indices", "0,2", "-c", "id,name", "-f", "json", dataset_uri]
    )
    assert result.exit_code == 0, result.output
    rows = json.loads(result.stdout)
    assert [row["id"] for row in rows] == [0, 2]
    assert rows[0]["name"] == "user_0"


def test_take_slice_and_negative(runner, dataset_uri):
    result = runner.invoke(app, ["take", "-i", "0:3,-1", "-c", "id", "-f", "json", dataset_uri])
    assert result.exit_code == 0, result.output
    rows = json.loads(result.stdout)
    ids = [row["id"] for row in rows]
    assert ids[:3] == [0, 1, 2]
    assert len(ids) == 4


def test_sample_seed_is_reproducible(runner, dataset_uri):
    a = runner.invoke(
        app, ["sample", "-n", "5", "--seed", "7", "-c", "id", "-f", "json", dataset_uri]
    )
    b = runner.invoke(
        app, ["sample", "-n", "5", "--seed", "7", "-c", "id", "-f", "json", dataset_uri]
    )
    assert a.exit_code == 0, a.output
    assert b.exit_code == 0, b.output
    assert json.loads(a.stdout) == json.loads(b.stdout)
    assert len(json.loads(a.stdout)) == 5


def test_tail(runner, dataset_uri):
    result = runner.invoke(app, ["tail", "-n", "2", "-c", "id", "-f", "json", dataset_uri])
    assert result.exit_code == 0, result.output
    rows = json.loads(result.stdout)
    assert len(rows) == 2


def test_show_order_by_desc(runner, dataset_uri):
    result = runner.invoke(
        app, ["show", "-n", "3", "-c", "id", "--order-by", "id:desc", "-f", "json", dataset_uri]
    )
    assert result.exit_code == 0, result.output
    ids = [row["id"] for row in json.loads(result.stdout)]
    assert ids == sorted(ids, reverse=True)
    assert ids[0] == 99


def test_freq_age(runner, dataset_uri):
    result = runner.invoke(app, ["freq", "-c", "age", "-n", "5", "--format", "json", dataset_uri])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload["column"] == "age"
    assert payload["rows"] == N_ROWS + APPEND_ROWS
    assert payload["top"]
    assert "count" in payload["top"][0]
