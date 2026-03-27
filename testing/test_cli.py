from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from setup_cli.cli import app

runner = CliRunner()


def test_cli_init_smoke(tmp_path: Path):
    dest = tmp_path / "myproject"
    result = runner.invoke(app, [str(dest), "--fastapi"])
    assert result.exit_code == 0, result.output
    assert (dest / "backend" / "pyproject.toml").exists()
