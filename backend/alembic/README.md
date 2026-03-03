# OpenMaritime Alembic Migrations

This directory contains the Alembic database migrations for OpenMaritime.

## Quick Start

### Prerequisites
- PostgreSQL database running
- Set `DATABASE_URL` environment variable:
  ```bash
  export DATABASE_URL="postgresql+asyncpg://postgres:password@localhost:5432/openmaritime"
  ```

### Running Migrations

Using the migration runner script:
```bash
cd backend

# Check database connection
python alembic_migrate.py check

# Run all migrations
python alembic_migrate.py upgrade

# Run one migration
python alembic_migrate.py upgrade +1

# Rollback one migration
python alembic_migrate.py downgrade

# Rollback all migrations
python alembic_migrate.py downgrade base

# Show current revision
python alembic_migrate.py current

# Show migration history
python alembic_migrate.py history

# Create new migration
python alembic_migrate.py create "add_new_field"
```

Using Alembic directly:
```bash
cd backend
alembic upgrade head
alembic current
alembic history
```

## Schema Overview

### Tables

| Table | Description |
|-------|-------------|
| `users` | User accounts with RLS support |
| `fixtures` | Maritime charter fixtures with Wake AI fields |
| `enrichments` | External data enrichments for fixtures |
| `plugin_configs` | Plugin configuration per user |
| `api_keys` | API keys for programmatic access |
| `email_syncs` | Email sync OAuth tokens |
| `regions` | Custom geographic polygons (GeoJSON) |
| `voice_notes` | Voice notes with transcription |
| `cost_tracking` | API cost tracking |

### Indexes

Key indexes for query optimization:
- `idx_fixture_user_status` - Composite index for user + status queries
- `idx_fixture_laycan` - Date range queries
- `idx_fixture_wake_score` - Wake AI sorting/filtering
- `idx_enrichment_fixture` - Enrichment lookups

### Row Level Security (RLS)

All tables have RLS policies enabled:
- Users can only see their own data
- Tenant isolation via `tenant_id`
- RLS context set via PostgreSQL session variables

### RLS Configuration

RLS uses these session variables:
- `app.current_user_id` - Current user's UUID
- `app.current_tenant_id` - Current tenant's UUID

The application sets these automatically via the `get_db_with_rls` dependency.

## Development

For SQLite development, migrations run automatically on startup.
For PostgreSQL production, always use Alembic migrations.

## Adding New Tables

1. Add model to `app/models/__init__.py`
2. Create migration:
   ```bash
   python alembic_migrate.py create "add_new_table"
   ```
3. Edit the migration file in `versions/`
4. Run migration:
   ```bash
   python alembic_migrate.py upgrade
   ```
