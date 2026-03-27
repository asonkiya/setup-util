from __future__ import annotations

import typer
from rich.console import Console
from pathlib import Path

from .planner import Flags, resolve_plan, apply_plan, Pack

app = typer.Typer()
console = Console()


def _role_summary(plan: list[Pack]) -> str:
    """
    Return a readable "role -> provider" summary for debugging.
    """
    by_role: dict[str, str] = {}
    for p in plan:
        by_role[p.role] = p.name  # roles should be unique in the plan

    # show in a stable order (even if not present)
    roles = ["base", "backend", "orm", "db", "migrations", "frontend"]
    parts = []
    for r in roles:
        if r in by_role:
            parts.append(f"{r}={by_role[r]}")
        else:
            parts.append(f"{r}=(none)")
    return ", ".join(parts)


def _selected_flags_list(flags: Flags) -> list[str]:
    items: list[tuple[str, bool]] = [
        ("fastapi", flags.fastapi),
        ("sqlalchemy", flags.sqlalchemy),
        ("postgres", flags.postgres),
        ("alembic", flags.alembic),
        ("angular", flags.angular),
    ]
    selected = [name for name, enabled in items if enabled]
    return selected or ["(none)"]


@app.command()
def init(
    directory: str = typer.Argument(..., help="Destination directory to create."),
    fastapi: bool = typer.Option(
        False, "--fastapi", help="Use FastAPI backend template."
    ),
    sqlalchemy: bool = typer.Option(
        False, "--sqlalchemy", help="Add SQLAlchemy ORM scaffolding."
    ),
    postgres: bool = typer.Option(
        False, "--postgres", help="Add Postgres DB config scaffolding."
    ),
    alembic: bool = typer.Option(
        False, "--alembic", help="Add Alembic migrations scaffolding."
    ),
    angular: bool = typer.Option(
        False, "--angular", help="Add Angular frontend scaffold placeholder."
    ),
    force: bool = typer.Option(
        False, "--force", help="Allow overwrite when applying templates."
    ),
    debug: bool = typer.Option(
        False, "--debug", help="Print detailed plan/debug info."
    ),
):
    dest = Path(directory).resolve()

    flags = Flags(
        fastapi=fastapi,
        sqlalchemy=sqlalchemy,
        postgres=postgres,
        alembic=alembic,
        angular=angular,
    )

    plan = resolve_plan(flags)

    console.print(f"[bold]Creating:[/bold] {dest}")
    console.print("[bold]Selected:[/bold] " + ", ".join(_selected_flags_list(flags)))
    console.print("[bold]Plan:[/bold] " + " -> ".join([p.name for p in plan]))
    console.print("[bold]Roles:[/bold] " + _role_summary(plan))

    if debug:
        console.print("\n[bold]Debug details:[/bold]")
        for p in plan:
            console.print(f" - name={p.name}")
            console.print(f"   role={p.role}")
            console.print(f"   provides={sorted(p.provides)}")
            console.print(f"   requires={sorted(p.requires)}")
            console.print(f"   template_dir={p.template_dir}")

    apply_plan(plan, dest, force=force)

    console.print("[green]? Project created[/green]")


if __name__ == "__main__":
    app()

