"""
Seed database with 800 mock SKUs for testing and demo.

Creates realistic product data across multiple electronics categories
with varied pricing and margin profiles.
"""

import random
from datetime import datetime, timedelta

import structlog

from db_utils import get_db_session, init_db
from models import SKU, ConversionMetric

logger = structlog.get_logger(__name__)


# Product categories and their characteristics
CATEGORIES = {
    "Laptops": {
        "prefix": "LAP",
        "price_range": (399.99, 2499.99),
        "margin_range": (15, 35),
        "products": [
            "Business Laptop", "Gaming Laptop", "Ultrabook", "2-in-1 Laptop",
            "Chromebook", "MacBook", "Budget Laptop", "Student Laptop",
            "Professional Workstation", "Convertible Laptop"
        ]
    },
    "Smartphones": {
        "prefix": "PHN",
        "price_range": (199.99, 1299.99),
        "margin_range": (20, 40),
        "products": [
            "Budget Smartphone", "Mid-Range Phone", "Flagship Phone",
            "5G Phone", "Camera Phone", "Gaming Phone", "Foldable Phone",
            "Rugged Phone", "Senior-Friendly Phone", "Kids Phone"
        ]
    },
    "Tablets": {
        "prefix": "TAB",
        "price_range": (149.99, 1099.99),
        "margin_range": (18, 38),
        "products": [
            "Budget Tablet", "iPad", "Android Tablet", "Drawing Tablet",
            "Kids Tablet", "E-Reader Tablet", "Gaming Tablet",
            "Business Tablet", "Large Screen Tablet", "Compact Tablet"
        ]
    },
    "Headphones": {
        "prefix": "AUD",
        "price_range": (29.99, 499.99),
        "margin_range": (25, 50),
        "products": [
            "Wireless Earbuds", "Over-Ear Headphones", "Gaming Headset",
            "Noise-Canceling Headphones", "Sports Earbuds", "Studio Headphones",
            "Kids Headphones", "Budget Earbuds", "Premium Earbuds", "Bone Conduction"
        ]
    },
    "Smartwatches": {
        "prefix": "WAT",
        "price_range": (79.99, 799.99),
        "margin_range": (22, 42),
        "products": [
            "Fitness Tracker", "Premium Smartwatch", "Budget Smartwatch",
            "Sports Watch", "Hybrid Watch", "Kids Smartwatch",
            "Fashion Smartwatch", "Rugged Watch", "Health Watch", "GPS Watch"
        ]
    },
    "Monitors": {
        "prefix": "MON",
        "price_range": (129.99, 1799.99),
        "margin_range": (15, 30),
        "products": [
            "24-inch Monitor", "27-inch Monitor", "32-inch Monitor",
            "4K Monitor", "Gaming Monitor", "Ultrawide Monitor",
            "Portable Monitor", "Curved Monitor", "Budget Monitor", "Professional Monitor"
        ]
    },
    "Keyboards": {
        "prefix": "KEY",
        "price_range": (19.99, 299.99),
        "margin_range": (30, 55),
        "products": [
            "Mechanical Keyboard", "Gaming Keyboard", "Wireless Keyboard",
            "Ergonomic Keyboard", "Budget Keyboard", "RGB Keyboard",
            "Compact Keyboard", "Split Keyboard", "Numpad Keyboard", "Travel Keyboard"
        ]
    },
    "Mice": {
        "prefix": "MOU",
        "price_range": (14.99, 179.99),
        "margin_range": (35, 60),
        "products": [
            "Gaming Mouse", "Wireless Mouse", "Ergonomic Mouse",
            "Budget Mouse", "Trackball", "Vertical Mouse",
            "Travel Mouse", "RGB Mouse", "MMO Mouse", "Presenter Mouse"
        ]
    },
}


def generate_sku_code(category_prefix: str, index: int) -> str:
    """Generate a unique SKU code."""
    return f"{category_prefix}-{index:04d}"


def generate_product_name(category: str, product_type: str, variant: int) -> str:
    """Generate a realistic product name with variant."""
    brands = ["TechPro", "EliteTech", "ValueTech", "ProGear", "SmartChoice", 
              "Premium", "Essential", "Advanced", "Professional", "Ultimate"]
    brand = random.choice(brands)
    
    if variant == 0:
        return f"{brand} {product_type}"
    else:
        return f"{brand} {product_type} {variant}"


def calculate_cost_from_margin(price: float, margin_percent: float) -> float:
    """Calculate cost given price and desired margin percentage."""
    # margin_percent = (price - cost) / price * 100
    # Solving for cost: cost = price * (1 - margin_percent/100)
    return price * (1 - margin_percent / 100)


def generate_mock_skus(count: int = 800) -> list[SKU]:
    """Generate mock SKU data."""
    skus = []
    sku_index = 1
    
    # Calculate how many SKUs per category
    categories = list(CATEGORIES.keys())
    skus_per_category = count // len(categories)
    remainder = count % len(categories)
    
    for cat_idx, category in enumerate(categories):
        cat_info = CATEGORIES[category]
        
        # Add one extra SKU to some categories to reach exact count
        num_skus = skus_per_category + (1 if cat_idx < remainder else 0)
        
        # Generate SKUs for this category
        products_in_category = cat_info["products"]
        variants_per_product = max(1, num_skus // len(products_in_category))
        
        product_idx = 0
        variant_idx = 0
        
        for _ in range(num_skus):
            product_type = products_in_category[product_idx]
            
            # Generate price and margin
            price = random.uniform(*cat_info["price_range"])
            margin_percent = random.uniform(*cat_info["margin_range"])
            cost = calculate_cost_from_margin(price, margin_percent)
            
            # Round to realistic values
            price = round(price, 2)
            cost = round(cost, 2)
            margin_percent = round(margin_percent, 1)
            
            # Create SKU
            sku = SKU(
                sku=generate_sku_code(cat_info["prefix"], sku_index),
                product_name=generate_product_name(category, product_type, variant_idx),
                category=category,
                our_price=price,
                cost=cost,
                margin_percent=margin_percent
            )
            
            skus.append(sku)
            sku_index += 1
            
            # Move to next product/variant
            variant_idx += 1
            if variant_idx >= variants_per_product:
                variant_idx = 0
                product_idx = (product_idx + 1) % len(products_in_category)
    
    return skus


def generate_mock_conversion_metrics(skus: list[SKU]) -> list[ConversionMetric]:
    """Generate realistic conversion metrics for a subset of SKUs."""
    metrics = []
    
    # Generate metrics for last 7 days for about 30% of SKUs
    sample_size = int(len(skus) * 0.3)
    sample_skus = random.sample(skus, sample_size)
    
    now = datetime.utcnow()
    
    for sku in sample_skus:
        for days_ago in range(7):
            period_end = now - timedelta(days=days_ago)
            period_start = period_end - timedelta(days=1)
            
            # Generate realistic funnel metrics
            # Higher priced items tend to have lower conversion
            price_factor = 1.0 - (sku.our_price / 3000.0)  # Normalize by max price
            price_factor = max(0.1, min(1.0, price_factor))
            
            views = random.randint(50, 500) * (1 if sku.our_price < 200 else 2 if sku.our_price < 500 else 3)
            click_rate = random.uniform(0.03, 0.15) * price_factor
            clicks = int(views * click_rate)
            
            conversion_rate = random.uniform(0.05, 0.25) * price_factor
            orders = int(clicks * conversion_rate)
            
            revenue = orders * sku.our_price
            gross_margin = orders * (sku.our_price - sku.cost)
            
            metric = ConversionMetric(
                sku_id=sku.id,
                period_start=period_start,
                period_end=period_end,
                views=views,
                clicks=clicks,
                orders=orders,
                revenue=round(revenue, 2),
                click_through_rate=round(click_rate * 100, 2),
                conversion_rate=round(conversion_rate * 100, 2),
                gross_margin=round(gross_margin, 2),
                margin_percent=sku.margin_percent
            )
            
            metrics.append(metric)
    
    return metrics


def seed_database(num_skus: int = 800) -> dict:
    """Seed the database with mock data."""
    logger.info("Starting database seeding", num_skus=num_skus)
    
    # Initialize database tables if needed
    try:
        init_db()
        logger.info("Database tables initialized")
    except Exception as e:
        logger.warning("Database initialization warning (may already exist)", error=str(e))
    
    stats = {
        "skus_created": 0,
        "metrics_created": 0,
        "categories": len(CATEGORIES),
        "errors": []
    }
    
    try:
        with get_db_session() as session:
            # Check if data already exists
            existing_count = session.query(SKU).count()
            if existing_count > 0:
                logger.warning("Database already contains SKUs", count=existing_count)
                response = input(f"Database has {existing_count} SKUs. Clear and reseed? (yes/no): ")
                if response.lower() != 'yes':
                    logger.info("Seeding cancelled by user")
                    return {"skus_created": 0, "metrics_created": 0, "cancelled": True}
                
                # Clear existing data
                logger.info("Clearing existing data...")
                session.query(ConversionMetric).delete()
                session.query(SKU).delete()
                session.commit()
                logger.info("Existing data cleared")
            
            # Generate and insert SKUs
            logger.info("Generating mock SKUs...")
            skus = generate_mock_skus(num_skus)
            
            logger.info("Inserting SKUs into database...")
            for sku in skus:
                session.add(sku)
            session.flush()  # Flush to get IDs assigned
            
            stats["skus_created"] = len(skus)
            logger.info("SKUs inserted", count=len(skus))
            
            # Generate and insert conversion metrics
            logger.info("Generating mock conversion metrics...")
            metrics = generate_mock_conversion_metrics(skus)
            
            logger.info("Inserting conversion metrics...")
            for metric in metrics:
                session.add(metric)
            
            stats["metrics_created"] = len(metrics)
            logger.info("Conversion metrics inserted", count=len(metrics))
            
            session.commit()
            
    except Exception as e:
        logger.error("Failed to seed database", error=str(e))
        stats["errors"].append(str(e))
        raise
    
    return stats


def print_seeding_summary(stats: dict):
    """Print a formatted summary of seeding results."""
    print("\n" + "="*60)
    print("Database Seeding Complete")
    print("="*60)
    
    if stats.get("cancelled"):
        print("❌ Seeding cancelled by user")
        return
    
    print(f"✅ SKUs created: {stats['skus_created']}")
    print(f"✅ Conversion metrics created: {stats['metrics_created']}")
    print(f"✅ Categories: {stats['categories']}")
    
    if stats.get("errors"):
        print(f"\n⚠️  Errors encountered:")
        for error in stats["errors"]:
            print(f"   - {error}")
    
    print("\n📊 Category Distribution:")
    for category, info in CATEGORIES.items():
        print(f"   - {category}: ~{stats['skus_created'] // stats['categories']} SKUs")
    
    print("\n💡 Quick Stats:")
    print("   - Price range: $14.99 - $2,499.99")
    print("   - Margin range: 15% - 60%")
    print("   - ~30% of SKUs have 7 days of conversion metrics")
    
    print("\n🚀 Ready for agent testing!")


def main():
    """Main seeding function."""
    try:
        stats = seed_database(num_skus=800)
        print_seeding_summary(stats)
        
        # Verify data
        with get_db_session() as session:
            sku_count = session.query(SKU).count()
            metric_count = session.query(ConversionMetric).count()
            
            print(f"\n✅ Verification: {sku_count} SKUs and {metric_count} metrics in database")
            
            # Show sample SKUs
            print("\n📦 Sample SKUs:")
            sample_skus = session.query(SKU).limit(5).all()
            for sku in sample_skus:
                print(f"   {sku.sku}: {sku.product_name} - ${sku.our_price} ({sku.margin_percent}% margin)")
        
        return True
        
    except Exception as e:
        logger.error("Seeding failed", error=str(e))
        print(f"\n❌ Seeding failed: {e}")
        return False


if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)