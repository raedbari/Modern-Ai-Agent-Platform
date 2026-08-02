"""Executable upgrade/downgrade checks for the Widget Alembic revision."""

from importlib import import_module

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError

from backend.app.db.models import Agent, Tenant


def test_widget_revision_is_reversible_and_tenant_safe() -> None:
    revision = import_module(
        "backend.alembic.versions."
        "b7c8d9e0f1a2_add_widget_configuration"
    )
    assert revision.down_revision == "a1b2c3d4e5f6"

    engine = create_engine("sqlite:///:memory:")
    try:
        with engine.connect() as connection:
            connection.exec_driver_sql("PRAGMA foreign_keys=ON")
            Tenant.__table__.create(connection)
            Agent.__table__.create(connection)
            migration_context = MigrationContext.configure(connection)

            with Operations.context(migration_context):
                revision.upgrade()

            assert {
                "agent_widget_settings",
                "widget_allowed_origins",
            }.issubset(inspect(connection).get_table_names())

            connection.execute(
                text(
                    "INSERT INTO tenants (id, name) VALUES "
                    "('tenant-a', 'Tenant A'), "
                    "('tenant-b', 'Tenant B')"
                )
            )
            connection.execute(
                text(
                    "INSERT INTO agents (id, tenant_id, name) VALUES "
                    "('agent-a', 'tenant-a', 'Agent A')"
                )
            )
            with pytest.raises(IntegrityError):
                connection.execute(
                    text(
                        "INSERT INTO agent_widget_settings "
                        "(tenant_id, agent_id, public_widget_id) VALUES "
                        "('tenant-b', 'agent-a', 'wgt_cross_tenant')"
                    )
                )
            connection.rollback()

            with Operations.context(migration_context):
                revision.downgrade()

            remaining_tables = set(inspect(connection).get_table_names())
            assert "agent_widget_settings" not in remaining_tables
            assert "widget_allowed_origins" not in remaining_tables
            assert {"tenants", "agents"}.issubset(remaining_tables)
    finally:
        engine.dispose()
