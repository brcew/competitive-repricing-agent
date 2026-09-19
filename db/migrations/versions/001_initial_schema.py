"""Initial schema - SKUs, watchlist, competitor prices, metrics, decisions, orchestrator runs

Revision ID: 001
Revises: 
Create Date: 2026-07-25

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create skus table
    op.create_table(
        'skus',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('sku', sa.String(length=100), nullable=False),
        sa.Column('product_name', sa.String(length=500), nullable=False),
        sa.Column('category', sa.String(length=100), nullable=True),
        sa.Column('our_price', sa.Float(), nullable=False),
        sa.Column('cost', sa.Float(), nullable=False),
        sa.Column('margin_percent', sa.Float(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_skus_id'), 'skus', ['id'], unique=False)
    op.create_index(op.f('ix_skus_sku'), 'skus', ['sku'], unique=True)
    op.create_index(op.f('ix_skus_category'), 'skus', ['category'], unique=False)
    
    # Create orchestrator_runs table (before watchlist due to FK)
    op.create_table(
        'orchestrator_runs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('duration_seconds', sa.Float(), nullable=True),
        sa.Column('watchlist_cap_used', sa.Integer(), nullable=False),
        sa.Column('skus_added', sa.Integer(), nullable=False),
        sa.Column('skus_removed', sa.Integer(), nullable=False),
        sa.Column('final_watchlist_size', sa.Integer(), nullable=False),
        sa.Column('reasoning', sa.Text(), nullable=True),
        sa.Column('rate_limit_constraint', sa.String(length=20), nullable=True),
        sa.Column('rate_limit_headroom_percent', sa.Float(), nullable=True),
        sa.Column('model_used', sa.String(length=100), nullable=False),
        sa.Column('tokens_used', sa.Integer(), nullable=True),
        sa.Column('success', sa.Boolean(), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_orchestrator_runs_id'), 'orchestrator_runs', ['id'], unique=False)
    op.create_index(op.f('ix_orchestrator_runs_started_at'), 'orchestrator_runs', ['started_at'], unique=False)
    
    # Create watchlist table
    op.create_table(
        'watchlist',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('sku_id', sa.Integer(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('priority_score', sa.Float(), nullable=True),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('added_at', sa.DateTime(), nullable=False),
        sa.Column('added_by_run_id', sa.Integer(), nullable=True),
        sa.Column('deactivated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['sku_id'], ['skus.id'], ),
        sa.ForeignKeyConstraint(['added_by_run_id'], ['orchestrator_runs.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_watchlist_id'), 'watchlist', ['id'], unique=False)
    op.create_index(op.f('ix_watchlist_is_active'), 'watchlist', ['is_active'], unique=False)
    op.create_index('idx_watchlist_active_sku', 'watchlist', ['sku_id', 'is_active'], unique=False)
    
    # Create competitor_prices table
    op.create_table(
        'competitor_prices',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('sku_id', sa.Integer(), nullable=False),
        sa.Column('competitor_name', sa.String(length=100), nullable=False),
        sa.Column('competitor_price', sa.Float(), nullable=False),
        sa.Column('is_available', sa.Boolean(), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('fetched_at', sa.DateTime(), nullable=False),
        sa.Column('source', sa.String(length=50), nullable=False),
        sa.ForeignKeyConstraint(['sku_id'], ['skus.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_competitor_prices_id'), 'competitor_prices', ['id'], unique=False)
    op.create_index(op.f('ix_competitor_prices_fetched_at'), 'competitor_prices', ['fetched_at'], unique=False)
    op.create_index('idx_competitor_prices_sku_time', 'competitor_prices', ['sku_id', 'fetched_at'], unique=False)
    
    # Create conversion_metrics table
    op.create_table(
        'conversion_metrics',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('sku_id', sa.Integer(), nullable=False),
        sa.Column('period_start', sa.DateTime(), nullable=False),
        sa.Column('period_end', sa.DateTime(), nullable=False),
        sa.Column('views', sa.Integer(), nullable=False),
        sa.Column('clicks', sa.Integer(), nullable=False),
        sa.Column('orders', sa.Integer(), nullable=False),
        sa.Column('revenue', sa.Float(), nullable=False),
        sa.Column('click_through_rate', sa.Float(), nullable=True),
        sa.Column('conversion_rate', sa.Float(), nullable=True),
        sa.Column('gross_margin', sa.Float(), nullable=True),
        sa.Column('margin_percent', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['sku_id'], ['skus.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('sku_id', 'period_start', 'period_end', name='uq_metrics_sku_period')
    )
    op.create_index(op.f('ix_conversion_metrics_id'), 'conversion_metrics', ['id'], unique=False)
    op.create_index(op.f('ix_conversion_metrics_period_start'), 'conversion_metrics', ['period_start'], unique=False)
    op.create_index('idx_conversion_metrics_period', 'conversion_metrics', ['period_start', 'period_end'], unique=False)
    
    # Create pricing_decisions table
    op.create_table(
        'pricing_decisions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('sku_id', sa.Integer(), nullable=False),
        sa.Column('our_price_at_decision', sa.Float(), nullable=False),
        sa.Column('competitor_price_at_decision', sa.Float(), nullable=False),
        sa.Column('margin_floor', sa.Float(), nullable=False),
        sa.Column('action', sa.String(length=20), nullable=False),
        sa.Column('new_price', sa.Float(), nullable=True),
        sa.Column('reasoning', sa.Text(), nullable=True),
        sa.Column('margin_check_passed', sa.Boolean(), nullable=False),
        sa.Column('margin_check_reason', sa.Text(), nullable=True),
        sa.Column('executed', sa.Boolean(), nullable=False),
        sa.Column('executed_at', sa.DateTime(), nullable=True),
        sa.Column('decided_at', sa.DateTime(), nullable=False),
        sa.Column('model_used', sa.String(length=100), nullable=False),
        sa.Column('tokens_used', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['sku_id'], ['skus.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_pricing_decisions_id'), 'pricing_decisions', ['id'], unique=False)
    op.create_index(op.f('ix_pricing_decisions_action'), 'pricing_decisions', ['action'], unique=False)
    op.create_index(op.f('ix_pricing_decisions_decided_at'), 'pricing_decisions', ['decided_at'], unique=False)
    op.create_index('idx_pricing_decisions_sku_time', 'pricing_decisions', ['sku_id', 'decided_at'], unique=False)
    op.create_index('idx_pricing_decisions_action', 'pricing_decisions', ['action', 'decided_at'], unique=False)


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table('pricing_decisions')
    op.drop_table('conversion_metrics')
    op.drop_table('competitor_prices')
    op.drop_table('watchlist')
    op.drop_table('orchestrator_runs')
    op.drop_table('skus')