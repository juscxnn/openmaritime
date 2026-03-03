"""
OpenMaritime SQLAlchemy Models

These models correspond to the Alembic migrations in backend/alembic/versions/
"""
from datetime import datetime
from typing import Optional, List, Any
from uuid import uuid4

from sqlalchemy import String, Integer, Float, DateTime, Boolean, Text, ForeignKey, Index, TypeDecorator
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.models.base import Base


class User(Base):
    """
    User model with RLS support.
    
    The tenant_id field enables multi-tenant RLS policies.
    """
    __tablename__ = "users"
    
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[Optional[str]] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default='true')
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, server_default='false')
    tenant_id: Mapped[Optional[UUID]] = mapped_column(UUID(as_uuid=True), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    fixtures: Mapped[List["Fixture"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    api_keys: Mapped[List["APIKey"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    email_syncs: Mapped[List["EmailSync"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    plugin_configs: Mapped[List["PluginConfig"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    regions: Mapped[List["Region"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    voice_notes: Mapped[List["VoiceNote"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    cost_trackings: Mapped[List["CostTracking"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class Fixture(Base):
    """
    Fixture model with comprehensive fields for maritime chartering.
    
    Includes Wake AI scoring fields and JSONB for flexible data storage.
    """
    __tablename__ = "fixtures"
    
    # Primary keys
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    tenant_id: Mapped[Optional[UUID]] = mapped_column(UUID(as_uuid=True), index=True)
    
    # Vessel info
    vessel_name: Mapped[str] = mapped_column(String(100))
    imo_number: Mapped[Optional[str]] = mapped_column(String(7), index=True)
    
    # Cargo info
    cargo_type: Mapped[str] = mapped_column(String(100))
    cargo_quantity: Mapped[float] = mapped_column(Float, default=0.0)
    cargo_unit: Mapped[str] = mapped_column(String(10), default="MT")
    
    # Laycan
    laycan_start: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    laycan_end: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    
    # Rate
    rate: Mapped[Optional[float]] = mapped_column(Float)
    rate_currency: Mapped[str] = mapped_column(String(3), default="USD")
    rate_unit: Mapped[str] = mapped_column(String(5), default="/mt")
    
    # Ports
    port_loading: Mapped[str] = mapped_column(String(100))
    port_discharge: Mapped[str] = mapped_column(String(100))
    
    # Charterer/Broker
    charterer: Mapped[Optional[str]] = mapped_column(String(100))
    broker: Mapped[Optional[str]] = mapped_column(String(100))
    
    # Source tracking
    source_email_id: Mapped[Optional[str]] = mapped_column(String(255))
    source_subject: Mapped[Optional[str]] = mapped_column(String(500))
    
    # Status - using Python enum
    status: Mapped[str] = mapped_column(String(20), default="new", server_default='new')
    
    # Wake AI fields
    wake_score: Mapped[Optional[float]] = mapped_column(Float)
    tce_estimate: Mapped[Optional[float]] = mapped_column(Float)
    market_diff: Mapped[Optional[float]] = mapped_column(Float)
    
    # JSON data
    raw_data: Mapped[Optional[dict]] = mapped_column(JSONB)
    enrichment_data: Mapped[Optional[dict]] = mapped_column(JSONB)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user: Mapped["User"] = relationship(back_populates="fixtures")
    enrichments: Mapped[List["Enrichment"]] = relationship(back_populates="fixture", cascade="all, delete-orphan")
    voice_notes: Mapped[List["VoiceNote"]] = relationship(back_populates="fixture")
    cost_trackings: Mapped[List["CostTracking"]] = relationship(back_populates="fixture")
    
    __table_args__ = (
        Index("idx_fixture_user_status", "user_id", "status"),
        Index("idx_fixture_laycan", "laycan_start", "laycan_end"),
        Index("idx_fixture_wake_score", "wake_score"),
        Index("idx_fixture_tenant_id", "tenant_id"),
        Index("idx_fixture_imo", "imo_number"),
        Index("idx_fixture_port_loading", "port_loading"),
        Index("idx_fixture_port_discharge", "port_discharge"),
        Index("idx_fixture_cargo_type", "cargo_type"),
        Index("idx_fixture_created_at", "created_at"),
    )


class Enrichment(Base):
    """
    Enrichment data for fixtures from external sources.
    """
    __tablename__ = "enrichments"
    
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    fixture_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("fixtures.id", ondelete="CASCADE"))
    user_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    tenant_id: Mapped[Optional[UUID]] = mapped_column(UUID(as_uuid=True), index=True)
    
    source: Mapped[str] = mapped_column(String(50), index=True)
    data: Mapped[dict] = mapped_column(JSONB)
    
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    
    # Relationships
    fixture: Mapped["Fixture"] = relationship(back_populates="enrichments")
    
    __table_args__ = (
        Index("idx_enrichment_fixture", "fixture_id"),
        Index("idx_enrichment_user", "user_id"),
        Index("idx_enrichment_source", "source"),
        Index("idx_enrichment_fetched_at", "fetched_at"),
    )


class PluginConfig(Base):
    """
    Plugin configuration per user.
    """
    __tablename__ = "plugin_configs"
    
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    tenant_id: Mapped[Optional[UUID]] = mapped_column(UUID(as_uuid=True), index=True)
    
    plugin_name: Mapped[str] = mapped_column(String(100), index=True)
    config: Mapped[dict] = mapped_column(JSONB)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default='true')
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user: Mapped["User"] = relationship(back_populates="plugin_configs")
    
    __table_args__ = (
        Index("idx_plugin_config_plugin_name", "plugin_name"),
        Index("idx_plugin_config_user", "user_id"),
        Index("idx_plugin_config_is_enabled", "is_enabled"),
    )


class APIKey(Base):
    """
    API keys for programmatic access, scoped to user.
    """
    __tablename__ = "api_keys"
    
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    tenant_id: Mapped[Optional[UUID]] = mapped_column(UUID(as_uuid=True), index=True)
    
    name: Mapped[str] = mapped_column(String(100))
    key_hash: Mapped[str] = mapped_column(String(255), index=True)
    permissions: Mapped[List[str]] = mapped_column(JSONB, default=list)
    
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), index=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    
    # Relationships
    user: Mapped["User"] = relationship(back_populates="api_keys")
    
    __table_args__ = (
        Index("idx_api_key_user", "user_id"),
        Index("idx_api_key_key_hash", "key_hash"),
    )


class EmailSync(Base):
    """
    Email sync credentials per user (OAuth tokens).
    """
    __tablename__ = "email_syncs"
    
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    tenant_id: Mapped[Optional[UUID]] = mapped_column(UUID(as_uuid=True), index=True)
    
    provider: Mapped[str] = mapped_column(String(20))  # gmail, outlook, imap
    access_token: Mapped[str] = mapped_column(Text)
    refresh_token: Mapped[Optional[str]] = mapped_column(Text)
    token_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    last_sync_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default='true')
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user: Mapped["User"] = relationship(back_populates="email_syncs")
    
    __table_args__ = (
        Index("idx_email_sync_user", "user_id"),
        Index("idx_email_sync_provider", "provider"),
        Index("idx_email_sync_is_active", "is_active"),
    )


class Region(Base):
    """
    Custom geographic regions (polygons) for loading/discharge zones.
    
    Stores GeoJSON in JSONB format for compatibility.
    """
    __tablename__ = "regions"
    
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    tenant_id: Mapped[Optional[UUID]] = mapped_column(UUID(as_uuid=True), index=True)
    
    name: Mapped[str] = mapped_column(String(100))
    region_type: Mapped[str] = mapped_column(String(50))  # loading_zone, discharge_zone, transit
    # GeoJSON polygon stored as JSONB
    polygon: Mapped[dict] = mapped_column(JSONB)
    color: Mapped[Optional[str]] = mapped_column(String(7))  # Hex color
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default='true')
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user: Mapped["User"] = relationship(back_populates="regions")
    
    __table_args__ = (
        Index("idx_region_user", "user_id"),
        Index("idx_region_type", "region_type"),
    )


class VoiceNote(Base):
    """
    Voice notes with transcription support.
    """
    __tablename__ = "voice_notes"
    
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    tenant_id: Mapped[Optional[UUID]] = mapped_column(UUID(as_uuid=True), index=True)
    
    fixture_id: Mapped[Optional[UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("fixtures.id", ondelete="SET NULL"))
    
    file_path: Mapped[str] = mapped_column(String(500))
    duration_seconds: Mapped[Optional[float]] = mapped_column(Float)
    
    transcription: Mapped[Optional[str]] = mapped_column(Text)
    transcription_model: Mapped[Optional[str]] = mapped_column(String(50))
    
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending, processing, completed, failed
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user: Mapped["User"] = relationship(back_populates="voice_notes")
    fixture: Mapped[Optional["Fixture"]] = relationship(back_populates="voice_notes")
    
    __table_args__ = (
        Index("idx_voice_note_user", "user_id"),
        Index("idx_voice_note_fixture", "fixture_id"),
        Index("idx_voice_note_status", "status"),
        Index("idx_voice_note_created_at", "created_at"),
    )


class CostTracking(Base):
    """
    Cost tracking for API calls and external services.
    """
    __tablename__ = "cost_tracking"
    
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    tenant_id: Mapped[Optional[UUID]] = mapped_column(UUID(as_uuid=True), index=True)
    
    fixture_id: Mapped[Optional[UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("fixtures.id", ondelete="SET NULL"))
    
    cost_type: Mapped[str] = mapped_column(String(50))  # api_call, enrichment, email_sync, voice_processing
    provider: Mapped[Optional[str]] = mapped_column(String(50))  # openai, anthropic, google, etc.
    
    amount: Mapped[float] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    
    tokens_used: Mapped[Optional[int]] = mapped_column(Integer)
    model: Mapped[Optional[str]] = mapped_column(String(50))
    
    # Using 'extra_data' instead of 'metadata' (reserved in SQLAlchemy)
    extra_data: Mapped[Optional[dict]] = mapped_column(JSONB)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    
    # Relationships
    user: Mapped["User"] = relationship(back_populates="cost_trackings")
    fixture: Mapped[Optional["Fixture"]] = relationship(back_populates="cost_trackings")
    
    __table_args__ = (
        Index("idx_cost_tracking_user", "user_id"),
        Index("idx_cost_tracking_fixture", "fixture_id"),
        Index("idx_cost_tracking_type", "cost_type"),
        Index("idx_cost_tracking_provider", "provider"),
        Index("idx_cost_tracking_created_at", "created_at"),
    )


class AuditLog(Base):
    """
    Audit logs for critical operations.
    Tracks fixture changes, AI decisions, plugin calls, auth events.
    """
    __tablename__ = "audit_logs"
    
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[Optional[UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    tenant_id: Mapped[Optional[UUID]] = mapped_column(UUID(as_uuid=True), index=True)
    
    action: Mapped[str] = mapped_column(String(100), index=True)  # fixture.create, ai.decision, auth.login, plugin.call
    resource_type: Mapped[str] = mapped_column(String(50))  # fixture, user, plugin, etc.
    resource_id: Mapped[Optional[str]] = mapped_column(String(255))
    
    # Who/what initiated the action
    actor_type: Mapped[str] = mapped_column(String(20), default="user")  # user, system, agent, plugin
    actor_id: Mapped[Optional[str]] = mapped_column(String(255))
    
    # Change tracking
    old_value: Mapped[Optional[dict]] = mapped_column(JSONB)
    new_value: Mapped[Optional[dict]] = mapped_column(JSONB)
    
    # Context
    ip_address: Mapped[Optional[str]] = mapped_column(String(45))
    user_agent: Mapped[Optional[str]] = mapped_column(String(500))
    request_id: Mapped[Optional[str]] = mapped_column(String(100))
    
    # AI-specific
    ai_model: Mapped[Optional[str]] = mapped_column(String(100))
    ai_prompt_tokens: Mapped[Optional[int]] = mapped_column(Integer)
    ai_completion_tokens: Mapped[Optional[int]] = mapped_column(Integer)
    
    # Result
    status: Mapped[str] = mapped_column(String(20), default="success")  # success, failure, pending
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, index=True)
    
    __table_args__ = (
        Index("idx_audit_user", "user_id"),
        Index("idx_audit_tenant", "tenant_id"),
        Index("idx_audit_action", "action"),
        Index("idx_audit_resource", "resource_type", "resource_id"),
        Index("idx_audit_created_at", "created_at"),
        Index("idx_audit_actor", "actor_type", "actor_id"),
    )


class PromptTemplate(Base):
    """
    Prompt templates for AI agents.
    Customizable per tenant for workflow adaptation.
    """
    __tablename__ = "prompt_templates"
    
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[Optional[UUID]] = mapped_column(UUID(as_uuid=True), index=True)
    
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    agent_type: Mapped[str] = mapped_column(String(50))  # extraction, enrichment, ranking, prediction, decision
    version: Mapped[int] = mapped_column(Integer, default=1)
    
    # Prompt content
    system_prompt: Mapped[str] = mapped_column(Text)
    user_template: Mapped[str] = mapped_column(Text)
    
    # Configuration
    model: Mapped[Optional[str]] = mapped_column(String(50))  # Override default model
    temperature: Mapped[Optional[float]] = mapped_column(Float, default=0.1)
    max_tokens: Mapped[Optional[int]] = mapped_column(Integer, default=2048)
    
    # Metadata
    description: Mapped[Optional[str]] = mapped_column(Text)
    variables: Mapped[Optional[dict]] = mapped_column(JSONB)  # Available variables for this prompt
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)  # System default
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index("idx_prompt_tenant", "tenant_id"),
        Index("idx_prompt_agent", "agent_type"),
        Index("idx_prompt_name", "name"),
    )
