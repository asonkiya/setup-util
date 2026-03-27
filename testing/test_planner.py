from __future__ import annotations

import pytest

from setup_cli.planner import (
    Flags,
    Pack,
    _order_by_role,
    resolve_plan,
    validate_plan,
)


def test_resolve_plan_base_only():
    plan = resolve_plan(Flags())
    assert len(plan) == 1
    assert plan[0].name == "base"


def test_resolve_plan_fastapi_flag():
    plan = resolve_plan(Flags(fastapi=True))
    names = [p.name for p in plan]
    assert names == ["base", "backend-fastapi"]


def test_resolve_plan_full_stack():
    plan = resolve_plan(Flags(fastapi=True, sqlalchemy=True, postgres=True, alembic=True))
    names = [p.name for p in plan]
    assert names == ["base", "backend-fastapi", "db-sqlalchemy", "db-postgres", "alembic"]


def test_resolve_plan_role_order_is_stable():
    flags = Flags(fastapi=True, sqlalchemy=True, postgres=True, alembic=True)
    assert [p.name for p in resolve_plan(flags)] == [p.name for p in resolve_plan(flags)]


def test_validate_plan_raises_on_missing_requirement():
    # alembic requires orm, but db-sqlalchemy is absent
    from setup_cli.planner import _registry
    reg = _registry()
    plan = [reg["base"], reg["backend-fastapi"], reg["alembic"]]
    with pytest.raises(ValueError, match="requires"):
        validate_plan(plan)


def test_validate_plan_raises_on_multiple_db_providers():
    p1 = Pack(name="db-a", template_dir=__file__, role="db", provides=frozenset({"db"}))
    p2 = Pack(name="db-b", template_dir=__file__, role="db2", provides=frozenset({"db"}))
    base = Pack(name="base", template_dir=__file__, role="base", provides=frozenset({"base"}))
    with pytest.raises(ValueError, match="multiple DB providers"):
        validate_plan([base, p1, p2])


def test_order_by_role_raises_on_duplicate_role():
    p1 = Pack(name="a", template_dir=__file__, role="backend", provides=frozenset())
    p2 = Pack(name="b", template_dir=__file__, role="backend", provides=frozenset())
    with pytest.raises(ValueError, match="multiple providers"):
        _order_by_role([p1, p2])


def test_resolve_plan_alembic_without_sqlalchemy_raises():
    with pytest.raises(ValueError):
        resolve_plan(Flags(fastapi=True, alembic=True))


def test_resolve_plan_sqlalchemy_without_fastapi_raises():
    with pytest.raises(ValueError):
        resolve_plan(Flags(sqlalchemy=True))
