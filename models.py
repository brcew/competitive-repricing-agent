"""
SQLAlchemy models for the competitive pricing system.

Database schema for storing SKUs, watchlist, competitor prices,
conversion metrics, pricing decisions, and orchestrator runs.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class SKU(Base):
    """Product SKUs with current pricing and margin information."""
    
    __tablename__ = "skus"
    
    id = Column(Integer, primary_key=True, index=True)
    sku = Column(String(100), unique=True, nullable=False, index=True)
    product_name = Column(String(500), nullable=False)
    category = Column(String(100), nullable=True, index=True)
    
    # Current pricing
    our_price = Column(Float, nullable=False)
    cost = Column(Float, nullable=False)
    
    # Calculated margin
    margin_percent = Column(Float, nullable=False)  # (our_price - cost) / our_price * 100
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    watchlist_entries = relationship("Watchlist", back_populates="sku", cascade="all, delete-orphan")
    competitor_prices = relationship("CompetitorPrice", back_populates="sku", cascade="all, delete-orphan")
    conversion_metrics = relationship("ConversionMetric", back_populates="sku", cascade="all, delete-orphan")
    pricing_decisions = relationship("PricingDecision", back_populates="sku", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<SKU(sku={self.sku}, product={self.product_name}, price={self.our_price})>"


class Watchlist(Base):
    """Active SKUs being monitored by the worker agents."""
    
    __tablename__ = "watchlist"
    
    id = Column(Integer, primary_key=True, index=True)
    sku_id = Column(Integer, ForeignKey("skus.id"), nullable=False)
    
    # Activation status
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    
    # Priority and reason (set by orchestrator)
    priority_score = Column(Float, nullable=True)  # Higher = more important
    reason = Column(Text, nullable=True)  # Orchestrator's reasoning for adding this SKU
    
    # Timestamps
    added_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    added_by_run_id = Column(Integer, ForeignKey("orchestrator_runs.id"), nullable=True)
    deactivated_at = Column(DateTime, nullable=True)
    
    # Relationships
    sku = relationship("SKU", back_populates="watchlist_entries")
    added_by_run = relationship("OrchestratorRun", foreign_keys=[added_by_run_id])
    
    # Ensure each SKU appears only once in active watchlist
    __table_args__ = (
        Index("idx_watchlist_active_sku", "sku_id", "is_active"),
    )
    
    def __repr__(self) -> str:
        return f"<Watchlist(sku_id={self.sku_id}, active={self.is_active}, priority={self.priority_score})>"


class CompetitorPrice(Base):
    """Competitor pricing data (simulated or scraped)."""
    
    __tablename__ = "competitor_prices"
    
    id = Column(Integer, primary_key=True, index=True)
    sku_id = Column(Integer, ForeignKey("skus.id"), nullable=False)
    
    # Competitor data
    competitor_name = Column(String(100), default="Amazon", nullable=False)
    competitor_price = Column(Float, nullable=False)
    
    # Data quality
    is_available = Column(Boolean, default=True, nullable=False)
    confidence = Column(Float, default=1.0, nullable=False)  # 0.0 to 1.0
    
    # Metadata
    fetched_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    source = Column(String(50), default="simulator", nullable=False)  # 'simulator' or 'scraper'
    
    # Relationships
    sku = relationship("SKU", back_populates="competitor_prices")
    
    # Index for efficient latest price queries
    __table_args__ = (
        Index("idx_competitor_prices_sku_time", "sku_id", "fetched_at"),
    )
    
    def __repr__(self) -> str:
        return f"<CompetitorPrice(sku_id={self.sku_id}, price={self.competitor_price}, at={self.fetched_at})>"


class ConversionMetric(Base):
    """Conversion and sales performance metrics per SKU."""
    
    __tablename__ = "conversion_metrics"
    
    id = Column(Integer, primary_key=True, index=True)
    sku_id = Column(Integer, ForeignKey("skus.id"), nullable=False)
    
    # Time period
    period_start = Column(DateTime, nullable=False, index=True)
    period_end = Column(DateTime, nullable=False)
    
    # Metrics
    views = Column(Integer, default=0, nullable=False)
    clicks = Column(Integer, default=0, nullable=False)
    orders = Column(Integer, default=0, nullable=False)
    revenue = Column(Float, default=0.0, nullable=False)
    
    # Calculated rates
    click_through_rate = Column(Float, nullable=True)  # clicks / views
    conversion_rate = Column(Float, nullable=True)  # orders / clicks
    
    # Margin performance
    gross_margin = Column(Float, nullable=True)  # Total margin in dollars
    margin_percent = Column(Float, nullable=True)  # Average margin percentage
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    sku = relationship("SKU", back_populates="conversion_metrics")
    
    # Ensure unique metrics per SKU per period
    __table_args__ = (
        UniqueConstraint("sku_id", "period_start", "period_end", name="uq_metrics_sku_period"),
        Index("idx_conversion_metrics_period", "period_start", "period_end"),
    )
    
    def __repr__(self) -> str:
        return f"<ConversionMetric(sku_id={self.sku_id}, period={self.period_start} to {self.period_end})>"


class PricingDecision(Base):
    """Worker agent pricing decisions with full audit trail."""
    
    __tablename__ = "pricing_decisions"
    
    id = Column(Integer, primary_key=True, index=True)
    sku_id = Column(Integer, ForeignKey("skus.id"), nullable=False)
    
    # Decision context
    our_price_at_decision = Column(Float, nullable=False)
    competitor_price_at_decision = Column(Float, nullable=False)
    margin_floor = Column(Float, nullable=False)  # The 12% floor enforced
    
    # Decision output
    action = Column(String(20), nullable=False, index=True)  # MATCH, UNDERCUT_50, HOLD
    new_price = Column(Float, nullable=True)  # NULL if action=HOLD
    
    # Agent reasoning
    reasoning = Column(Text, nullable=True)  # LLM's explanation
    
    # Margin safety check
    margin_check_passed = Column(Boolean, nullable=False)
    margin_check_reason = Column(Text, nullable=True)  # Why it passed/failed
    
    # Execution status
    executed = Column(Boolean, default=False, nullable=False)
    executed_at = Column(DateTime, nullable=True)
    
    # Metadata
    decided_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    model_used = Column(String(100), nullable=False)  # e.g., 'llama-3.1-8b-instant'
    tokens_used = Column(Integer, nullable=True)
    
    # Relationships
    sku = relationship("SKU", back_populates="pricing_decisions")
    
    # Index for efficient recent decisions queries
    __table_args__ = (
        Index("idx_pricing_decisions_sku_time", "sku_id", "decided_at"),
        Index("idx_pricing_decisions_action", "action", "decided_at"),
    )
    
    def __repr__(self) -> str:
        return f"<PricingDecision(sku_id={self.sku_id}, action={self.action}, new_price={self.new_price})>"


class OrchestratorRun(Base):
    """Orchestrator agent execution history with watchlist decisions."""
    
    __tablename__ = "orchestrator_runs"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Execution timing
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    completed_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Float, nullable=True)
    
    # Watchlist sizing decision
    watchlist_cap_used = Column(Integer, nullable=False)  # Cap in effect during this run
    skus_added = Column(Integer, default=0, nullable=False)
    skus_removed = Column(Integer, default=0, nullable=False)
    final_watchlist_size = Column(Integer, nullable=False)
    
    # Agent reasoning
    reasoning = Column(Text, nullable=True)  # LLM's explanation of watchlist changes
    
    # Rate limiting context
    rate_limit_constraint = Column(String(20), nullable=True)  # 'RPD', 'TPM', 'TPD', or NULL
    rate_limit_headroom_percent = Column(Float, nullable=True)  # How much capacity remained
    
    # Model info
    model_used = Column(String(100), nullable=False)  # e.g., 'llama-3.3-70b-versatile'
    tokens_used = Column(Integer, nullable=True)
    
    # Status
    success = Column(Boolean, default=True, nullable=False)
    error_message = Column(Text, nullable=True)
    
    # Relationships
    watchlist_entries_added = relationship(
        "Watchlist",
        foreign_keys=[Watchlist.added_by_run_id],
        back_populates="added_by_run"
    )
    
    def __repr__(self) -> str:
        return f"<OrchestratorRun(id={self.id}, at={self.started_at}, watchlist_size={self.final_watchlist_size})>"