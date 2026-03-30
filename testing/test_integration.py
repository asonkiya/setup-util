from __future__ import annotations

from pathlib import Path

import pytest

try:
    import tomllib
except ImportError:
    import tomli as tomllib  # type: ignore[no-redef]

from setup_cli.planner import Flags, apply_plan, resolve_plan


def _plan(flags: Flags, dest: Path, force: bool = False) -> None:
    apply_plan(resolve_plan(flags), dest, force=force)


# ---------------------------------------------------------------------------
# Per-combination file/content assertions
# ---------------------------------------------------------------------------


def test_apply_base_only(tmp_dest: Path):
    _plan(Flags(), tmp_dest)
    assert (tmp_dest / "README.md").exists()
    assert (tmp_dest / ".gitignore").exists()
    assert "myproject" in (tmp_dest / "README.md").read_text()
    assert not (tmp_dest / "backend").exists()


def test_apply_fastapi(tmp_dest: Path):
    _plan(Flags(fastapi=True), tmp_dest)
    pyproject = tmp_dest / "backend" / "pyproject.toml"
    assert pyproject.exists()
    assert (tmp_dest / "backend" / "app" / "main.py").exists()
    assert (tmp_dest / "backend" / "app" / "__init__.py").exists()
    data = tomllib.loads(pyproject.read_text())
    assert data["project"]["name"] == "myproject-backend"
    deps = data["project"]["dependencies"]
    assert "fastapi>=0.110" in deps
    assert "uvicorn[standard]>=0.27" in deps
    # cross-pack deps must NOT be baked in — they come via patches
    assert "sqlalchemy>=2.0" not in deps
    assert "psycopg[binary]>=3.1" not in deps
    assert "alembic>=1.13" not in deps


def test_apply_fastapi_sqlalchemy(tmp_dest: Path):
    _plan(Flags(fastapi=True, sqlalchemy=True), tmp_dest)
    assert (tmp_dest / "backend" / "app" / "db" / "session.py").exists()
    assert (tmp_dest / "backend" / "app" / "db" / "base.py").exists()
    assert (tmp_dest / "backend" / "app" / "db" / "__init__.py").exists()
    assert (tmp_dest / "backend" / "app" / "models" / "__init__.py").exists()
    data = tomllib.loads((tmp_dest / "backend" / "pyproject.toml").read_text())
    deps = data["project"]["dependencies"]
    assert "fastapi>=0.110" in deps
    assert "sqlalchemy>=2.0" in deps


def test_apply_fastapi_postgres(tmp_dest: Path):
    _plan(Flags(fastapi=True, postgres=True), tmp_dest)
    # no --docker, so compose file should NOT be created
    assert not (tmp_dest / "docker-compose.yml").exists()
    assert (tmp_dest / "backend" / ".env.example").exists()
    assert (tmp_dest / "backend" / "app" / "core" / "config.py").exists()
    env = (tmp_dest / "backend" / ".env.example").read_text()
    assert "DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/myproject" in env
    data = tomllib.loads((tmp_dest / "backend" / "pyproject.toml").read_text())
    assert "psycopg[binary]>=3.1" in data["project"]["dependencies"]


def test_apply_docker_only(tmp_dest: Path):
    _plan(Flags(docker=True), tmp_dest)
    assert (tmp_dest / "docker-compose.yml").exists()
    assert (tmp_dest / ".dockerignore").exists()
    compose = (tmp_dest / "docker-compose.yml").read_text()
    assert "services" in compose
    assert not (tmp_dest / "backend").exists()


def test_apply_docker_fastapi_postgres(tmp_dest: Path):
    _plan(Flags(docker=True, fastapi=True, postgres=True), tmp_dest)
    assert (tmp_dest / "docker-compose.yml").exists()
    compose = (tmp_dest / "docker-compose.yml").read_text()
    assert "postgres:16" in compose
    assert "myproject_pgdata" in compose
    assert "backend" in compose
    assert "8000" in compose


def test_apply_full_stack(tmp_dest: Path):
    _plan(Flags(fastapi=True, sqlalchemy=True, postgres=True, alembic=True), tmp_dest)
    assert (tmp_dest / "backend" / "alembic.ini").exists()
    assert (tmp_dest / "backend" / "alembic" / "env.py").exists()
    assert (tmp_dest / "backend" / "alembic" / "script.py.mako").exists()
    assert (tmp_dest / "backend" / "alembic" / "versions").is_dir()
    data = tomllib.loads((tmp_dest / "backend" / "pyproject.toml").read_text())
    deps = data["project"]["dependencies"]
    assert "fastapi>=0.110" in deps
    assert "sqlalchemy>=2.0" in deps
    assert "psycopg[binary]>=3.1" in deps
    assert "alembic>=1.13" in deps
    env_py = (tmp_dest / "backend" / "alembic" / "env.py").read_text()
    assert "from app.core.config import DATABASE_URL" in env_py


def test_apply_angular_standalone(tmp_dest: Path):
    _plan(Flags(angular=True), tmp_dest)
    assert (tmp_dest / "frontend" / "README.md").exists()
    assert not (tmp_dest / "backend").exists()


def test_apply_force_false_no_crash_on_rerun(tmp_dest: Path):
    _plan(Flags(fastapi=True), tmp_dest, force=False)
    original = (tmp_dest / "backend" / "pyproject.toml").read_text()
    _plan(Flags(fastapi=True), tmp_dest, force=False)
    assert (tmp_dest / "backend" / "pyproject.toml").read_text() == original


def test_apply_force_true_restores_corrupted_file(tmp_dest: Path):
    _plan(Flags(fastapi=True), tmp_dest)
    (tmp_dest / "backend" / "pyproject.toml").write_text("this is not toml!!!")
    _plan(Flags(fastapi=True), tmp_dest, force=True)
    # should be valid TOML again
    data = tomllib.loads((tmp_dest / "backend" / "pyproject.toml").read_text())
    assert "project" in data


# ---------------------------------------------------------------------------
# Regression guard: no patch files left behind in any combination
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "flags",
    [
        Flags(),
        Flags(fastapi=True),
        Flags(fastapi=True, sqlalchemy=True),
        Flags(fastapi=True, postgres=True),
        Flags(fastapi=True, sqlalchemy=True, postgres=True, alembic=True),
        Flags(angular=True),
        Flags(docker=True),
        Flags(docker=True, fastapi=True),
        Flags(docker=True, fastapi=True, postgres=True),
        Flags(docker=True, fastapi=True, sqlalchemy=True, postgres=True, alembic=True),
    ],
)
def test_no_patch_files_remain(flags: Flags, tmp_dest: Path):
    _plan(flags, tmp_dest)
    assert list(tmp_dest.rglob("*.patch.toml")) == []
    assert list(tmp_dest.rglob("*.env.patch")) == []
