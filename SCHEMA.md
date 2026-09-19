# Database Schema Documentation

## Overview

The competitive pricing agent system uses a PostgreSQL database with 6 core tables to track SKUs, watchlist management, competitor pricing, conversion metrics, pricing decisions, and orchestrator activity.

## Entity Relationship Diagram

```
┌─────────────────────┐
│       SKUs          │
│  (Product Catalog)  │
├─────────────────────┤
│ id (PK)             │
│ sku (unique)        │
│ product_name        │
│ category            │
│ our_price           │
│ cost                │
│ margin_percent      │
│ created_at          │
│ updated_at          │
└─────────────────────┘
          │
          │ 1:N relationships to:
          ├──────────────────────┐
          │                      │
          ▼                      ▼
┌─────────────────┐    ┌──────────────────┐
│   Watchlist     │    │ CompetitorPrice  │
├─────────────────┤    ├──────────────────┤
│ id (PK)         │    │ id (PK)          │
│ sku_id (FK)     │    │ sku_id (FK)      │
│ is_active       │    │ competitor_name  │
│ priority_score  │    │ competitor_price │
│ reason          │    │ is_available     │
│ added_at        │    │ confidence       │
│ added_by_run_id │    │ fetched_at       │
│ deactivated_at  │    │ source           │
└─────────────────┘    └──────────────────┘
          │
          │ (FK)                 ▼
          │            ┌──────────────────┐
          │            │ ConversionMetric │
          │            ├──────────────────┤
          │            │ id (PK)          │
          │            │ sku_id (FK)      │
          │            │ period_start     │
          │            │ period_end       │
          │            │ views, clicks    │
          │            │ orders, revenue  │
          │            │ CTR, conv_rate   │
          │            │ gross_margin     │
          │            └──────────────────┘
          │
          ▼                      ▼
┌───────────────────┐  ┌──────────────────┐
│ OrchestratorRun   │  │ PricingDecision  │
├───────────────────┤  ├──────────────────┤
│ id (PK)           │  │ id (PK)          │
│ started_at        │  │ sku_id (FK)      │
│ completed_at      │  │ our_price        │
│ duration_seconds  │  │ competitor_price │
│ watchlist_cap     │  │ margin_floor     │
│ skus_added        │  │ action           │
│ skus_removed      │  │ new_price        │
│ final_size        │  │ reasoning        │
│ reasoning         │  │ margin_check_*   │
│ rate_limit_*      │  │ executed         │
│ model_used        │  │ decided_at       │
│ tokens_used       │  │ model_used       │
│ success           │  │ tokens_used      │
└───────────────────┘  └──────────────────┘
```

## Table Descriptions

### 1. `skus`
**Purpose**: Product catalog with current pricing and margin information.

**Key Fields**:
- `sku`: Unique product identifier
- `our_price`: Current selling price
- `cost`: Product cost (for margin calculation)
- `margin_percent`: Calculated gross margin percentage

**Indexes**:
- Primary key on `id`
- Unique index on `sku`
- Index on `category` for filtering

**Usage**: Central table that all other tables reference for product data.

---

### 2. `watchlist`
**Purpose**: Tracks which SKUs are actively monitored by worker agents.

**Key Fields**:
- `sku_id`: FK to skus table
- `is_active`: Whether this SKU is currently being monitored
- `priority_score`: Orchestrator-assigned importance (higher = more important)
- `reason`: Orchestrator's explanation for adding this SKU
- `added_by_run_id`: FK to orchestrator_runs (which run added this)

**Indexes**:
- Composite index on `(sku_id, is_active)` for efficient active watchlist queries

**Business Rules**:
- Each SKU should appear only once in the active watchlist
- Orchestrator manages this list hourly
- Worker agents only process active watchlist SKUs

---

### 3. `competitor_prices`
**Purpose**: Historical competitor pricing data (simulated or scraped).

**Key Fields**:
- `sku_id`: FK to skus table
- `competitor_name`: Which competitor (default: "Amazon")
- `competitor_price`: Their current price
- `is_available`: Whether product is in stock
- `confidence`: Data quality score (0.0 to 1.0)
- `source`: "simulator" or "scraper"
- `fetched_at`: Timestamp of price fetch

**Indexes**:
- Composite index on `(sku_id, fetched_at)` for efficient "latest price" queries

**Usage**: Worker agents fetch latest competitor price for each active watchlist SKU.

---

### 4. `conversion_metrics`
**Purpose**: Sales and conversion performance data per SKU over time periods.

**Key Fields**:
- `sku_id`: FK to skus table
- `period_start`, `period_end`: Time range for metrics
- `views`, `clicks`, `orders`: Funnel metrics
- `revenue`: Total sales in period
- `click_through_rate`: clicks / views
- `conversion_rate`: orders / clicks
- `gross_margin`: Total margin dollars
- `margin_percent`: Average margin percentage

**Constraints**:
- Unique constraint on `(sku_id, period_start, period_end)` - one metric row per SKU per period

**Usage**: Orchestrator reads these to identify high-performing or struggling SKUs.

---

### 5. `pricing_decisions`
**Purpose**: Complete audit trail of all worker agent pricing decisions.

**Key Fields**:
- `sku_id`: FK to skus table
- `our_price_at_decision`: Our price when decision was made
- `competitor_price_at_decision`: Their price when decision was made
- `margin_floor`: The 12% floor enforced during this decision
- `action`: One of: MATCH, UNDERCUT_50, HOLD
- `new_price`: Proposed new price (NULL if action=HOLD)
- `reasoning`: LLM's explanation text
- `margin_check_passed`: Whether the deterministic safety check passed
- `margin_check_reason`: Why it passed/failed
- `executed`: Whether the price change was actually applied
- `model_used`: Which worker model made this decision
- `tokens_used`: Token count for cost tracking

**Indexes**:
- Composite index on `(sku_id, decided_at)` for recent decisions per SKU
- Composite index on `(action, decided_at)` for decision type analysis

**Business Rules**:
- Every worker agent decision is logged, even if rejected by margin check
- This is the primary auditability mechanism

---

### 6. `orchestrator_runs`
**Purpose**: Historical record of orchestrator agent executions.

**Key Fields**:
- `started_at`, `completed_at`, `duration_seconds`: Timing data
- `watchlist_cap_used`: Watchlist size limit during this run
- `skus_added`, `skus_removed`: Changes made to watchlist
- `final_watchlist_size`: Resulting watchlist size
- `reasoning`: LLM's explanation of watchlist changes
- `rate_limit_constraint`: Which limit bound this run (RPD, TPM, TPD)
- `rate_limit_headroom_percent`: Remaining capacity
- `model_used`: Which orchestrator model (70b)
- `tokens_used`: Token count for cost tracking
- `success`: Whether run completed without errors

**Usage**: 
- Historical record for debugging orchestrator logic
- Input for daily cost analysis reports
- Rate limit tracking over time

---

## Key Design Decisions

### 1. Soft Deletes vs Hard Deletes
- Watchlist uses soft deletes (`is_active=False`) to preserve history
- SKUs, decisions, and metrics are never deleted (audit trail)

### 2. Denormalization
- `our_price_at_decision` and `competitor_price_at_decision` are duplicated in `pricing_decisions` to create an immutable snapshot of the decision context

### 3. Margin Calculation
- Margin is stored both in `skus.margin_percent` (current) and `pricing_decisions.margin_floor` (at-time-of-decision) for different purposes

### 4. Time Series Data
- `competitor_prices`: One row per fetch (historical time series)
- `conversion_metrics`: One row per time period (aggregated time series)
- `pricing_decisions`: One row per decision (event stream)

### 5. Foreign Key Constraints
- All FKs are enforced at database level
- Cascading deletes on SKU → child tables (watchlist, prices, metrics, decisions)
- No cascade from orchestrator_runs → watchlist (preserve history even if run is deleted)

## Query Patterns

### Get Active Watchlist
```sql
SELECT s.*, w.priority_score, w.reason
FROM watchlist w
JOIN skus s ON w.sku_id = s.id
WHERE w.is_active = TRUE
ORDER BY w.priority_score DESC;
```

### Get Latest Competitor Price for SKU
```sql
SELECT *
FROM competitor_prices
WHERE sku_id = ?
ORDER BY fetched_at DESC
LIMIT 1;
```

### Get Recent Decisions for SKU
```sql
SELECT *
FROM pricing_decisions
WHERE sku_id = ?
ORDER BY decided_at DESC
LIMIT 10;
```

### Get Orchestrator Performance Stats
```sql
SELECT 
    DATE(started_at) as date,
    COUNT(*) as runs,
    AVG(duration_seconds) as avg_duration,
    AVG(final_watchlist_size) as avg_watchlist_size,
    SUM(tokens_used) as total_tokens
FROM orchestrator_runs
WHERE success = TRUE
GROUP BY DATE(started_at)
ORDER BY date DESC;
```

## Migrations

Migrations are managed via Alembic and stored in `db/migrations/versions/`.

**Initial migration**: `001_initial_schema.py`

To apply migrations:
```bash
alembic upgrade head
```

To rollback:
```bash
alembic downgrade -1
```