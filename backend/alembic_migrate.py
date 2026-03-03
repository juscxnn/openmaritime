#!/usr/bin/env python3
"""
Alembic migration runner for OpenMaritime.

Usage:
    python alembic_migrate.py upgrade        # Run all migrations
    python alembic_migrate.py upgrade +1      # Run one migration
    python alembic_migrate.py downgrade       # Rollback one migration
    python alembic_migrate.py downgrade base  # Rollback all migrations
    python alembic_migrate.py current         # Show current revision
    python alembic_migrate.py history         # Show migration history
    python alembic_migrate.py create <name>   # Create new migration
"""
import os
import sys
import asyncio

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from alembic.config import Config
from alembic import command
from sqlalchemy.ext.asyncio import create_async_engine


def get_alembic_config():
    """Get Alembic configuration."""
    alembic_cfg = Config("alembic.ini")
    
    # Override sqlalchemy.url from environment
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        # Convert sync to async driver
        if database_url.startswith("postgresql://"):
            database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        elif database_url.startswith("sqlite://"):
            database_url = database_url.replace("sqlite://", "sqlite+aiosqlite://", 1)
        alembic_cfg.set_main_option("sqlalchemy.url", database_url)
    
    return alembic_cfg


def upgrade(revision: str = "head"):
    """Run migrations forward."""
    alembic_cfg = get_alembic_config()
    command.upgrade(alembic_cfg, revision)


def downgrade(revision: str = "-1"):
    """Run migrations backward."""
    alembic_cfg = get_alembic_config()
    command.downgrade(alembic_cfg, revision)


def current():
    """Show current migration."""
    alembic_cfg = get_alembic_config()
    command.current(alembic_cfg)


def history():
    """Show migration history."""
    alembic_cfg = get_alembic_config()
    command.history(alembic_cfg)


def create(name: str, autogenerate: bool = True):
    """Create new migration."""
    alembic_cfg = get_alembic_config()
    command.revision(alembic_cfg, message=name, autogenerate=autogenerate)


def init():
    """Initialize Alembic (create versions directory)."""
    alembic_cfg = get_alembic_config()
    command.init(alembic_cfg, "backend/alembic", "versions")


async def check_connection():
    """Check database connection."""
    database_url = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/openmaritime")
    
    if database_url.startswith("postgresql"):
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    
    try:
        engine = create_async_engine(database_url, echo=False)
        async with engine.connect() as conn:
            print("Database connection successful!")
            # Check if migrations table exists
            result = await conn.execute(
                "SELECT tablename FROM pg_tables WHERE schemaname = 'public' AND tablename = 'alembic_version'"
            )
            tables = result.fetchall()
            if tables:
                result = await conn.execute("SELECT * FROM alembic_version")
                version = result.fetchone()
                if version:
                    print(f"Current migration: {version[0]}")
                else:
                    print("No migrations applied yet.")
            else:
                print("Alembic not initialized. Run 'alembic upgrade head' first.")
        await engine.dispose()
    except Exception as e:
        print(f"Database connection failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    action = sys.argv[1]
    
    if action == "upgrade":
        revision = sys.argv[2] if len(sys.argv) > 2 else "head"
        upgrade(revision)
    elif action == "downgrade":
        revision = sys.argv[2] if len(sys.argv) > 2 else "-1"
        downgrade(revision)
    elif action == "current":
        current()
    elif action == "history":
        history()
    elif action == "create":
        if len(sys.argv) < 3:
            print("Usage: python alembic_migrate.py create <migration_name>")
            sys.exit(1)
        name = sys.argv[2]
        autogenerate = "--autogenerate" not in sys.argv or True
        create(name, autogenerate)
    elif action == "init":
        init()
    elif action == "check":
        asyncio.run(check_connection())
    else:
        print(f"Unknown action: {action}")
        print(__doc__)
        sys.exit(1)
