# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Setup & Running

```bash
cd setup-cli
pip install -e .
```

Run the CLI:
```bash
setup init <project-name> --fastapi --sqlalchemy --postgres --alembic
```

All flags: `--fastapi`, `--sqlalchemy`, `--postgres`, `--alembic`, `--angular`, `--force`, `--debug`

## Testing

The `testing/` directory is currently empty — no tests exist yet. When added, they'll use pytest and run from `testing/`.

## Architecture

The project is a composable scaffolder. The two key concepts are **Packs** and the **Planner**.

### Packs (`setup-cli/templates/`)

Each subdirectory is a Copier template pack. A pack has:
- A `role` — the slot it fills (base, backend, orm, db, migrations, frontend)
- `provides` — capabilities it makes available (e.g. `{"backend"}`)
- `requires` — capabilities it needs from earlier packs (e.g. `{"orm"}`)

Template files use Jinja2 (`.jinja` extension) and receive `project_name` as the only variable.

### Planner (`setup-cli/setup_cli/planner.py`)

`resolve_plan(flags)` converts CLI flags into an ordered list of Packs. The flow:
1. Flags map to pack names (e.g. `--fastapi` → `"backend-fastapi"`)
2. `_order_by_role()` enforces a fixed ordering: base → backend → orm → db → migrations → frontend, and prevents duplicate roles
3. `validate_plan()` checks that each pack's `requires` are satisfied by earlier packs' `provides`
4. `apply_plan()` runs `copier.run_copy()` on each pack sequentially against the same destination

The registry (`_registry()`) is hardcoded in `planner.py`. Adding a new template pack means adding a new `Pack(...)` entry there.

### Dependency rules currently enforced
- `--sqlalchemy` and `--postgres` both require `--fastapi`
- `--alembic` requires `--sqlalchemy`
- Only one pack per role is allowed
