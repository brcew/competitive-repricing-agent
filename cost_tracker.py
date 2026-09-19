"""
Cost tracker for Groq API usage.

Tracks tokens and costs for every model call to enable:
1. Budget monitoring and alerts
2. Cost comparison analysis (AI pricing vs. potential revenue impact)
3. ROI calculation for the pricing system
4. Per-SKU profitability analysis

Groq Pricing (2026):
- Llama 3.1 8B Instant:      $0.05/1M input, $0.08/1M output
- Llama 3.3 70B Versatile:   $0.59/1M input, $0.79/1M output

Free Tier Limits:
- ~14,400 requests per day
- ~12K tokens per minute (varies by model)

This module provides the foundation for T11 (budget guard) and T15 (cost reports).
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Literal

import structlog
from sqlalchemy import func

from db_utils import get_db_session
from models import PricingDecision, OrchestratorRun

logger = structlog.get_logger(__name__)


ModelName = Literal[
    "llama-3.1-8b-instant",
    "llama-3.3-70b-versatile",
    "other"
]


@dataclass
class ModelPricing:
    """Pricing information for a specific model."""
    
    model_name: str
    input_cost_per_million: float   # USD per 1M input tokens
    output_cost_per_million: float  # USD per 1M output tokens
    
    def calculate_cost(
        self,
        input_tokens: int,
        output_tokens: int
    ) -> float:
        """
        Calculate cost for a single API call.
        
        Args:
            input_tokens: Number of input (prompt) tokens
            output_tokens: Number of output (completion) tokens
        
        Returns:
            Cost in USD
        """
        input_cost = (input_tokens / 1_000_000) * self.input_cost_per_million
        output_cost = (output_tokens / 1_000_000) * self.output_cost_per_million
        
        return input_cost + output_cost


# Groq pricing table (2026)
GROQ_PRICING = {
    "llama-3.1-8b-instant": ModelPricing(
        model_name="llama-3.1-8b-instant",
        input_cost_per_million=0.05,   # $0.05 per 1M tokens
        output_cost_per_million=0.08   # $0.08 per 1M tokens
    ),
    "llama-3.3-70b-versatile": ModelPricing(
        model_name="llama-3.3-70b-versatile",
        input_cost_per_million=0.59,   # $0.59 per 1M tokens
        output_cost_per_million=0.79   # $0.79 per 1M tokens
    )
}


@dataclass
class CostRecord:
    """Cost record for a single API call."""
    
    model_name: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    input_cost_usd: float
    output_cost_usd: float
    total_cost_usd: float
    timestamp: datetime
    call_type: str  # 'worker' or 'orchestrator'


class CostTracker:
    """
    Tracks costs for all Groq API calls.
    
    Features:
    - Per-call cost calculation
    - Cumulative cost tracking
    - Daily/hourly aggregation
    - Budget monitoring
    - Cost comparison analysis
    """
    
    def __init__(self):
        """Initialize cost tracker."""
        self.session_start = datetime.now(timezone.utc)
        self.calls_this_session = 0
        self.cost_this_session = 0.0
        
        logger.info("Cost tracker initialized", session_start=self.session_start)
    
    def get_model_pricing(self, model_name: str) -> ModelPricing:
        """
        Get pricing for a model.
        
        Args:
            model_name: Model name (with or without 'groq/' prefix)
        
        Returns:
            ModelPricing for the model
        """
        # Strip 'groq/' prefix if present
        clean_name = model_name.replace("groq/", "")
        
        if clean_name in GROQ_PRICING:
            return GROQ_PRICING[clean_name]
        
        # Fallback for unknown models (use 8B pricing as conservative estimate)
        logger.warning(
            "Unknown model, using fallback pricing",
            model=model_name
        )
        return GROQ_PRICING["llama-3.1-8b-instant"]
    
    def calculate_call_cost(
        self,
        model_name: str,
        input_tokens: int,
        output_tokens: int,
        call_type: str = "unknown"
    ) -> CostRecord:
        """
        Calculate cost for a single API call.
        
        Args:
            model_name: Name of the model used
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            call_type: 'worker' or 'orchestrator'
        
        Returns:
            CostRecord with detailed cost breakdown
        """
        pricing = self.get_model_pricing(model_name)
        
        input_cost = (input_tokens / 1_000_000) * pricing.input_cost_per_million
        output_cost = (output_tokens / 1_000_000) * pricing.output_cost_per_million
        total_cost = input_cost + output_cost
        
        record = CostRecord(
            model_name=model_name,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            input_cost_usd=input_cost,
            output_cost_usd=output_cost,
            total_cost_usd=total_cost,
            timestamp=datetime.now(timezone.utc),
            call_type=call_type
        )
        
        # Update session counters
        self.calls_this_session += 1
        self.cost_this_session += total_cost
        
        logger.debug(
            "API call cost calculated",
            model=model_name,
            tokens=f"{input_tokens}+{output_tokens}={record.total_tokens}",
            cost=f"${total_cost:.6f}",
            call_type=call_type
        )
        
        return record
    
    def get_worker_costs_from_db(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, any]:
        """
        Get worker agent costs from database.
        
        Args:
            start_date: Start of date range (default: 24 hours ago)
            end_date: End of date range (default: now)
        
        Returns:
            Dict with cost statistics
        """
        if start_date is None:
            start_date = datetime.now(timezone.utc) - timedelta(hours=24)
        if end_date is None:
            end_date = datetime.now(timezone.utc)
        
        with get_db_session() as session:
            # Get all decisions in date range
            decisions = session.query(PricingDecision)\
                .filter(
                    PricingDecision.decided_at >= start_date,
                    PricingDecision.decided_at <= end_date
                )\
                .all()
            
            if not decisions:
                return {
                    "call_count": 0,
                    "total_tokens": 0,
                    "total_cost_usd": 0.0,
                    "avg_tokens_per_call": 0,
                    "avg_cost_per_call": 0.0,
                    "period_start": start_date,
                    "period_end": end_date
                }
            
            total_tokens = 0
            total_cost = 0.0
            
            for decision in decisions:
                if decision.tokens_used:
                    total_tokens += decision.tokens_used
                    
                    # Calculate cost (assuming 50/50 input/output split as approximation)
                    input_tokens = decision.tokens_used // 2
                    output_tokens = decision.tokens_used - input_tokens
                    
                    pricing = self.get_model_pricing(decision.model_used)
                    cost = pricing.calculate_cost(input_tokens, output_tokens)
                    total_cost += cost
            
            call_count = len(decisions)
            
            return {
                "call_count": call_count,
                "total_tokens": total_tokens,
                "total_cost_usd": total_cost,
                "avg_tokens_per_call": total_tokens / call_count if call_count > 0 else 0,
                "avg_cost_per_call": total_cost / call_count if call_count > 0 else 0.0,
                "period_start": start_date,
                "period_end": end_date
            }
    
    def get_orchestrator_costs_from_db(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, any]:
        """
        Get orchestrator agent costs from database.
        
        Args:
            start_date: Start of date range (default: 24 hours ago)
            end_date: End of date range (default: now)
        
        Returns:
            Dict with cost statistics
        """
        if start_date is None:
            start_date = datetime.now(timezone.utc) - timedelta(hours=24)
        if end_date is None:
            end_date = datetime.now(timezone.utc)
        
        with get_db_session() as session:
            # Get all runs in date range
            runs = session.query(OrchestratorRun)\
                .filter(
                    OrchestratorRun.started_at >= start_date,
                    OrchestratorRun.started_at <= end_date
                )\
                .all()
            
            if not runs:
                return {
                    "call_count": 0,
                    "total_tokens": 0,
                    "total_cost_usd": 0.0,
                    "avg_tokens_per_call": 0,
                    "avg_cost_per_call": 0.0,
                    "period_start": start_date,
                    "period_end": end_date
                }
            
            total_tokens = 0
            total_cost = 0.0
            
            for run in runs:
                if run.tokens_used:
                    total_tokens += run.tokens_used
                    
                    # Calculate cost (assuming 60/40 input/output for orchestrator)
                    input_tokens = int(run.tokens_used * 0.6)
                    output_tokens = run.tokens_used - input_tokens
                    
                    pricing = self.get_model_pricing(run.model_used)
                    cost = pricing.calculate_cost(input_tokens, output_tokens)
                    total_cost += cost
            
            call_count = len(runs)
            
            return {
                "call_count": call_count,
                "total_tokens": total_tokens,
                "total_cost_usd": total_cost,
                "avg_tokens_per_call": total_tokens / call_count if call_count > 0 else 0,
                "avg_cost_per_call": total_cost / call_count if call_count > 0 else 0.0,
                "period_start": start_date,
                "period_end": end_date
            }
    
    def get_total_costs_from_db(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, any]:
        """
        Get total system costs from database.
        
        Args:
            start_date: Start of date range (default: 24 hours ago)
            end_date: End of date range (default: now)
        
        Returns:
            Dict with combined cost statistics
        """
        worker_costs = self.get_worker_costs_from_db(start_date, end_date)
        orchestrator_costs = self.get_orchestrator_costs_from_db(start_date, end_date)
        
        total_calls = worker_costs['call_count'] + orchestrator_costs['call_count']
        total_tokens = worker_costs['total_tokens'] + orchestrator_costs['total_tokens']
        total_cost = worker_costs['total_cost_usd'] + orchestrator_costs['total_cost_usd']
        
        return {
            "period_start": start_date or (datetime.now(timezone.utc) - timedelta(hours=24)),
            "period_end": end_date or datetime.now(timezone.utc),
            "worker": worker_costs,
            "orchestrator": orchestrator_costs,
            "total_calls": total_calls,
            "total_tokens": total_tokens,
            "total_cost_usd": total_cost,
            "avg_tokens_per_call": total_tokens / total_calls if total_calls > 0 else 0,
            "avg_cost_per_call": total_cost / total_calls if total_calls > 0 else 0.0,
            "cost_breakdown": {
                "worker_percent": (worker_costs['total_cost_usd'] / total_cost * 100) if total_cost > 0 else 0,
                "orchestrator_percent": (orchestrator_costs['total_cost_usd'] / total_cost * 100) if total_cost > 0 else 0
            }
        }
    
    def estimate_daily_cost(self) -> Dict[str, any]:
        """
        Estimate daily cost based on recent usage.
        
        Uses last 24 hours of data to project daily costs.
        
        Returns:
            Dict with daily cost estimate
        """
        costs = self.get_total_costs_from_db()
        
        # Calculate hourly rate
        hours_in_period = (costs['period_end'] - costs['period_start']).total_seconds() / 3600
        if hours_in_period == 0:
            hours_in_period = 24
        
        hourly_cost = costs['total_cost_usd'] / hours_in_period
        daily_cost = hourly_cost * 24
        
        # Calculate daily call rate
        hourly_calls = costs['total_calls'] / hours_in_period
        daily_calls = hourly_calls * 24
        
        return {
            "estimated_daily_cost_usd": daily_cost,
            "estimated_daily_calls": int(daily_calls),
            "based_on_hours": hours_in_period,
            "actual_cost_in_period": costs['total_cost_usd'],
            "actual_calls_in_period": costs['total_calls']
        }
    
    def check_budget_status(
        self,
        daily_budget_usd: float = 1.0
    ) -> Dict[str, any]:
        """
        Check current budget status.
        
        Args:
            daily_budget_usd: Daily budget in USD
        
        Returns:
            Dict with budget status
        """
        estimate = self.estimate_daily_cost()
        
        budget_used_percent = (estimate['estimated_daily_cost_usd'] / daily_budget_usd * 100) if daily_budget_usd > 0 else 0
        budget_remaining = daily_budget_usd - estimate['estimated_daily_cost_usd']
        
        # Determine status
        if budget_used_percent < 50:
            status = "HEALTHY"
        elif budget_used_percent < 80:
            status = "WARNING"
        elif budget_used_percent < 100:
            status = "CRITICAL"
        else:
            status = "OVER_BUDGET"
        
        return {
            "status": status,
            "daily_budget_usd": daily_budget_usd,
            "estimated_daily_cost_usd": estimate['estimated_daily_cost_usd'],
            "budget_used_percent": budget_used_percent,
            "budget_remaining_usd": budget_remaining,
            "estimated_daily_calls": estimate['estimated_daily_calls']
        }
    
    def get_session_summary(self) -> Dict[str, any]:
        """Get cost summary for current session."""
        return {
            "session_start": self.session_start,
            "calls_this_session": self.calls_this_session,
            "cost_this_session_usd": self.cost_this_session,
            "avg_cost_per_call": self.cost_this_session / self.calls_this_session if self.calls_this_session > 0 else 0.0
        }


# Global tracker instance
_tracker = None


def get_cost_tracker() -> CostTracker:
    """Get or create the global cost tracker instance."""
    global _tracker
    if _tracker is None:
        _tracker = CostTracker()
    return _tracker


# Convenience functions
def calculate_call_cost(
    model_name: str,
    input_tokens: int,
    output_tokens: int,
    call_type: str = "unknown"
) -> CostRecord:
    """Calculate cost for a single API call."""
    tracker = get_cost_tracker()
    return tracker.calculate_call_cost(model_name, input_tokens, output_tokens, call_type)


def get_total_costs(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
) -> Dict[str, any]:
    """Get total system costs from database."""
    tracker = get_cost_tracker()
    return tracker.get_total_costs_from_db(start_date, end_date)


def check_budget_status(daily_budget_usd: float = 1.0) -> Dict[str, any]:
    """Check current budget status."""
    tracker = get_cost_tracker()
    return tracker.check_budget_status(daily_budget_usd)
