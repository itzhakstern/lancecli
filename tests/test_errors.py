from __future__ import annotations

from lancecli.cli import app


def test_missing_dataset(runner, tmp_path):
    missing = tmp_path / "does-not-exist.lance"
    result = runner.invoke(app, ["show", str(missing)])
    assert result.exit_code == 1
    assert "not found" in result.output.lower() or "Dataset not found" in result.output
    assert "Traceback" not in result.output


def test_empty_directory_is_not_lance(runner, tmp_path):
    empty = tmp_path / "empty_dir"
    empty.mkdir()
    result = runner.invoke(app, ["inspect", str(empty)])
    assert result.exit_code == 1
    assert "Traceback" not in result.output


def test_fragment_file_rejected(runner, dataset_uri):
    from pathlib import Path

    data_dir = Path(dataset_uri) / "data"
    files = list(data_dir.glob("*.lance"))
    assert files, "expected at least one fragment file"
    result = runner.invoke(app, ["inspect", str(files[0])])
    assert result.exit_code == 1
    assert "data file" in result.output.lower() or "fragment" in result.output.lower()
    assert "Traceback" not in result.output


def test_no_args_help(runner):
    result = runner.invoke(app, [])
    assert result.exit_code == 0
    assert "show" in result.stdout
    assert "inspect" in result.stdout


def test_version_and_tag_conflict(runner, dataset_uri):
    result = runner.invoke(app, ["show", "--version", "1", "--tag", "prod", dataset_uri])
    assert result.exit_code == 1
    assert "only one" in result.output.lower()
