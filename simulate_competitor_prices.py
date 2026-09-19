"""
Bulk generate historical competitor price data for testing.

This script generates realistic competitor price history for SKUs
to enable testing of agent decisions with varied price scenarios.
"""

import os
os.environ['USE_LOCAL_CONFIG'] = '1'

import config
import config_local
config.settings = config_local.settings

import random
from datetime import datetime, timedelta

import structlog

from db_utils import get_db_session
from models import SKU, CompetitorPrice
from competitor_price_simulator import get_simulator

logger = structlog.get_logger(__name__)


def generate_historical_prices(
    num_skus: int = 50,
    days_history: int = 7,
    fetches_per_day: int = 4
):
    """
    Generate historical competitor prices for a subset of SKUs.
    
    Args:
        num_skus: Number of SKUs to generate prices for
        days_history: Number of days of history to generate
        fetches_per_day: Number of price fetches per day
    """
    print("="*70)
    print("Generating Historical Competitor Prices")
    print("="*70)
    print(f"\nParameters:")
    print(f"   SKUs: {num_skus}")
    print(f"   Days of history: {days_history}")
    print(f"   Fetches per day: {fetches_per_day}")
    print(f"   Total prices: {num_skus * days_history * fetches_per_day}")
    
    simulator = get_simulator()
    
    # Get SKUs
    with get_db_session() as session:
        # Get a diverse sample of SKUs (mix of categories and price points)
        all_skus = session.query(SKU).all()
        
        if len(all_skus) < num_skus:
            print(f"\n⚠️  Only {len(all_skus)} SKUs available, using all of them")
            num_skus = len(all_skus)
        
        sample_skus = random.sample(all_skus, num_skus)
        
        # Detach from session
        for sku in sample_skus:
            session.expunge(sku)
    
    print(f"\n📦 Selected {len(sample_skus)} SKUs for price simulation\n")
    
    # Generate prices chronologically (oldest to newest)
    now = datetime.utcnow()
    total_prices = 0
    
    prices_to_insert = []
    
    for day_offset in range(days_history, 0, -1):
        day_date = now - timedelta(days=day_offset)
        
        print(f"Generating prices for {day_date.date()}...")
        
        for fetch_num in range(fetches_per_day):
            # Spread fetches throughout the day
            hour_offset = fetch_num * (24 // fetches_per_day)
            fetch_time = day_date + timedelta(hours=hour_offset)
            
            for sku in sample_skus:
                price_data = simulator.get_competitor_price(sku)
                
                comp_price = CompetitorPrice(
                    sku_id=sku.id,
                    competitor_name=price_data["competitor_name"],
                    competitor_price=price_data["competitor_price"],
                    is_available=price_data["is_available"],
                    confidence=price_data["confidence"],
                    fetched_at=fetch_time,
                    source=price_data["source"]
                )
                
                prices_to_insert.append(comp_price)
                total_prices += 1
    
    # Bulk insert
    print(f"\nInserting {len(prices_to_insert)} prices into database...")
    
    with get_db_session() as session:
        for price in prices_to_insert:
            session.add(price)
        session.commit()
    
    print(f"✅ Successfully inserted {total_prices} competitor prices")
    
    # Show statistics
    print(f"\n📊 Statistics:")
    
    with get_db_session() as session:
        # Total prices
        total = session.query(CompetitorPrice).count()
        print(f"   Total competitor prices in DB: {total}")
        
        # Prices per SKU
        from sqlalchemy import func
        prices_per_sku = session.query(
            func.count(CompetitorPrice.id)
        ).filter(
            CompetitorPrice.sku_id.in_([sku.id for sku in sample_skus])
        ).scalar()
        
        avg_per_sku = prices_per_sku / len(sample_skus)
        print(f"   Average prices per SKU: {avg_per_sku:.1f}")
        
        # Sample some prices
        print(f"\n📈 Sample Price Data:")
        
        for sku in sample_skus[:3]:
            prices = session.query(CompetitorPrice)\
                .filter_by(sku_id=sku.id)\
                .order_by(CompetitorPrice.fetched_at.desc())\
                .limit(5)\
                .all()
            
            if prices:
                print(f"\n   {sku.sku}: {sku.product_name[:40]}")
                print(f"   Our Price: ${sku.our_price:.2f}")
                print(f"   Recent competitor prices:")
                for price in prices:
                    diff = price.competitor_price - sku.our_price
                    diff_pct = (diff / sku.our_price) * 100
                    status = "✅" if price.is_available else "❌"
                    print(f"      ${price.competitor_price:7.2f} ({diff_pct:+5.1f}%) {status} - {price.fetched_at}")
    
    print(f"\n" + "="*70)
    print("✅ Historical price generation complete!")
    print("="*70)
    
    return True


if __name__ == "__main__":
    import sys
    
    print("🎲 Competitor Price History Generator\n")
    
    # Default: 50 SKUs, 7 days, 4 fetches/day = 1,400 prices
    success = generate_historical_prices(
        num_skus=50,
        days_history=7,
        fetches_per_day=4
    )
    
    sys.exit(0 if success else 1)