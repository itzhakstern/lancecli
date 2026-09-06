from __future__ import annotations

from lancecli.cli import app
from tests.conftest import N_ROWS


def test_show_default_head(runner, dataset_uri):
    result = runner.invoke(app, ["show", dataset_uri])
    assert result.exit_code == 0, result.output
    assert "user_0" in result.stdout
    assert "user_9" in result.stdout
    assert f"user_{N_ROWS - 1}" not in result.stdout
    assert "embedding" in result.stdout
    assert "…" in result.stdout or "..." in result.stdout or "(" in result.stdout


def test_show_n_and_columns(runner, dataset_uri):
    result = runner.invoke(app, ["show", "-n", "5", "-c", "id,name", dataset_uri])
    assert result.exit_code == 0, result.output
    assert "user_0" in result.stdout
    assert "user_4" in result.stdout
    assert "user_5" not in result.stdout
    assert "age" not in result.stdout.splitlines()[0] if result.stdout else True
    assert "embedding" not in result.stdout


def test_show_filter(runner, dataset_uri):
    result = runner.invoke(
        app, ["show", "-n", "20", "-c", "id,name", "--filter", "id >= 90", dataset_uri]
    )
    assert result.exit_code == 0, result.output
    assert "user_90" in result.stdout
    assert "user_0" not in result.stdout


def test_show_json_format(runner, dataset_uri):
    result = runner.invoke(app, ["show", "-n", "2", "-c", "id,name", "-f", "json", dataset_uri])
    assert result.exit_code == 0, result.output
    assert '"id"' in result.stdout
    assert '"name"' in result.stdout
