"""Initial schema with RLS and all tables

Revision ID: 001_initial
Revises: 
Create Date: 2026-03-03

This migration creates the complete OpenMaritime schema with:
- User table with RLS support
- Fixture table with all fields and indexes
- Enrichment table
- PluginConfig table
- APIKey table
- EmailSync table
- Region table (for custom polygons via GeoJSON)
- VoiceNote table
- CostTracking table
- Row Level Security (RLS) policies
- Optimized indexes for multi-tenant queries

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ============================================
    # EXTENSIONS
    # ============================================
    
    # Enable UUID extension
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    
    # ============================================
    # ENUM TYPES
    # ============================================
    
    # Fixture status enum
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE fixture_status AS ENUM (
                'new', 'validated', 'enriched', 
                'rejected', 'archived'
            );
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    
    # Email provider enum
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE email_provider AS ENUM ('gmail', 'outlook', 'imap');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    
    # Voice note status enum
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE voice_note_status AS ENUM ('pending', 'processing', 'completed', 'failed');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    
    # ============================================
    # USER TABLE
    # ============================================
    
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('hashed_password', sa.String(255), nullable=False),
        sa.Column('full_name', sa.String(255), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_superuser', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=True),  # For multi-tenant RLS
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email')
    )
    
    # User indexes
    op.create_index('idx_users_email', 'users', ['email'])
    op.create_index('idx_users_tenant_id', 'users', ['tenant_id'])
    op.create_index('idx_users_is_active', 'users', ['is_active'])
    
    # Enable RLS on users table
    op.execute('ALTER TABLE users ENABLE ROW LEVEL SECURITY')
    
    # RLS policy for users - users can only see their own row
    op.execute("""
        CREATE POLICY users_select_policy ON users
        FOR SELECT
        USING (id = current_setting('app.current_user_id', true)::uuid 
               OR is_superuser = true)
    """)
    
    # RLS policy for users - users can only update their own row
    op.execute("""
        CREATE POLICY users_update_policy ON users
        FOR UPDATE
        USING (id = current_setting('app.current_user_id', true)::uuid 
               OR is_superuser = true)
    """)
    
    # ============================================
    # FIXTURE TABLE
    # ============================================
    
    op.create_table(
        'fixtures',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=True),  # For multi-tenant RLS
        
        # Vessel info
        sa.Column('vessel_name', sa.String(100), nullable=False),
        sa.Column('imo_number', sa.String(7), nullable=True),
        
        # Cargo info
        sa.Column('cargo_type', sa.String(100), nullable=False),
        sa.Column('cargo_quantity', sa.Float(), nullable=False, server_default='0'),
        sa.Column('cargo_unit', sa.String(10), nullable=False, server_default='MT'),
        
        # Laycan
        sa.Column('laycan_start', sa.DateTime(timezone=True), nullable=False),
        sa.Column('laycan_end', sa.DateTime(timezone=True), nullable=False),
        
        # Rate
        sa.Column('rate', sa.Float(), nullable=True),
        sa.Column('rate_currency', sa.String(3), nullable=False, server_default='USD'),
        sa.Column('rate_unit', sa.String(5), nullable=False, server_default='/mt'),
        
        # Ports
        sa.Column('port_loading', sa.String(100), nullable=False),
        sa.Column('port_discharge', sa.String(100), nullable=False),
        
        # Charterer/Broker
        sa.Column('charterer', sa.String(100), nullable=True),
        sa.Column('broker', sa.String(100), nullable=True),
        
        # Source tracking
        sa.Column('source_email_id', sa.String(255), nullable=True),
        sa.Column('source_subject', sa.String(500), nullable=True),
        
        # Status
        sa.Column('status', sa.Enum('new', 'validated', 'enriched', 'rejected', 'archived', name='fixture_status'), 
                  nullable=False, server_default='new'),
        
        # Wake AI fields
        sa.Column('wake_score', sa.Float(), nullable=True),
        sa.Column('tce_estimate', sa.Float(), nullable=True),
        sa.Column('market_diff', sa.Float(), nullable=True),
        
        # JSON data
        sa.Column('raw_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('enrichment_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    )
    
    # Composite indexes for optimized queries
    op.create_index('idx_fixture_user_status', 'fixtures', ['user_id', 'status'])
    op.create_index('idx_fixture_laycan', 'fixtures', ['laycan_start', 'laycan_end'])
    op.create_index('idx_fixture_wake_score', 'fixtures', ['wake_score'])
    op.create_index('idx_fixture_tenant_id', 'fixtures', ['tenant_id'])
    op.create_index('idx_fixture_imo', 'fixtures', ['imo_number'])
    op.create_index('idx_fixture_port_loading', 'fixtures', ['port_loading'])
    op.create_index('idx_fixture_port_discharge', 'fixtures', ['port_discharge'])
    op.create_index('idx_fixture_cargo_type', 'fixtures', ['cargo_type'])
    op.create_index('idx_fixture_created_at', 'fixtures', ['created_at'])
    
    # GIN indexes for JSONB queries
    op.execute('CREATE INDEX idx_fixture_raw_data_gin ON fixtures USING gin(raw_data jsonb_path_ops)')
    op.execute('CREATE INDEX idx_fixture_enrichment_data_gin ON fixtures USING gin(enrichment_data jsonb_path_ops)')
    
    # Enable RLS on fixtures table
    op.execute('ALTER TABLE fixtures ENABLE ROW LEVEL SECURITY')
    
    # RLS policy for fixtures - users can only see their own fixtures
    op.execute("""
        CREATE POLICY fixtures_select_policy ON fixtures
        FOR SELECT
        USING (user_id = current_setting('app.current_user_id', true)::uuid 
               OR tenant_id = current_setting('app.current_tenant_id', true)::uuid)
    """)
    
    # RLS policy for fixtures - users can only insert their own fixtures
    op.execute("""
        CREATE POLICY fixtures_insert_policy ON fixtures
        FOR INSERT
        WITH CHECK (user_id = current_setting('app.current_user_id', true)::uuid)
    """)
    
    # RLS policy for fixtures - users can only update their own fixtures
    op.execute("""
        CREATE POLICY fixtures_update_policy ON fixtures
        FOR UPDATE
        USING (user_id = current_setting('app.current_user_id', true)::uuid 
               OR tenant_id = current_setting('app.current_tenant_id', true)::uuid)
    """)
    
    # RLS policy for fixtures - users can only delete their own fixtures
    op.execute("""
        CREATE POLICY fixtures_delete_policy ON fixtures
        FOR DELETE
        USING (user_id = current_setting('app.current_user_id', true)::uuid 
               OR tenant_id = current_setting('app.current_tenant_id', true)::uuid)
    """)
    
    # ============================================
    # ENRICHMENT TABLE
    # ============================================
    
    op.create_table(
        'enrichments',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('fixture_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),  # For RLS
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=True),  # For RLS
        
        sa.Column('source', sa.String(50), nullable=False),
        sa.Column('data', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        
        sa.Column('fetched_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['fixture_id'], ['fixtures.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    )
    
    # Indexes for enrichment queries
    op.create_index('idx_enrichment_fixture', 'enrichments', ['fixture_id'])
    op.create_index('idx_enrichment_user', 'enrichments', ['user_id'])
    op.create_index('idx_enrichment_tenant', 'enrichments', ['tenant_id'])
    op.create_index('idx_enrichment_source', 'enrichments', ['source'])
    op.create_index('idx_enrichment_fetched_at', 'enrichments', ['fetched_at'])
    
    # GIN index for JSONB data
    op.execute('CREATE INDEX idx_enrichments_data_gin ON enrichments USING gin(data jsonb_path_ops)')
    
    # Enable RLS on enrichments table
    op.execute('ALTER TABLE enrichments ENABLE ROW LEVEL SECURITY')
    
    # RLS policy for enrichments
    op.execute("""
        CREATE POLICY enrichments_select_policy ON enrichments
        FOR SELECT
        USING (user_id = current_setting('app.current_user_id', true)::uuid 
               OR tenant_id = current_setting('app.current_tenant_id', true)::uuid)
    """)
    
    # ============================================
    # PLUGIN CONFIG TABLE
    # ============================================
    
    op.create_table(
        'plugin_configs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=True),
        
        sa.Column('plugin_name', sa.String(100), nullable=False),
        sa.Column('config', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('is_enabled', sa.Boolean(), nullable=False, server_default='true'),
        
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    )
    
    # Indexes
    op.create_index('idx_plugin_config_plugin_name', 'plugin_configs', ['plugin_name'])
    op.create_index('idx_plugin_config_user', 'plugin_configs', ['user_id'])
    op.create_index('idx_plugin_config_tenant', 'plugin_configs', ['tenant_id'])
    op.create_index('idx_plugin_config_is_enabled', 'plugin_configs', ['is_enabled'])
    
    # Enable RLS
    op.execute('ALTER TABLE plugin_configs ENABLE ROW LEVEL SECURITY')
    
    op.execute("""
        CREATE POLICY plugin_configs_select_policy ON plugin_configs
        FOR SELECT
        USING (user_id = current_setting('app.current_user_id', true)::uuid 
               OR tenant_id = current_setting('app.current_tenant_id', true)::uuid)
    """)
    
    # ============================================
    # API KEY TABLE
    # ============================================
    
    op.create_table(
        'api_keys',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=True),
        
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('key_hash', sa.String(255), nullable=False),
        sa.Column('permissions', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    )
    
    # Indexes
    op.create_index('idx_api_key_user', 'api_keys', ['user_id'])
    op.create_index('idx_api_key_tenant', 'api_keys', ['tenant_id'])
    op.create_index('idx_api_key_key_hash', 'api_keys', ['key_hash'])
    op.create_index('idx_api_key_expires', 'api_keys', ['expires_at'])
    
    # Enable RLS
    op.execute('ALTER TABLE api_keys ENABLE ROW LEVEL SECURITY')
    
    op.execute("""
        CREATE POLICY api_keys_select_policy ON api_keys
        FOR SELECT
        USING (user_id = current_setting('app.current_user_id', true)::uuid 
               OR tenant_id = current_setting('app.current_tenant_id', true)::uuid)
    """)
    
    # ============================================
    # EMAIL SYNC TABLE
    # ============================================
    
    op.create_table(
        'email_syncs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=True),
        
        sa.Column('provider', sa.Enum('gmail', 'outlook', 'imap', name='email_provider'), nullable=False),
        sa.Column('access_token', sa.Text(), nullable=False),
        sa.Column('refresh_token', sa.Text(), nullable=True),
        sa.Column('token_expires_at', sa.DateTime(timezone=True), nullable=True),
        
        sa.Column('last_sync_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    )
    
    # Indexes
    op.create_index('idx_email_sync_user', 'email_syncs', ['user_id'])
    op.create_index('idx_email_sync_tenant', 'email_syncs', ['tenant_id'])
    op.create_index('idx_email_sync_provider', 'email_syncs', ['provider'])
    op.create_index('idx_email_sync_is_active', 'email_syncs', ['is_active'])
    
    # Enable RLS
    op.execute('ALTER TABLE email_syncs ENABLE ROW LEVEL SECURITY')
    
    op.execute("""
        CREATE POLICY email_syncs_select_policy ON email_syncs
        FOR SELECT
        USING (user_id = current_setting('app.current_user_id', true)::uuid 
               OR tenant_id = current_setting('app.current_tenant_id', true)::uuid)
    """)
    
    # ============================================
    # REGION TABLE (Custom Polygons via GeoJSON)
    # ============================================
    
    op.create_table(
        'regions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=True),
        
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('region_type', sa.String(50), nullable=False),  # 'loading_zone', 'discharge_zone', 'transit'
        # GeoJSON polygon stored as JSONB
        sa.Column('polygon', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('color', sa.String(7), nullable=True),  # Hex color
        
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    )
    
    # Indexes
    op.create_index('idx_region_user', 'regions', ['user_id'])
    op.create_index('idx_region_tenant', 'regions', ['tenant_id'])
    op.create_index('idx_region_type', 'regions', ['region_type'])
    
    # Enable RLS
    op.execute('ALTER TABLE regions ENABLE ROW LEVEL SECURITY')
    
    op.execute("""
        CREATE POLICY regions_select_policy ON regions
        FOR SELECT
        USING (user_id = current_setting('app.current_user_id', true)::uuid 
               OR tenant_id = current_setting('app.current_tenant_id', true)::uuid)
    """)
    
    # ============================================
    # VOICE NOTE TABLE
    # ============================================
    
    op.create_table(
        'voice_notes',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=True),
        
        sa.Column('fixture_id', postgresql.UUID(as_uuid=True), nullable=True),
        
        sa.Column('file_path', sa.String(500), nullable=False),
        sa.Column('duration_seconds', sa.Float(), nullable=True),
        
        sa.Column('transcription', sa.Text(), nullable=True),
        sa.Column('transcription_model', sa.String(50), nullable=True),
        
        sa.Column('status', sa.Enum('pending', 'processing', 'completed', 'failed', name='voice_note_status'),
                  nullable=False, server_default='pending'),
        sa.Column('error_message', sa.Text(), nullable=True),
        
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['fixture_id'], ['fixtures.id'], ondelete='SET NULL'),
    )
    
    # Indexes
    op.create_index('idx_voice_note_user', 'voice_notes', ['user_id'])
    op.create_index('idx_voice_note_tenant', 'voice_notes', ['tenant_id'])
    op.create_index('idx_voice_note_fixture', 'voice_notes', ['fixture_id'])
    op.create_index('idx_voice_note_status', 'voice_notes', ['status'])
    op.create_index('idx_voice_note_created_at', 'voice_notes', ['created_at'])
    
    # Enable RLS
    op.execute('ALTER TABLE voice_notes ENABLE ROW LEVEL SECURITY')
    
    op.execute("""
        CREATE POLICY voice_notes_select_policy ON voice_notes
        FOR SELECT
        USING (user_id = current_setting('app.current_user_id', true)::uuid 
               OR tenant_id = current_setting('app.current_tenant_id', true)::uuid)
    """)
    
    # ============================================
    # COST TRACKING TABLE
    # ============================================
    
    op.create_table(
        'cost_tracking',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=True),
        
        sa.Column('fixture_id', postgresql.UUID(as_uuid=True), nullable=True),
        
        sa.Column('cost_type', sa.String(50), nullable=False),  # 'api_call', 'enrichment', 'email_sync', 'voice_processing'
        sa.Column('provider', sa.String(50), nullable=True),  # 'openai', 'anthropic', 'google', etc.
        
        sa.Column('amount', sa.Float(), nullable=False),
        sa.Column('currency', sa.String(3), nullable=False, server_default='USD'),
        
        sa.Column('tokens_used', sa.Integer(), nullable=True),
        sa.Column('model', sa.String(50), nullable=True),
        
        sa.Column('extra_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['fixture_id'], ['fixtures.id'], ondelete='SET NULL'),
    )
    
    # Indexes
    op.create_index('idx_cost_tracking_user', 'cost_tracking', ['user_id'])
    op.create_index('idx_cost_tracking_tenant', 'cost_tracking', ['tenant_id'])
    op.create_index('idx_cost_tracking_fixture', 'cost_tracking', ['fixture_id'])
    op.create_index('idx_cost_tracking_type', 'cost_tracking', ['cost_type'])
    op.create_index('idx_cost_tracking_provider', 'cost_tracking', ['provider'])
    op.create_index('idx_cost_tracking_created_at', 'cost_tracking', ['created_at'])
    
    # GIN index for extra_data
    op.execute('CREATE INDEX idx_cost_tracking_extra_data_gin ON cost_tracking USING gin(extra_data jsonb_path_ops)')
    
    # Enable RLS
    op.execute('ALTER TABLE cost_tracking ENABLE ROW LEVEL SECURITY')
    
    op.execute("""
        CREATE POLICY cost_tracking_select_policy ON cost_tracking
        FOR SELECT
        USING (user_id = current_setting('app.current_user_id', true)::uuid 
               OR tenant_id = current_setting('app.current_tenant_id', true)::uuid)
    """)
    
    # ============================================
    # FUNCTIONS FOR RLS
    # ============================================
    
    # Function to set RLS context
    op.execute("""
        CREATE OR REPLACE FUNCTION set_rls_context(p_user_id UUID, p_tenant_id UUID)
        RETURNS void
        LANGUAGE plpgsql
        SECURITY DEFINER
        AS $$
        BEGIN
            PERFORM set_config('app.current_user_id', p_user_id::text, false);
            IF p_tenant_id IS NOT NULL THEN
                PERFORM set_config('app.current_tenant_id', p_tenant_id::text, false);
            END IF;
        END;
        $$;
    """)
    
    # ============================================
    # UPDATED AT TRIGGER FUNCTION
    # ============================================
    
    op.execute("""
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = now();
            RETURN NEW;
        END;
        $$ language 'plpgsql';
    """)
    
    # Create triggers for updated_at on all tables
    for table in ['users', 'fixtures', 'plugin_configs', 'email_syncs', 'regions', 'voice_notes', 'cost_tracking']:
        op.execute(f"""
            DROP TRIGGER IF EXISTS update_{table}_updated_at ON {table};
            CREATE TRIGGER update_{table}_updated_at
            BEFORE UPDATE ON {table}
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
        """)


def downgrade() -> None:
    # Drop triggers
    for table in ['users', 'fixtures', 'plugin_configs', 'email_syncs', 'regions', 'voice_notes', 'cost_tracking']:
        op.execute(f"DROP TRIGGER IF EXISTS update_{table}_updated_at ON {table}")
    
    # Drop RLS policies
    for table in ['users', 'fixtures', 'enrichments', 'plugin_configs', 'api_keys', 'email_syncs', 'regions', 'voice_notes', 'cost_tracking']:
        op.execute(f"DROP POLICY IF EXISTS {table}_select_policy ON {table}")
        op.execute(f"DROP POLICY IF EXISTS {table}_insert_policy ON {table}")
        op.execute(f"DROP POLICY IF EXISTS {table}_update_policy ON {table}")
        op.execute(f"DROP POLICY IF EXISTS {table}_delete_policy ON {table}")
    
    # Disable RLS
    op.execute('ALTER TABLE users DISABLE ROW LEVEL SECURITY')
    op.execute('ALTER TABLE fixtures DISABLE ROW LEVEL SECURITY')
    op.execute('ALTER TABLE enrichments DISABLE ROW LEVEL SECURITY')
    op.execute('ALTER TABLE plugin_configs DISABLE ROW LEVEL SECURITY')
    op.execute('ALTER TABLE api_keys DISABLE ROW LEVEL SECURITY')
    op.execute('ALTER TABLE email_syncs DISABLE ROW LEVEL SECURITY')
    op.execute('ALTER TABLE regions DISABLE ROW LEVEL SECURITY')
    op.execute('ALTER TABLE voice_notes DISABLE ROW LEVEL SECURITY')
    op.execute('ALTER TABLE cost_tracking DISABLE ROW LEVEL SECURITY')
    
    # Drop functions
    op.execute('DROP FUNCTION IF EXISTS set_rls_context(UUID, UUID)')
    op.execute('DROP FUNCTION IF EXISTS update_updated_at_column()')
    
    # Drop tables (in reverse order due to foreign keys)
    op.drop_table('cost_tracking')
    op.drop_table('voice_notes')
    op.drop_table('regions')
    op.drop_table('email_syncs')
    op.drop_table('api_keys')
    op.drop_table('plugin_configs')
    op.drop_table('enrichments')
    op.drop_table('fixtures')
    op.drop_table('users')
    
    # Drop enum types
    op.execute('DROP TYPE IF EXISTS voice_note_status')
    op.execute('DROP TYPE IF EXISTS email_provider')
    op.execute('DROP TYPE IF EXISTS fixture_status')
