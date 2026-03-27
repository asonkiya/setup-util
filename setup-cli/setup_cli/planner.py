from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from collections.abc import Iterable

from copier import run_copy

from .merger import apply_patches


@dataclass(frozen=True)
class Pack:
    """
    A template pack.

    - role: the "slot" this pack fills (backend/db/orm/etc.)
    - provides/requires: capability-based validation to keep things scalable
    """

    name: str
    template_dir: Path
    role: str
    provides: frozenset[str] = frozenset()
    requires: frozenset[str] = frozenset()


@dataclass(frozen=True)
class Flags:
    fastapi: bool = False
    sqlalchemy: bool = False
    postgres: bool = False
    alembic: bool = False
    angular: bool = False


def _templates_root() -> Path:
    root = Path(__file__).resolve().parent.parent
    return root / "templates"


def _registry() -> dict[str, Pack]:
    t = _templates_root()

    return {
        "base": Pack(
            name="base",
            template_dir=t / "base",
            role="base",
            provides=frozenset({"base"}),
        ),
        "backend-fastapi": Pack(
            name="backend-fastapi",
            template_dir=t / "backend-fastapi",
            role="backend",
            provides=frozenset({"backend"}),
        ),
        "db-sqlalchemy": Pack(
            name="db-sqlalchemy",
            template_dir=t / "db-sqlalchemy",
            role="orm",
            provides=frozenset({"orm"}),
            requires=frozenset({"backend"}),
        ),
        "db-postgres": Pack(
            name="db-postgres",
            template_dir=t / "db-postgres",
            role="db",
            provides=frozenset({"db"}),
            requires=frozenset({"backend"}),
        ),
        "alembic": Pack(
            name="alembic",
            template_dir=t / "alembic",
            role="migrations",
            provides=frozenset({"migrations"}),
            requires=frozenset({"orm"}),
        ),
        "frontend-angular": Pack(
            name="frontend-angular",
            template_dir=t / "frontend-angular",
            role="frontend",
            provides=frozenset({"frontend"}),
        ),
    }


_ROLE_ORDER: list[str] = [
    "base",
    "backend",
    "orm",
    "db",
    "migrations",
    "frontend",
]


def resolve_plan(flags: Flags) -> list[Pack]:
    """
    Convert flags -> list of packs, deterministically ordered by role.
    """
    reg = _registry()

    selected_names: set[str] = {"base"}

    if flags.fastapi:
        selected_names.add("backend-fastapi")
    if flags.sqlalchemy:
        selected_names.add("db-sqlalchemy")
    if flags.postgres:
        selected_names.add("db-postgres")
    if flags.alembic:
        selected_names.add("alembic")
    if flags.angular:
        selected_names.add("frontend-angular")

    packs = [reg[name] for name in selected_names]
    plan = _order_by_role(packs)

    validate_plan(plan)
    return plan


def _order_by_role(packs: Iterable[Pack]) -> list[Pack]:
    """
    Deterministically order packs by their role.
    Also enforces max-1 pack per role (except base, which is always single anyway).
    """
    by_role: dict[str, list[Pack]] = {}
    for p in packs:
        by_role.setdefault(p.role, []).append(p)

    for role, items in by_role.items():
        if len(items) > 1:
            names = [i.name for i in items]
            raise ValueError(
                f"Invalid selection: multiple providers for role '{role}': {names}"
            )

    ordered: list[Pack] = []
    for role in _ROLE_ORDER:
        item = by_role.get(role)
        if item:
            ordered.append(item[0])

    return ordered


def validate_plan(plan: Iterable[Pack]) -> None:
    """
    Validates capability dependencies in plan order.
    """
    provides: set[str] = set()
    plan_list = list(plan)

    for p in plan_list:
        missing = set(p.requires) - provides
        if missing:
            raise ValueError(
                f"Invalid plan: '{p.name}' requires {sorted(missing)} "
                f"but only {sorted(provides)} are provided by earlier packs."
            )
        provides |= set(p.provides)

    db_providers = [p.name for p in plan_list if "db" in p.provides]
    if len(db_providers) > 1:
        raise ValueError(
            f"Invalid plan: multiple DB providers selected: {db_providers}"
        )


def apply_plan(plan: list[Pack], dest: Path, *, force: bool) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    project_name = dest.name

    for pack in plan:
        run_copy(
            src_path=str(pack.template_dir),
            dst_path=str(dest),
            defaults=True,
            overwrite=force,
            unsafe=True,
            data={"project_name": project_name},
        )
        apply_patches(dest)
