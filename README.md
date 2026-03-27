# setup-util

A composable project scaffolder. Pick your stack with flags, get a working project skeleton.

```bash
setup init my_project --fastapi --sqlalchemy --postgres --alembic
```

## What it does

Generates full-stack project structures from a registry of template packs. Each pack owns one layer of the stack, declares what it provides, and what it requires. The planner validates dependencies, orders packs deterministically, and applies them via [Copier](https://copier.readthedocs.io/) — merging TOML and `.env` files across packs as it goes.

## Quick start

```bash
cd setup-cli
pip install -e .
```

```bash
# FastAPI + SQLAlchemy + Postgres + Alembic
setup init my_app --fastapi --sqlalchemy --postgres --alembic

# With Angular frontend
setup init my_app --fastapi --sqlalchemy --postgres --alembic --angular

# Preview the plan without applying
setup init my_app --fastapi --sqlalchemy --postgres --debug
```

## Available flags

| Flag | What it adds |
|---|---|
| `--fastapi` | FastAPI app with `/health` endpoint |
| `--sqlalchemy` | SQLAlchemy ORM, Base, SessionLocal |
| `--postgres` | PostgreSQL config, `docker-compose.yml`, `.env.example` |
| `--alembic` | Alembic migrations, pre-wired to your models |
| `--angular` | Angular frontend placeholder |

## Repository layout

```
setup-cli/      # CLI source + template packs
  setup_cli/    # planner, merger, CLI
  templates/    # one directory per pack
testing/        # pytest suite (unit + integration)
```

See [`setup-cli/README.md`](setup-cli/README.md) for full usage, generated project structure, and roadmap.

## Roadmap

- [x] Planner with capability-based dependency validation
- [x] 6 template packs (base, fastapi, sqlalchemy, postgres, alembic, angular stub)
- [x] TOML deep-merge and `.env` append via patch file convention
- [x] 45-test pytest suite
- [ ] Docker overlay as a standalone pack
- [ ] `--dry-run` / `--fast` modes
- [ ] Presets (`--preset fullstack-angular`)
- [ ] `.setup-cli.lock` for template versioning

## License

MIT
