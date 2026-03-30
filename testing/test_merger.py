from __future__ import annotations

from pathlib import Path

import pytest

try:
    import tomllib
except ImportError:
    import tomli as tomllib  # type: ignore[no-redef]

from setup_cli.merger import (
    _merge_toml_dicts,
    apply_patches,
    merge_env_files,
    merge_toml_files,
    merge_yaml_files,
)


# ---------------------------------------------------------------------------
# _merge_toml_dicts — pure dict logic, no filesystem
# ---------------------------------------------------------------------------


def test_merge_toml_dicts_adds_new_key():
    base = {"project": {"name": "x"}}
    patch = {"project": {"version": "1.0"}}
    result = _merge_toml_dicts(base, patch)
    assert result["project"]["name"] == "x"
    assert result["project"]["version"] == "1.0"


def test_merge_toml_dicts_overwrites_scalar():
    base = {"project": {"version": "0.1.0"}}
    patch = {"project": {"version": "2.0.0"}}
    result = _merge_toml_dicts(base, patch)
    assert result["project"]["version"] == "2.0.0"


def test_merge_toml_dicts_appends_list_dedup():
    base = {"project": {"dependencies": ["fastapi>=0.110", "uvicorn[standard]>=0.27"]}}
    patch = {"project": {"dependencies": ["sqlalchemy>=2.0", "fastapi>=0.110"]}}
    result = _merge_toml_dicts(base, patch)
    deps = result["project"]["dependencies"]
    assert deps == ["fastapi>=0.110", "uvicorn[standard]>=0.27", "sqlalchemy>=2.0"]


def test_merge_toml_dicts_list_preserves_base_order():
    base = {"deps": ["a", "b"]}
    patch = {"deps": ["c", "b"]}
    result = _merge_toml_dicts(base, patch)
    assert result["deps"] == ["a", "b", "c"]


def test_merge_toml_dicts_patch_only_key():
    base = {}
    patch = {"tool": {"uvicorn": {"workers": 4}}}
    result = _merge_toml_dicts(base, patch)
    assert result == {"tool": {"uvicorn": {"workers": 4}}}


def test_merge_toml_dicts_deep_recursion():
    base = {"a": {"b": {"c": "original"}}}
    patch = {"a": {"b": {"d": "new"}}}
    result = _merge_toml_dicts(base, patch)
    assert result["a"]["b"]["c"] == "original"
    assert result["a"]["b"]["d"] == "new"


def test_merge_toml_dicts_does_not_mutate_base():
    base = {"project": {"dependencies": ["fastapi>=0.110"]}}
    patch = {"project": {"dependencies": ["sqlalchemy>=2.0"]}}
    _merge_toml_dicts(base, patch)
    assert base["project"]["dependencies"] == ["fastapi>=0.110"]


# ---------------------------------------------------------------------------
# merge_toml_files — file-level TOML merge
# ---------------------------------------------------------------------------


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


def test_merge_toml_files_merges_dependencies(tmp_path: Path):
    base = _write(
        tmp_path / "pyproject.toml",
        '[project]\ndependencies = ["fastapi>=0.110", "uvicorn[standard]>=0.27"]\n',
    )
    patch = _write(
        tmp_path / "pyproject.patch.toml",
        '[project]\ndependencies = ["sqlalchemy>=2.0"]\n',
    )
    merge_toml_files(base, patch)
    data = tomllib.loads(base.read_text())
    assert "fastapi>=0.110" in data["project"]["dependencies"]
    assert "uvicorn[standard]>=0.27" in data["project"]["dependencies"]
    assert "sqlalchemy>=2.0" in data["project"]["dependencies"]


def test_merge_toml_files_deletes_patch_file(tmp_path: Path):
    base = _write(tmp_path / "pyproject.toml", "[project]\nname = \"x\"\n")
    patch = _write(tmp_path / "pyproject.patch.toml", "[project]\nversion = \"1.0\"\n")
    merge_toml_files(base, patch)
    assert not patch.exists()


def test_merge_toml_files_raises_if_base_missing(tmp_path: Path):
    patch = _write(tmp_path / "pyproject.patch.toml", "[project]\nname = \"x\"\n")
    with pytest.raises(FileNotFoundError, match="Was the base pack applied first"):
        merge_toml_files(tmp_path / "pyproject.toml", patch)
    # patch should survive for inspection
    assert patch.exists()


def test_merge_toml_files_real_patch_structure(tmp_path: Path):
    base = _write(
        tmp_path / "pyproject.toml",
        (
            '[project]\n'
            'name = "myproject-backend"\n'
            'version = "0.1.0"\n'
            'requires-python = ">=3.10"\n'
            'dependencies = [\n'
            '  "fastapi>=0.110",\n'
            '  "uvicorn[standard]>=0.27",\n'
            ']\n'
        ),
    )
    patch = _write(
        tmp_path / "pyproject.patch.toml",
        '[project]\ndependencies = ["sqlalchemy>=2.0"]\n',
    )
    merge_toml_files(base, patch)
    data = tomllib.loads(base.read_text())
    deps = data["project"]["dependencies"]
    assert "fastapi>=0.110" in deps
    assert "sqlalchemy>=2.0" in deps
    assert data["project"]["name"] == "myproject-backend"


# ---------------------------------------------------------------------------
# merge_env_files — .env line-based merge
# ---------------------------------------------------------------------------


def test_merge_env_files_appends_new_keys(tmp_path: Path):
    base = _write(tmp_path / ".env.example", "DATABASE_URL=postgresql://localhost/db\n")
    patch = _write(tmp_path / ".env.example.patch", "REDIS_URL=redis://localhost:6379\n")
    merge_env_files(base, patch)
    content = base.read_text()
    assert "DATABASE_URL=postgresql://localhost/db" in content
    assert "REDIS_URL=redis://localhost:6379" in content
    assert not patch.exists()


def test_merge_env_files_skips_duplicate_keys(tmp_path: Path):
    base = _write(tmp_path / ".env.example", "DATABASE_URL=old_value\n")
    patch = _write(tmp_path / ".env.example.patch", "DATABASE_URL=new_value\n")
    merge_env_files(base, patch)
    content = base.read_text()
    assert "old_value" in content
    assert "new_value" not in content
    assert not patch.exists()


def test_merge_env_files_creates_base_if_missing(tmp_path: Path):
    base = tmp_path / ".env.example"
    patch = _write(tmp_path / ".env.example.patch", "DATABASE_URL=postgresql://localhost/db\n")
    merge_env_files(base, patch)
    assert base.exists()
    assert "DATABASE_URL=postgresql://localhost/db" in base.read_text()
    assert not patch.exists()


def test_merge_env_files_adds_newline_separator(tmp_path: Path):
    base = _write(tmp_path / ".env.example", "FOO=bar")  # no trailing newline
    patch = _write(tmp_path / ".env.example.patch", "BAZ=qux\n")
    merge_env_files(base, patch)
    content = base.read_text()
    assert "FOO=bar\nBAZ=qux" in content


def test_merge_env_files_ignores_comment_lines(tmp_path: Path):
    base = _write(tmp_path / ".env.example", "DATABASE_URL=old\n")
    patch = _write(
        tmp_path / ".env.example.patch",
        "# This is a comment\nDATABASE_URL=new\n",
    )
    merge_env_files(base, patch)
    content = base.read_text()
    assert "# This is a comment" in content
    assert content.count("DATABASE_URL=") == 1
    assert "old" in content


def test_merge_env_files_handles_empty_lines(tmp_path: Path):
    base = _write(tmp_path / ".env.example", "")
    patch = _write(tmp_path / ".env.example.patch", "\nFOO=1\n\nBAR=2\n")
    merge_env_files(base, patch)
    content = base.read_text()
    assert "FOO=1" in content
    assert "BAR=2" in content


# ---------------------------------------------------------------------------
# apply_patches — directory scanner
# ---------------------------------------------------------------------------


def test_apply_patches_processes_toml_patches(tmp_path: Path):
    base = _write(
        tmp_path / "backend" / "pyproject.toml",
        '[project]\ndependencies = ["fastapi>=0.110"]\n',
    )
    _write(
        tmp_path / "backend" / "pyproject.patch.toml",
        '[project]\ndependencies = ["sqlalchemy>=2.0"]\n',
    )
    apply_patches(tmp_path)
    data = tomllib.loads(base.read_text())
    assert "sqlalchemy>=2.0" in data["project"]["dependencies"]
    assert not (tmp_path / "backend" / "pyproject.patch.toml").exists()


def test_apply_patches_processes_env_patches(tmp_path: Path):
    _write(tmp_path / "backend" / ".env.example", "FOO=1\n")
    _write(tmp_path / "backend" / ".env.example.patch", "BAR=2\n")
    apply_patches(tmp_path)
    content = (tmp_path / "backend" / ".env.example").read_text()
    assert "BAR=2" in content
    assert not (tmp_path / "backend" / ".env.example.patch").exists()


def test_apply_patches_processes_multiple_toml_patches(tmp_path: Path):
    for subdir, dep in [("a", "sqlalchemy>=2.0"), ("b", "alembic>=1.13")]:
        _write(
            tmp_path / subdir / "pyproject.toml",
            '[project]\ndependencies = ["fastapi>=0.110"]\n',
        )
        _write(
            tmp_path / subdir / "pyproject.patch.toml",
            f'[project]\ndependencies = ["{dep}"]\n',
        )
    apply_patches(tmp_path)
    for subdir, dep in [("a", "sqlalchemy>=2.0"), ("b", "alembic>=1.13")]:
        data = tomllib.loads((tmp_path / subdir / "pyproject.toml").read_text())
        assert dep in data["project"]["dependencies"]
        assert not (tmp_path / subdir / "pyproject.patch.toml").exists()


def test_apply_patches_raises_on_missing_toml_base(tmp_path: Path):
    _write(
        tmp_path / "backend" / "pyproject.patch.toml",
        '[project]\ndependencies = ["sqlalchemy>=2.0"]\n',
    )
    with pytest.raises(FileNotFoundError):
        apply_patches(tmp_path)


# ---------------------------------------------------------------------------
# merge_yaml_files — docker-compose YAML merge
# ---------------------------------------------------------------------------


def test_merge_yaml_files_merges_services(tmp_path: Path):
    base = _write(tmp_path / "docker-compose.yml", "services: {}\nvolumes: {}\n")
    patch = _write(
        tmp_path / "docker-compose.patch.yml",
        "services:\n  db:\n    image: postgres:16\n",
    )
    merge_yaml_files(base, patch)
    content = base.read_text()
    assert "postgres:16" in content
    assert not patch.exists()


def test_merge_yaml_files_deep_merge(tmp_path: Path):
    base = _write(
        tmp_path / "docker-compose.yml",
        "services:\n  db:\n    image: postgres:16\nvolumes: {}\n",
    )
    patch = _write(
        tmp_path / "docker-compose.patch.yml",
        "services:\n  backend:\n    build: ./backend\n",
    )
    merge_yaml_files(base, patch)
    content = base.read_text()
    assert "postgres:16" in content
    assert "backend" in content
    assert not patch.exists()


def test_merge_yaml_files_skips_if_base_missing(tmp_path: Path):
    patch = _write(
        tmp_path / "docker-compose.patch.yml",
        "services:\n  db:\n    image: postgres:16\n",
    )
    # should not raise — silently skips and deletes the patch
    merge_yaml_files(tmp_path / "docker-compose.yml", patch)
    assert not patch.exists()
    assert not (tmp_path / "docker-compose.yml").exists()


def test_apply_patches_processes_yaml_patches(tmp_path: Path):
    _write(tmp_path / "docker-compose.yml", "services: {}\nvolumes: {}\n")
    _write(
        tmp_path / "docker-compose.patch.yml",
        "services:\n  db:\n    image: postgres:16\n",
    )
    apply_patches(tmp_path)
    content = (tmp_path / "docker-compose.yml").read_text()
    assert "postgres:16" in content
    assert not (tmp_path / "docker-compose.patch.yml").exists()
