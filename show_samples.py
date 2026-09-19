"""
Show sample data from each table for verification.
"""

from db_utils import get_db_session
from models import (
    SKU,
    Watchlist,
    CompetitorPrice,
    ConversionMetric,
    PricingDecision,
    OrchestratorRun,
)


def show_samples():
    """Display sample records from each table."""
    print("="*70)
    print("Sample Data from Each Table")
    print("="*70)
    
    with get_db_session() as session:
        # SKUs
        print(f"\n📦 Sample SKUs:")
        skus = session.query(SKU).limit(3).all()
        if skus:
            for sku in skus:
                print(f"   [{sku.sku}] {sku.product_name}")
                print(f"      Category: {sku.category}")
                print(f"      Price: ${sku.our_price:.2f} | Cost: ${sku.cost:.2f} | Margin: {sku.margin_percent}%")
        else:
            print("   No SKUs found")
        
        # Watchlist
        print(f"\n👁️  Active Watchlist:")
        watchlist = session.query(Watchlist).filter_by(is_active=True).limit(3).all()
        if watchlist:
            for entry in watchlist:
                sku = session.query(SKU).get(entry.sku_id)
                print(f"   [{sku.sku}] {sku.product_name}")
                print(f"      Priority: {entry.priority_score}")
                print(f"      Reason: {entry.reason}")
        else:
            print("   No active watchlist entries")
        
        # Competitor Prices
        print(f"\n💲 Recent Competitor Prices:")
        comp_prices = session.query(CompetitorPrice)\
            .order_by(CompetitorPrice.fetched_at.desc())\
            .limit(3)\
            .all()
        if comp_prices:
            for cp in comp_prices:
                sku = session.query(SKU).get(cp.sku_id)
                print(f"   [{sku.sku}] {sku.product_name}")
                print(f"      Competitor: {cp.competitor_name} - ${cp.competitor_price:.2f}")
                print(f"      Fetched: {cp.fetched_at} | Source: {cp.source}")
        else:
            print("   No competitor prices found")
        
        # Conversion Metrics
        print(f"\n📊 Recent Conversion Metrics:")
        metrics = session.query(ConversionMetric)\
            .order_by(ConversionMetric.created_at.desc())\
            .limit(3)\
            .all()
        if metrics:
            for metric in metrics:
                sku = session.query(SKU).get(metric.sku_id)
                print(f"   [{sku.sku}] {sku.product_name}")
                print(f"      Period: {metric.period_start.date()} to {metric.period_end.date()}")
                print(f"      Funnel: {metric.views} views → {metric.clicks} clicks → {metric.orders} orders")
                print(f"      Revenue: ${metric.revenue:.2f} | Margin: ${metric.gross_margin:.2f}")
        else:
            print("   No conversion metrics found")
        
        # Pricing Decisions
        print(f"\n🤖 Recent Pricing Decisions:")
        decisions = session.query(PricingDecision)\
            .order_by(PricingDecision.decided_at.desc())\
            .limit(3)\
            .all()
        if decisions:
            for decision in decisions:
                sku = session.query(SKU).get(decision.sku_id)
                print(f"   [{sku.sku}] {sku.product_name}")
                print(f"      Action: {decision.action} | New Price: ${decision.new_price or 'N/A'}")
                print(f"      Our Price: ${decision.our_price_at_decision:.2f} | Competitor: ${decision.competitor_price_at_decision:.2f}")
                print(f"      Margin Check: {'✅ Passed' if decision.margin_check_passed else '❌ Failed'}")
                print(f"      Model: {decision.model_used} | Tokens: {decision.tokens_used}")
        else:
            print("   No pricing decisions found")
        
        # Orchestrator Runs
        print(f"\n🎯 Recent Orchestrator Runs:")
        runs = session.query(OrchestratorRun)\
            .order_by(OrchestratorRun.started_at.desc())\
            .limit(3)\
            .all()
        if runs:
            for run in runs:
                print(f"   Run #{run.id} - {run.started_at}")
                print(f"      Watchlist: {run.final_watchlist_size} SKUs (+{run.skus_added}, -{run.skus_removed})")
                print(f"      Cap Used: {run.watchlist_cap_used} | Success: {'✅' if run.success else '❌'}")
                print(f"      Model: {run.model_used} | Tokens: {run.tokens_used}")
                if run.rate_limit_constraint:
                    print(f"      Rate Limit: {run.rate_limit_constraint} ({run.rate_limit_headroom_percent:.1f}% headroom)")
        else:
            print("   No orchestrator runs found")
        
        # Summary
        print(f"\n" + "="*70)
        print(f"Table Record Counts:")
        print(f"   SKUs: {session.query(SKU).count()}")
        print(f"   Watchlist: {session.query(Watchlist).count()}")
        print(f"   Competitor Prices: {session.query(CompetitorPrice).count()}")
        print(f"   Conversion Metrics: {session.query(ConversionMetric).count()}")
        print(f"   Pricing Decisions: {session.query(PricingDecision).count()}")
        print(f"   Orchestrator Runs: {session.query(OrchestratorRun).count()}")


if __name__ == "__main__":
    show_samples()