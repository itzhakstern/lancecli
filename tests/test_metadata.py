from __future__ import annotations

import json

from lancecli.cli import app
from tests.conftest import APPEND_ROWS, N_ROWS


def test_count(runner, dataset_uri):
    result = runner.invoke(app, ["count", dataset_uri])
    assert result.exit_code == 0, result.output
    assert result.stdout.strip() == str(N_ROWS + APPEND_ROWS)


def test_count_filter(runner, dataset_uri):
    result = runner.invoke(app, ["count", "--filter", "id >= 90", dataset_uri])
    assert result.exit_code == 0, result.output
    assert result.stdout.strip() == "10"


def test_versions(runner, dataset_uri):
    result = runner.invoke(app, ["versions", "--format", "json", dataset_uri])
    assert result.exit_code == 0, result.output
    versions = json.loads(result.stdout)
    assert len(versions) >= 2


def test_fragments(runner, dataset_uri):
    result = runner.invoke(app, ["fragments", "--format", "json", dataset_uri])
    assert result.exit_code == 0, result.output
    fragments = json.loads(result.stdout)
    assert len(fragments) >= 1
    assert "physical_rows" in fragments[0]
    assert "files" in fragments[0]


def test_indices(runner, dataset_uri):
    result = runner.invoke(app, ["indices", "--format", "json", dataset_uri])
    assert result.exit_code == 0, result.output
    indices = json.loads(result.stdout)
    assert len(indices) >= 1
    names = [row.get("name") for row in indices]
    assert any(name for name in names)
