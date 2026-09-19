"""
Seed database with 800 mock SKUs using SQLite for local development.
"""

import sys
import os

# Override config to use local SQLite settings
os.environ['USE_LOCAL_CONFIG'] = '1'

# Replace config import before importing db_utils
import config
import config_local
config.settings = config_local.settings

from seed_data import seed_database, print_seeding_summary
from db_utils import get_db_session
from models import SKU, ConversionMetric

def main():
    """Main seeding function for local SQLite database."""
    print("🔧 Using SQLite for local development")
    print(f"📁 Database file: {config_local.settings.db_file}")
    print()
    
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
        
        print(f"\n💡 Tip: Run 'python inspect_data.py' to see detailed statistics")
        print(f"💡 Tip: Run 'python show_samples.py' to see sample data from all tables")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Seeding failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)