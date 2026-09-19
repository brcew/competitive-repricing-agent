# Competitor Price Simulator Documentation

## Overview

The `competitor_price_simulator.py` module simulates Amazon pricing behavior without violating their Terms of Service. It provides realistic competitor price data for testing and demonstration while maintaining the same interface that a real scraper would use.

## Design Philosophy

**Why Simulation?**
- Avoids Amazon ToS violations (scraping prohibited)
- Enables deterministic testing and demos
- Provides realistic pricing patterns
- Swappable interface for real scraper later

**Realism Factors:**
- Base pricing (typically 5% below our price)
- Random walk (daily volatility)
- Occasional aggressive undercuts
- Mean reversion after undercuts
- Stock availability changes

## Pricing Model

### Base Pricing
```python
base_price = our_price * (1 - base_discount_percent / 100)
```
- Default: 5% below our price
- Represents normal competitive positioning

### Random Walk
```python
new_price = current_price * (1 ± daily_volatility_percent / 100)
```
- Default: ±2% daily volatility
- Simulates natural market fluctuations

### Aggressive Undercuts
- **Probability**: 5% per fetch (configurable)
- **Magnitude**: 10-20% below our price
- **Trigger**: Random event simulating promotional pricing
- **Recovery**: Gradual mean reversion over time

### Mean Reversion
```python
adjustment = (target_price - current_price) * mean_reversion_factor
new_price = current_price + adjustment
```
- Default: 10% reversion per period
- Prices gradually return to base after undercuts

### Availability
- **In Stock**: 95% probability (default)
- **Out of Stock**: 5% probability
- Simulates inventory fluctuations

## Usage Examples

### Basic Price Fetching

```python
from competitor_price_simulator import get_competitor_price
from models import SKU

# Get a SKU
sku = session.query(SKU).first()

# Fetch competitor price
price_data = get_competitor_price(sku)

print(f"Competitor: ${price_data['competitor_price']:.2f}")
print(f"Available: {price_data['is_available']}")
```

### Fetch and Store

```python
from competitor_price_simulator import fetch_and_store_price

# Fetch and automatically store in database
comp_price = fetch_and_store_price(sku)

print(f"Stored price: ${comp_price.competitor_price:.2f}")
```

### Get Latest Price

```python
from competitor_price_simulator import get_latest_price

# Retrieve most recent price from database
latest = get_latest_price(sku.id)

if latest:
    print(f"Latest: ${latest.competitor_price:.2f}")
    print(f"Fetched: {latest.fetched_at}")
```

### Custom Configuration

```python
from competitor_price_simulator import CompetitorPriceSimulator

# Create simulator with custom parameters
simulator = CompetitorPriceSimulator(
    base_discount_percent=8.0,  # 8% below our price
    daily_volatility_percent=3.0,  # ±3% daily
    aggressive_undercut_probability=0.10,  # 10% chance
    aggressive_undercut_range=(15.0, 25.0),  # 15-25% undercut
    availability_probability=0.90,  # 90% in stock
    mean_reversion_factor=0.15  # 15% reversion rate
)

price_data = simulator.get_competitor_price(sku)
```

## State Management

The simulator maintains state for each SKU to ensure continuity:

```python
state = {
    "base_price": float,  # Target price for mean reversion
    "current_price": float,  # Current simulated price
    "last_fetch": datetime,  # Last fetch timestamp
    "in_aggressive_undercut": bool,  # Currently recovering from undercut
    "undercut_recovery_target": float  # Target for recovery
}
```

This ensures:
- Prices evolve smoothly over time
- Undercut recovery is gradual
- Each SKU has independent price trajectory

## Testing

### Run Basic Tests
```bash
python test_simulator.py
```

Tests include:
- Basic price fetching
- Price evolution over time
- Database storage
- Aggressive undercut triggering
- Latest price retrieval

### Generate Historical Data
```bash
python simulate_competitor_prices.py
```

Generates:
- 50 SKUs with price history
- 7 days of historical data
- 4 fetches per day
- Total: 1,400 price points

## Swapping for Real Scraper

The simulator uses the same interface a real scraper would:

```python
# Current (simulator)
from competitor_price_simulator import get_competitor_price

# Future (real scraper)
from competitor_price_scraper import get_competitor_price  # Same signature

# Worker agent code stays unchanged
price_data = get_competitor_price(sku)
```

### Real Scraper Interface

When implementing a real scraper, maintain this contract:

```python
def get_competitor_price(sku: SKU, competitor_name: str = "Amazon") -> Dict[str, Any]:
    """
    Returns:
        {
            "competitor_name": str,  # "Amazon"
            "competitor_price": float,  # Dollar amount
            "is_available": bool,  # In stock?
            "confidence": float,  # 0.0-1.0 (data quality)
            "source": str,  # "scraper"
            "fetched_at": datetime  # UTC timestamp
        }
    """
```

## Configuration Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `base_discount_percent` | 5.0 | Base discount vs our price (%) |
| `daily_volatility_percent` | 2.0 | Daily price fluctuation range (±%) |
| `aggressive_undercut_probability` | 0.05 | Chance of aggressive undercut (5%) |
| `aggressive_undercut_range` | (10.0, 20.0) | Undercut magnitude range (%) |
| `availability_probability` | 0.95 | Chance product is in stock (95%) |
| `mean_reversion_factor` | 0.1 | Speed of recovery after undercut (10%/period) |

## Price Bounds

The simulator enforces realistic bounds:

```python
# Never below 80% of our cost (prevents unrealistic loss-leading)
min_price = sku.cost * 0.8

# Never above 120% of our price (prevents unrealistic pricing)
max_price = sku.our_price * 1.2
```

## Logging

The simulator logs key events:

```python
# Aggressive undercut triggered
logger.info(
    "Aggressive undercut triggered",
    sku=sku.sku,
    old_price=...,
    new_price=...,
    undercut_percent=...
)

# Recovery complete
logger.info(
    "Recovered from aggressive undercut",
    sku=sku.sku,
    new_price=...
)

# Out of stock
logger.info(
    "Competitor out of stock",
    sku=sku.sku,
    competitor=...
)
```

## Database Schema

Competitor prices are stored in `competitor_prices` table:

```sql
CREATE TABLE competitor_prices (
    id INTEGER PRIMARY KEY,
    sku_id INTEGER NOT NULL REFERENCES skus(id),
    competitor_name VARCHAR(100) NOT NULL,
    competitor_price FLOAT NOT NULL,
    is_available BOOLEAN NOT NULL,
    confidence FLOAT NOT NULL,
    fetched_at TIMESTAMP NOT NULL,
    source VARCHAR(50) NOT NULL
);

CREATE INDEX idx_competitor_prices_sku_time ON competitor_prices(sku_id, fetched_at);
```

## Future Enhancements

Potential improvements for more realism:

1. **Time-of-day patterns**: Lower prices during off-peak hours
2. **Seasonal trends**: Holiday pricing adjustments
3. **Category-specific behavior**: Different volatility by product type
4. **Competitor strategies**: Multiple competitors with different strategies
5. **Event-driven changes**: React to our price changes
6. **Stock level simulation**: Gradual stock depletion

## Integration with Agents

### Worker Agent
```python
# Worker fetches latest competitor price
latest_comp_price = get_latest_price(sku.id)

if not latest_comp_price or is_stale(latest_comp_price):
    # Fetch fresh price
    fetch_and_store_price(sku)
    latest_comp_price = get_latest_price(sku.id)

# Make pricing decision
if latest_comp_price.competitor_price < our_price:
    # Competitor undercut us, decide action...
```

### Orchestrator Agent
```python
# Analyze competitor price trends for watchlist decisions
recent_prices = session.query(CompetitorPrice)\
    .filter_by(sku_id=sku_id)\
    .order_by(CompetitorPrice.fetched_at.desc())\
    .limit(10)\
    .all()

# Calculate volatility, trend, etc.
```

## Troubleshooting

**Prices seem random**: State is maintained per-SKU, so continuous fetching will show gradual evolution, not random jumps.

**Too many undercuts**: Reduce `aggressive_undercut_probability` (default 5%).

**Prices not changing**: Ensure you're using the same simulator instance, or state is reset between calls.

**Database errors**: Ensure SKU exists before fetching price, and session is managed properly.