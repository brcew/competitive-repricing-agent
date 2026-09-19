"""
Daily cost comparison summary generator.

This module generates comprehensive cost reports comparing:
1. Two-tier approach (8B worker + 70B orchestrator) - ACTUAL
2. Single large model approach (70B for everything) - HYPOTHETICAL
3. Savings analysis and ROI calculations

The comparison demonstrates the cost optimization benefits of the
hierarchical multi-agent architecture.

This is a KEY PORTFOLIO PIECE showing:
- Cost-conscious AI system design
- Quantitative analysis and reporting
- Trade-off evaluation (cost vs. quality)
- Business value communication
"""

import os
os.environ['USE_LOCAL_CONFIG'] = '1'

import config
import config_local
config.settings = config_local.settings

from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from dataclasses import dataclass

import structlog

from db_utils import get_db_session
from models import PricingDecision, OrchestratorRun
from cost_tracker import get_cost_tracker, GROQ_PRICING

logger = structlog.get_logger(__name__)


@dataclass
class CostComparison:
    """Cost comparison between two-tier and single-model approaches."""
    
    # Actual costs (two-tier)
    actual_worker_calls: int
    actual_worker_tokens: int
    actual_worker_cost: float
    actual_orchestrator_calls: int
    actual_orchestrator_tokens: int
    actual_orchestrator_cost: float
    actual_total_cost: float
    
    # Hypothetical costs (single large model)
    hypothetical_calls: int
    hypothetical_tokens: int
    hypothetical_cost: float
    
    # Comparison
    cost_savings: float
    savings_percent: float
    
    # Metadata
    period_start: datetime
    period_end: datetime
    period_hours: float


class CostComparisonGenerator:
    """
    Generates cost comparison reports.
    
    Compares actual two-tier costs against hypothetical single-model costs.
    """
    
    def __init__(self):
        """Initialize cost comparison generator."""
        self.cost_tracker = get_cost_tracker()
        self.worker_pricing = GROQ_PRICING["llama-3.1-8b-instant"]
        self.orchestrator_pricing = GROQ_PRICING["llama-3.3-70b-versatile"]
        
        logger.info("Cost comparison generator initialized")
    
    def generate_comparison(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> CostComparison:
        """
        Generate cost comparison for a time period.
        
        Args:
            start_date: Start of period (default: 24 hours ago)
            end_date: End of period (default: now)
        
        Returns:
            CostComparison object
        """
        if start_date is None:
            start_date = datetime.utcnow() - timedelta(hours=24)
        if end_date is None:
            end_date = datetime.utcnow()
        
        period_hours = (end_date - start_date).total_seconds() / 3600
        
        # Get actual costs from database
        worker_costs = self.cost_tracker.get_worker_costs_from_db(start_date, end_date)
        orchestrator_costs = self.cost_tracker.get_orchestrator_costs_from_db(start_date, end_date)
        
        actual_total_cost = worker_costs['total_cost_usd'] + orchestrator_costs['total_cost_usd']
        
        # Calculate hypothetical cost (all calls using 70B model)
        total_calls = worker_costs['call_count'] + orchestrator_costs['call_count']
        total_tokens = worker_costs['total_tokens'] + orchestrator_costs['total_tokens']
        
        # Assume same total tokens, but all at 70B pricing
        # Use 55/45 input/output split as average
        hypothetical_input_tokens = int(total_tokens * 0.55)
        hypothetical_output_tokens = total_tokens - hypothetical_input_tokens
        hypothetical_cost = self.orchestrator_pricing.calculate_cost(
            hypothetical_input_tokens,
            hypothetical_output_tokens
        )
        
        # Calculate savings
        cost_savings = hypothetical_cost - actual_total_cost
        savings_percent = (cost_savings / hypothetical_cost * 100) if hypothetical_cost > 0 else 0
        
        return CostComparison(
            actual_worker_calls=worker_costs['call_count'],
            actual_worker_tokens=worker_costs['total_tokens'],
            actual_worker_cost=worker_costs['total_cost_usd'],
            actual_orchestrator_calls=orchestrator_costs['call_count'],
            actual_orchestrator_tokens=orchestrator_costs['total_tokens'],
            actual_orchestrator_cost=orchestrator_costs['total_cost_usd'],
            actual_total_cost=actual_total_cost,
            hypothetical_calls=total_calls,
            hypothetical_tokens=total_tokens,
            hypothetical_cost=hypothetical_cost,
            cost_savings=cost_savings,
            savings_percent=savings_percent,
            period_start=start_date,
            period_end=end_date,
            period_hours=period_hours
        )
    
    def generate_daily_summary(self) -> Dict[str, Any]:
        """
        Generate a comprehensive daily cost summary.
        
        Returns:
            Dict with summary statistics and comparison
        """
        # Get last 24 hours
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(hours=24)
        
        comparison = self.generate_comparison(start_date, end_date)
        
        # Calculate daily projections
        daily_actual_cost = comparison.actual_total_cost * (24 / comparison.period_hours) if comparison.period_hours > 0 else 0
        daily_hypothetical_cost = comparison.hypothetical_cost * (24 / comparison.period_hours) if comparison.period_hours > 0 else 0
        daily_savings = daily_actual_cost - daily_hypothetical_cost
        
        # Calculate monthly projections (30 days)
        monthly_actual_cost = daily_actual_cost * 30
        monthly_hypothetical_cost = daily_hypothetical_cost * 30
        monthly_savings = monthly_actual_cost - monthly_hypothetical_cost
        
        return {
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
                "hours": round(comparison.period_hours, 2)
            },
            "actual_costs": {
                "worker": {
                    "calls": comparison.actual_worker_calls,
                    "tokens": comparison.actual_worker_tokens,
                    "cost_usd": round(comparison.actual_worker_cost, 6),
                    "model": "llama-3.1-8b-instant"
                },
                "orchestrator": {
                    "calls": comparison.actual_orchestrator_calls,
                    "tokens": comparison.actual_orchestrator_tokens,
                    "cost_usd": round(comparison.actual_orchestrator_cost, 6),
                    "model": "llama-3.3-70b-versatile"
                },
                "total": {
                    "calls": comparison.actual_worker_calls + comparison.actual_orchestrator_calls,
                    "tokens": comparison.actual_worker_tokens + comparison.actual_orchestrator_tokens,
                    "cost_usd": round(comparison.actual_total_cost, 6)
                }
            },
            "hypothetical_costs": {
                "scenario": "All calls using llama-3.3-70b-versatile",
                "calls": comparison.hypothetical_calls,
                "tokens": comparison.hypothetical_tokens,
                "cost_usd": round(comparison.hypothetical_cost, 6)
            },
            "comparison": {
                "cost_savings_usd": round(comparison.cost_savings, 6),
                "savings_percent": round(comparison.savings_percent, 2),
                "efficiency_ratio": round(comparison.actual_total_cost / comparison.hypothetical_cost, 4) if comparison.hypothetical_cost > 0 else 0
            },
            "projections": {
                "daily": {
                    "actual_cost_usd": round(daily_actual_cost, 6),
                    "hypothetical_cost_usd": round(daily_hypothetical_cost, 6),
                    "savings_usd": round(daily_savings, 6)
                },
                "monthly": {
                    "actual_cost_usd": round(monthly_actual_cost, 4),
                    "hypothetical_cost_usd": round(monthly_hypothetical_cost, 4),
                    "savings_usd": round(monthly_savings, 4)
                }
            }
        }
    
    def print_summary(self, summary: Optional[Dict[str, Any]] = None) -> None:
        """
        Print a formatted cost summary to console.
        
        Args:
            summary: Summary dict (default: generate new one)
        """
        if summary is None:
            summary = self.generate_daily_summary()
        
        print("\n" + "=" * 80)
        print("DAILY COST COMPARISON SUMMARY")
        print("=" * 80)
        
        # Period
        print(f"\nPeriod: {summary['period']['start']} to {summary['period']['end']}")
        print(f"Duration: {summary['period']['hours']:.1f} hours")
        
        # Actual costs (two-tier approach)
        print("\n" + "-" * 80)
        print("ACTUAL COSTS (Two-Tier Approach)")
        print("-" * 80)
        
        worker = summary['actual_costs']['worker']
        print(f"\nWorker Agent ({worker['model']}):")
        print(f"  Calls:  {worker['calls']:,}")
        print(f"  Tokens: {worker['tokens']:,}")
        print(f"  Cost:   ${worker['cost_usd']:.6f}")
        
        orch = summary['actual_costs']['orchestrator']
        print(f"\nOrchestrator Agent ({orch['model']}):")
        print(f"  Calls:  {orch['calls']:,}")
        print(f"  Tokens: {orch['tokens']:,}")
        print(f"  Cost:   ${orch['cost_usd']:.6f}")
        
        total = summary['actual_costs']['total']
        print(f"\nTotal:")
        print(f"  Calls:  {total['calls']:,}")
        print(f"  Tokens: {total['tokens']:,}")
        print(f"  Cost:   ${total['cost_usd']:.6f}")
        
        # Hypothetical costs (single model)
        print("\n" + "-" * 80)
        print("HYPOTHETICAL COSTS (Single Large Model)")
        print("-" * 80)
        
        hypo = summary['hypothetical_costs']
        print(f"\nScenario: {hypo['scenario']}")
        print(f"  Calls:  {hypo['calls']:,}")
        print(f"  Tokens: {hypo['tokens']:,}")
        print(f"  Cost:   ${hypo['cost_usd']:.6f}")
        
        # Comparison
        print("\n" + "-" * 80)
        print("COST COMPARISON")
        print("-" * 80)
        
        comp = summary['comparison']
        print(f"\nSavings with Two-Tier Approach:")
        print(f"  Cost Reduction: ${comp['cost_savings_usd']:.6f}")
        print(f"  Savings:        {comp['savings_percent']:.2f}%")
        print(f"  Efficiency:     {comp['efficiency_ratio']:.4f}x")
        
        # Projections
        print("\n" + "-" * 80)
        print("COST PROJECTIONS")
        print("-" * 80)
        
        daily = summary['projections']['daily']
        print(f"\nDaily (24 hours):")
        print(f"  Two-Tier:      ${daily['actual_cost_usd']:.6f}")
        print(f"  Single Model:  ${daily['hypothetical_cost_usd']:.6f}")
        print(f"  Savings:       ${daily['savings_usd']:.6f}")
        
        monthly = summary['projections']['monthly']
        print(f"\nMonthly (30 days):")
        print(f"  Two-Tier:      ${monthly['actual_cost_usd']:.4f}")
        print(f"  Single Model:  ${monthly['hypothetical_cost_usd']:.4f}")
        print(f"  Savings:       ${monthly['savings_usd']:.4f}")
        
        print("\n" + "=" * 80)
        print("KEY INSIGHTS")
        print("=" * 80)
        
        print(f"\n• Two-tier approach saves {comp['savings_percent']:.1f}% compared to single model")
        print(f"• Worker agent handles {worker['calls']} calls at lower cost (8B model)")
        print(f"• Orchestrator runs {orch['calls']} strategic decisions (70B model)")
        print(f"• Cost efficiency: {comp['efficiency_ratio']:.2f}x better than single model")
        print(f"• Monthly savings: ${monthly['savings_usd']:.2f}")
        
        print("\n" + "=" * 80 + "\n")
    
    def save_summary_to_file(
        self,
        filename: str = "daily_cost_summary.txt",
        summary: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Save cost summary to a text file.
        
        Args:
            filename: Output filename
            summary: Summary dict (default: generate new one)
        """
        if summary is None:
            summary = self.generate_daily_summary()
        
        import sys
        from io import StringIO
        
        # Capture print output
        old_stdout = sys.stdout
        sys.stdout = StringIO()
        
        self.print_summary(summary)
        
        output = sys.stdout.getvalue()
        sys.stdout = old_stdout
        
        # Write to file
        with open(filename, 'w') as f:
            f.write(output)
        
        logger.info("Cost summary saved to file", filename=filename)
        print(f"Cost summary saved to: {filename}")


# Global instance
_generator = None


def get_cost_comparison_generator() -> CostComparisonGenerator:
    """Get or create the global cost comparison generator."""
    global _generator
    if _generator is None:
        _generator = CostComparisonGenerator()
    return _generator


def generate_and_print_summary() -> Dict[str, Any]:
    """
    Generate and print daily cost summary.
    
    Returns:
        Summary dict
    """
    generator = get_cost_comparison_generator()
    summary = generator.generate_daily_summary()
    generator.print_summary(summary)
    return summary


if __name__ == "__main__":
    """Run cost comparison when executed directly."""
    print("\nGenerating cost comparison summary...\n")
    generate_and_print_summary()
