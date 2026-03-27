# setup-cli

A composable project scaffolder that generates full-stack project structures from a registry of templates. Pick your stack with flags, get a working project skeleton — no boilerplate, no friction.

```bash
setup init my_project --fastapi --sqlalchemy --postgres --alembic
```

## How it works

`setup-cli` is built on [Copier](https://copier.readthedocs.io/) and a custom planner layer. Each technology is a self-contained **template pack** that declares what it provides and what it requires. When you run `setup init`, the planner:

1. Resolves which packs to apply based on your flags
2. Validates dependencies (e.g. Alembic requires SQLAlchemy)
3. Orders the packs deterministically (base → backend → orm → db → migrations → frontend)
4. Applies each template via Copier in sequence

The result is a composable, conflict-free project scaffold every time.

## Installation

```bash
git clone https://github.com/yourusername/setup-util.git
cd setup-util/setup-cli
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Usage

```bash
setup init <project-name> [OPTIONS]
```

**Options:**

| Flag | Description |
|---|---|
| `--fastapi` | FastAPI backend with a `/health` endpoint |
| `--sqlalchemy` | SQLAlchemy ORM (requires `--fastapi`) |
| `--postgres` | PostgreSQL config + `docker-compose.yml` (requires `--fastapi`) |
| `--alembic` | Alembic migrations, pre-wired to your models (requires `--sqlalchemy`) |
| `--angular` | Angular frontend placeholder |
| `--force` | Overwrite existing files |
| `--debug` | Print detailed plan info before applying |

**Examples:**

```bash
# Minimal FastAPI project
setup init my_api --fastapi

# Full backend stack
setup init my_app --fastapi --sqlalchemy --postgres --alembic

# Full stack with frontend
setup init my_app --fastapi --sqlalchemy --postgres --alembic --angular

# Preview what will be applied
setup init my_app --fastapi --sqlalchemy --postgres --debug
```

## Template packs

| Pack | Role | Provides | Requires |
|---|---|---|---|
| `base` | `base` | `base` | — |
| `backend-fastapi` | `backend` | `backend` | — |
| `db-sqlalchemy` | `orm` | `orm` | `backend` |
| `db-postgres` | `db` | `db` | `backend` |
| `alembic` | `migrations` | `migrations` | `orm` |
| `frontend-angular` | `frontend` | `frontend` | — |

## Generated project structure

Running `setup init my_app --fastapi --sqlalchemy --postgres --alembic` produces:

```
my_app/
├── README.md
├── .gitignore
├── docker-compose.yml          # PostgreSQL 16 with health check
└── backend/
    ├── pyproject.toml          # FastAPI, Uvicorn, SQLAlchemy, psycopg, Alembic
    ├── .env.example
    └── app/
        ├── main.py             # FastAPI app with /health endpoint
        ├── core/
        │   └── config.py       # DATABASE_URL from environment
        ├── db/
        │   ├── base.py         # SQLAlchemy DeclarativeBase
        │   └── session.py      # engine + SessionLocal
        ├── models/
        │   └── __init__.py
        └── alembic/
            ├── alembic.ini
            ├── env.py          # Auto-discovery of models
            ├── script.py.mako
            └── versions/
```

## Roadmap

- [x] Core planner with dependency validation
- [x] 6 template packs (base, fastapi, sqlalchemy, postgres, alembic, angular stub)
- [x] Rich terminal output
- [ ] TOML/ENV merge/patch utilities
- [ ] Docker overlay templates
- [ ] `--dry-run` and `--fast` modes
- [ ] Test suite (pytest, golden-path smoke tests)
- [ ] Presets (`--preset fullstack-angular`, etc.)
- [ ] `.setup-cli.lock` for template versioning

## Tech stack

- [Typer](https://typer.tiangolo.com/) — CLI framework
- [Copier](https://copier.readthedocs.io/) — Template engine
- [Rich](https://rich.readthedocs.io/) — Terminal output
- [Jinja2](https://jinja.palletsprojects.com/) — Template rendering

## License

MIT
