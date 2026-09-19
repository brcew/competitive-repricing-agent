# Database Quick Reference

## Setup

### Initialize Database (First Time)
```bash
# Using Alembic migrations (recommended)
alembic upgrade head

# Or using SQLAlchemy directly
python -c "from db_utils import init_db; init_db()"
```

### Reset Database (Development Only)
```bash
python -c "from db_utils import reset_db; reset_db()"
```

## Common Operations

### Get a Database Session
```python
from db_utils import get_db_session

with get_db_session() as session:
    # Your database operations here
    skus = session.query(SKU).all()
    # Automatic commit on success, rollback on exception
```

### Create Records
```python
from models import SKU
from db_utils import get_db_session

with get_db_session() as session:
    sku = SKU(
        sku="PROD-001",
        product_name="Sample Product",
        our_price=99.99,
        cost=60.00,
        margin_percent=40.0
    )
    session.add(sku)
    # Commits automatically at end of context
```

### Query with Relationships
```python
from models import SKU
from db_utils import get_db_session

with get_db_session() as session:
    sku = session.query(SKU).filter_by(sku="PROD-001").first()
    
    # Access relationships
    watchlist_entries = sku.watchlist_entries
    competitor_prices = sku.competitor_prices
    decisions = sku.pricing_decisions
```

## Migration Commands

```bash
# Create a new migration
alembic revision --autogenerate -m "Description of changes"

# Apply all pending migrations
alembic upgrade head

# Rollback last migration
alembic downgrade -1

# Show current migration version
alembic current

# Show migration history
alembic history
```

## Testing

```bash
# Run model validation tests
python test_models.py
```

## Schema Documentation

See [SCHEMA.md](../SCHEMA.md) for complete schema documentation including:
- Entity relationship diagram
- Table descriptions
- Indexes and constraints
- Query patterns
- Design decisions