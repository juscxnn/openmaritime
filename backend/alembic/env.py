"""
Alembic environment configuration for async SQLAlchemy.

This env.py is configured to work with async SQLAlchemy 2.0+ and
supports PostgreSQL with Row Level Security (RLS).
"""

import asyncio
import os
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config
from sqlalchemy import create_engine

from alembic import context

# Import the models Base and all models for autogenerate support
from app.models.base import Base
from app.models import (
    User,
    Fixture,
    Enrichment,
    PluginConfig,
    APIKey,
    EmailSync,
)

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Override sqlalchemy.url from environment if set
if database_url := os.getenv("DATABASE_URL"):
    # Convert sync driver to async if needed
    if database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif database_url.startswith("sqlite://"):
        database_url = database_url.replace("sqlite://", "sqlite+aiosqlite://", 1)
    config.set_main_option("sqlalchemy.url", database_url)

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Run migrations with connection."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        # Enable autogenerate for non-RLS tables
        render_as_batch=False,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations in 'online' mode with async engine."""

    # Get the async URL
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    asyncio.run(run_async_migrations())


# For SQLite during development/testing, use synchronous mode
def run_migrations_online_sync() -> None:
    """Run migrations with synchronous engine for SQLite."""
    url = config.get_main_option("sqlalchemy.url")
    
    # Use sync engine for SQLite (doesn't support RLS)
    if "sqlite" in url:
        connectable = create_engine(
            url,
            poolclass=pool.NullPool,
        )
        with connectable.connect() as connection:
            context.configure(
                connection=connection,
                target_metadata=target_metadata,
            )
            with context.begin_transaction():
                context.run_migrations()
    else:
        run_migrations_online()


if context.is_offline_mode():
    run_migrations_offline()
else:
    # Check if we're using SQLite (dev mode)
    url = config.get_main_option("sqlalchemy.url")
    if "sqlite" in url:
        run_migrations_online_sync()
    else:
        run_migrations_online()
