from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import String, Integer, Float, DateTime, Boolean, Text, JSON, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import Base


class User(Base):
    __tablename__ = "users"
    
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[Optional[str]] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    fixtures: Mapped[list["Fixture"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    api_keys: Mapped[list["APIKey"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class Fixture(Base):
    __tablename__ = "fixtures"
    
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    
    vessel_name: Mapped[str] = mapped_column(String(100))
    imo_number: Mapped[Optional[str]] = mapped_column(String(7), index=True)
    cargo_type: Mapped[str] = mapped_column(String(100))
    cargo_quantity: Mapped[float] = mapped_column(Float)
    cargo_unit: Mapped[str] = mapped_column(String(10), default="MT")
    
    laycan_start: Mapped[datetime] = mapped_column(DateTime)
    laycan_end: Mapped[datetime] = mapped_column(DateTime)
    
    rate: Mapped[Optional[float]] = mapped_column(Float)
    rate_currency: Mapped[str] = mapped_column(String(3), default="USD")
    rate_unit: Mapped[str] = mapped_column(String(5), default="/mt")
    
    port_loading: Mapped[str] = mapped_column(String(100))
    port_discharge: Mapped[str] = mapped_column(String(100))
    
    charterer: Mapped[Optional[str]] = mapped_column(String(100))
    broker: Mapped[Optional[str]] = mapped_column(String(100))
    
    source_email_id: Mapped[Optional[str]] = mapped_column(String(255))
    source_subject: Mapped[Optional[str]] = mapped_column(String(500))
    
    status: Mapped[str] = mapped_column(String(20), default="new")
    
    wake_score: Mapped[Optional[float]] = mapped_column(Float)
    tce_estimate: Mapped[Optional[float]] = mapped_column(Float)
    market_diff: Mapped[Optional[float]] = mapped_column(Float)
    
    raw_data: Mapped[Optional[dict]] = mapped_column(JSON)
    enrichment_data: Mapped[Optional[dict]] = mapped_column(JSON)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user: Mapped["User"] = relationship(back_populates="fixtures")
    enrichments: Mapped[list["Enrichment"]] = relationship(back_populates="fixture", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("idx_fixture_user_status", "user_id", "status"),
        Index("idx_fixture_laycan", "laycan_start", "laycan_end"),
    )


class Enrichment(Base):
    __tablename__ = "enrichments"
    
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    fixture_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("fixtures.id"))
    
    source: Mapped[str] = mapped_column(String(50))
    data: Mapped[dict] = mapped_column(JSON)
    
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    fixture: Mapped["Fixture"] = relationship(back_populates="enrichments")


class PluginConfig(Base):
    __tablename__ = "plugin_configs"
    
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    
    plugin_name: Mapped[str] = mapped_column(String(100), index=True)
    config: Mapped[dict] = mapped_column(JSON)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class APIKey(Base):
    __tablename__ = "api_keys"
    
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    
    name: Mapped[str] = mapped_column(String(100))
    key_hash: Mapped[str] = mapped_column(String(255))
    permissions: Mapped[list[str]] = mapped_column(JSON, default=list)
    
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    user: Mapped["User"] = relationship(back_populates="api_keys")


class EmailSync(Base):
    __tablename__ = "email_syncs"
    
    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    
    provider: Mapped[str] = mapped_column(String(20))
    access_token: Mapped[str] = mapped_column(Text)
    refresh_token: Mapped[Optional[str]] = mapped_column(Text)
    token_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    
    last_sync_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
