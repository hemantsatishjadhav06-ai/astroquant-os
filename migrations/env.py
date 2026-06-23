"""Alembic environment — pulls the DSN from astroquant settings and targets the models metadata."""
from __future__ import annotations

from alembic import context
from sqlalchemy import engine_from_config, pool

from astroquant.common.config import get_settings
from astroquant.db.models import Base

config = context.config
config.set_main_option("sqlalchemy.url", get_settings().pg_dsn)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
