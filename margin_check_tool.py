"""
Deterministic margin safety check tool.

This is THE critical safety mechanism in the system. The 12% margin floor
is enforced by plain Python code, NOT by LLM judgment. This is the single
most important proof point that the system understands hard constraints
cannot be delegated to probabilistic models.

The margin check tool:
1. Takes proposed price action as input
2. Calculates resulting margin
3. REJECTS any action that would violate the floor
4. Logs all decisions with reasoning
5. Returns explicit pass/fail with explanation

This is deliberately NOT part of the agent's prompt or reasoning -
it's a hard gate that the agent's output must pass through.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, Literal

import structlog

from config import settings

logger = structlog.get_logger(__name__)


@dataclass
class MarginCheckInput:
    """Input parameters for margin safety check."""
    sku_id: int
    sku_code: str
    our_current_price: float
    cost: float
    competitor_price: float
    proposed_action: Literal["MATCH", "UNDERCUT_50", "HOLD"]
    proposed_new_price: Optional[float]  # None if action is HOLD


@dataclass
class MarginCheckResult:
    """Result of margin safety check."""
    passed: bool
    current_margin_percent: float
    proposed_margin_percent: float
    margin_floor_percent: float
    gap_threshold_percent: float
    competitor_gap_percent: float
    reason: str
    checked_at: datetime


class MarginSafetyChecker:
    """
    Enforces margin floor and gap threshold rules.
    
    Rules (from spec):
    1. Margin Floor: Resulting gross margin must be >= 12%
    2. Gap Threshold: Only act if competitor gap > 5%
    
    Both rules must pass for the action to be approved.
    """
    
    def __init__(
        self,
        margin_floor_percent: float = None,
        gap_threshold_percent: float = None
    ):
        """
        Initialize margin checker with configuration.
        
        Args:
            margin_floor_percent: Minimum allowed margin (default from config)
            gap_threshold_percent: Minimum competitor gap to act (default from config)
        """
        self.margin_floor_percent = (
            margin_floor_percent 
            if margin_floor_percent is not None 
            else settings.margin_floor_percent
        )
        
        self.gap_threshold_percent = (
            gap_threshold_percent
            if gap_threshold_percent is not None
            else settings.competitor_gap_threshold_percent
        )
    
    def calculate_margin_percent(self, price: float, cost: float) -> float:
        """
        Calculate gross margin percentage.
        
        Formula: margin% = (price - cost) / price * 100
        
        Args:
            price: Selling price
            cost: Product cost
        
        Returns:
            Margin percentage (e.g., 25.5 for 25.5%)
        """
        if price <= 0:
            return 0.0
        
        margin_dollars = price - cost
        margin_percent = (margin_dollars / price) * 100.0
        
        return round(margin_percent, 2)
    
    def calculate_gap_percent(self, our_price: float, competitor_price: float) -> float:
        """
        Calculate price gap between us and competitor.
        
        Positive gap means we're more expensive.
        Negative gap means we're cheaper.
        
        Args:
            our_price: Our current price
            competitor_price: Competitor's price
        
        Returns:
            Gap percentage (e.g., 10.5 means we're 10.5% more expensive)
        """
        if our_price <= 0:
            return 0.0
        
        gap = ((our_price - competitor_price) / our_price) * 100.0
        
        return round(gap, 2)
    
    def check_margin_safety(self, input_data: MarginCheckInput) -> MarginCheckResult:
        """
        Perform margin safety check on proposed pricing action.
        
        This is the critical enforcement point. No action proceeds without
        passing this check.
        
        Args:
            input_data: Margin check input parameters
        
        Returns:
            MarginCheckResult with pass/fail and detailed reasoning
        """
        # Calculate current state
        current_margin = self.calculate_margin_percent(
            input_data.our_current_price,
            input_data.cost
        )
        
        competitor_gap = self.calculate_gap_percent(
            input_data.our_current_price,
            input_data.competitor_price
        )
        
        # Handle HOLD action (no price change)
        if input_data.proposed_action == "HOLD":
            return MarginCheckResult(
                passed=True,  # HOLD always passes (no risk)
                current_margin_percent=current_margin,
                proposed_margin_percent=current_margin,  # Unchanged
                margin_floor_percent=self.margin_floor_percent,
                gap_threshold_percent=self.gap_threshold_percent,
                competitor_gap_percent=competitor_gap,
                reason="HOLD action requires no margin check (price unchanged)",
                checked_at=datetime.now(timezone.utc)
            )
        
        # Validate proposed new price exists
        if input_data.proposed_new_price is None:
            return MarginCheckResult(
                passed=False,
                current_margin_percent=current_margin,
                proposed_margin_percent=0.0,
                margin_floor_percent=self.margin_floor_percent,
                gap_threshold_percent=self.gap_threshold_percent,
                competitor_gap_percent=competitor_gap,
                reason="REJECTED: Action requires new_price but none provided",
                checked_at=datetime.now(timezone.utc)
            )
        
        # Calculate proposed margin
        proposed_margin = self.calculate_margin_percent(
            input_data.proposed_new_price,
            input_data.cost
        )
        
        # Rule 1: Check margin floor
        if proposed_margin < self.margin_floor_percent:
            reason = (
                f"REJECTED: Proposed margin {proposed_margin:.1f}% "
                f"< floor {self.margin_floor_percent:.1f}%. "
                f"Price ${input_data.proposed_new_price:.2f} would violate margin safety rule."
            )
            
            logger.warning(
                "Margin floor violation",
                sku=input_data.sku_code,
                proposed_price=input_data.proposed_new_price,
                proposed_margin=proposed_margin,
                margin_floor=self.margin_floor_percent,
                action=input_data.proposed_action
            )
            
            return MarginCheckResult(
                passed=False,
                current_margin_percent=current_margin,
                proposed_margin_percent=proposed_margin,
                margin_floor_percent=self.margin_floor_percent,
                gap_threshold_percent=self.gap_threshold_percent,
                competitor_gap_percent=competitor_gap,
                reason=reason,
                checked_at=datetime.now(timezone.utc)
            )
        
        # Rule 2: Check gap threshold
        if competitor_gap < self.gap_threshold_percent:
            reason = (
                f"REJECTED: Competitor gap {competitor_gap:.1f}% "
                f"< threshold {self.gap_threshold_percent:.1f}%. "
                f"Price difference too small to justify action."
            )
            
            logger.info(
                "Gap threshold not met",
                sku=input_data.sku_code,
                competitor_gap=competitor_gap,
                gap_threshold=self.gap_threshold_percent,
                action=input_data.proposed_action
            )
            
            return MarginCheckResult(
                passed=False,
                current_margin_percent=current_margin,
                proposed_margin_percent=proposed_margin,
                margin_floor_percent=self.margin_floor_percent,
                gap_threshold_percent=self.gap_threshold_percent,
                competitor_gap_percent=competitor_gap,
                reason=reason,
                checked_at=datetime.now(timezone.utc)
            )
        
        # Both rules passed
        reason = (
            f"APPROVED: Margin {proposed_margin:.1f}% >= {self.margin_floor_percent:.1f}% floor, "
            f"gap {competitor_gap:.1f}% >= {self.gap_threshold_percent:.1f}% threshold. "
            f"Safe to change price from ${input_data.our_current_price:.2f} "
            f"to ${input_data.proposed_new_price:.2f}."
        )
        
        logger.info(
            "Margin check passed",
            sku=input_data.sku_code,
            current_price=input_data.our_current_price,
            proposed_price=input_data.proposed_new_price,
            proposed_margin=proposed_margin,
            competitor_gap=competitor_gap,
            action=input_data.proposed_action
        )
        
        return MarginCheckResult(
            passed=True,
            current_margin_percent=current_margin,
            proposed_margin_percent=proposed_margin,
            margin_floor_percent=self.margin_floor_percent,
            gap_threshold_percent=self.gap_threshold_percent,
            competitor_gap_percent=competitor_gap,
            reason=reason,
            checked_at=datetime.now(timezone.utc)
        )


# Global checker instance
_checker = None


def get_margin_checker() -> MarginSafetyChecker:
    """Get or create the global margin checker instance."""
    global _checker
    if _checker is None:
        _checker = MarginSafetyChecker()
    return _checker


# Convenience function for easy access
def check_margin_safety(input_data: MarginCheckInput) -> MarginCheckResult:
    """
    Check margin safety (convenience function).
    
    This is the function that worker agents will call.
    """
    checker = get_margin_checker()
    return checker.check_margin_safety(input_data)