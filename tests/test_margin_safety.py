"""
Unit tests for margin safety check tool.

This is THE most critical test file in the system. These tests prove
that hard financial constraints are enforced deterministically by code,
not by LLM judgment.

This is the test suite Shahul should be able to defend line-by-line
in an interview as proof that he understands when to trust LLMs
and when NOT to trust them.
"""

import pytest
from datetime import datetime

from margin_check_tool import (
    MarginSafetyChecker,
    MarginCheckInput,
    MarginCheckResult,
    check_margin_safety
)


class TestMarginCalculations:
    """Test margin percentage calculation."""
    
    def test_calculate_margin_basic(self):
        """Test basic margin calculation."""
        checker = MarginSafetyChecker()
        
        # $100 price, $60 cost = 40% margin
        margin = checker.calculate_margin_percent(price=100.0, cost=60.0)
        assert margin == 40.0
    
    def test_calculate_margin_low(self):
        """Test low margin calculation."""
        checker = MarginSafetyChecker()
        
        # $100 price, $88 cost = 12% margin (exactly at floor)
        margin = checker.calculate_margin_percent(price=100.0, cost=88.0)
        assert margin == 12.0
    
    def test_calculate_margin_negative(self):
        """Test negative margin (loss)."""
        checker = MarginSafetyChecker()
        
        # $100 price, $120 cost = -20% margin (selling at a loss)
        margin = checker.calculate_margin_percent(price=100.0, cost=120.0)
        assert margin == -20.0
    
    def test_calculate_margin_zero_price(self):
        """Test margin with zero price (edge case)."""
        checker = MarginSafetyChecker()
        
        margin = checker.calculate_margin_percent(price=0.0, cost=50.0)
        assert margin == 0.0


class TestGapCalculations:
    """Test competitor gap calculation."""
    
    def test_calculate_gap_we_are_higher(self):
        """Test gap when we're more expensive."""
        checker = MarginSafetyChecker()
        
        # We're $100, competitor is $90 = 10% gap (we're higher)
        gap = checker.calculate_gap_percent(our_price=100.0, competitor_price=90.0)
        assert gap == 10.0
    
    def test_calculate_gap_we_are_lower(self):
        """Test gap when we're cheaper."""
        checker = MarginSafetyChecker()
        
        # We're $90, competitor is $100
        # Gap = (90 - 100) / 90 * 100 = -11.11% (we're lower)
        gap = checker.calculate_gap_percent(our_price=90.0, competitor_price=100.0)
        assert gap == -11.11
    
    def test_calculate_gap_equal(self):
        """Test gap when prices are equal."""
        checker = MarginSafetyChecker()
        
        gap = checker.calculate_gap_percent(our_price=100.0, competitor_price=100.0)
        assert gap == 0.0


class TestMarginFloorEnforcement:
    """Test that margin floor is strictly enforced."""
    
    def test_pass_margin_above_floor(self):
        """Test action passes when margin is above floor."""
        checker = MarginSafetyChecker(margin_floor_percent=12.0)
        
        input_data = MarginCheckInput(
            sku_id=1,
            sku_code="TEST-001",
            our_current_price=100.0,
            cost=60.0,  # 40% margin currently
            competitor_price=90.0,
            proposed_action="MATCH",
            proposed_new_price=90.0  # Would give 33.3% margin
        )
        
        result = checker.check_margin_safety(input_data)
        
        assert result.passed is True
        assert result.proposed_margin_percent >= 12.0
        assert "APPROVED" in result.reason
    
    def test_pass_margin_exactly_at_floor(self):
        """Test action passes when margin is exactly at floor."""
        checker = MarginSafetyChecker(margin_floor_percent=12.0)
        
        input_data = MarginCheckInput(
            sku_id=1,
            sku_code="TEST-001",
            our_current_price=100.0,
            cost=88.0,  # 12% margin currently
            competitor_price=90.0,
            proposed_action="MATCH",
            proposed_new_price=100.0  # Keeps 12% margin (exactly at floor)
        )
        
        result = checker.check_margin_safety(input_data)
        
        assert result.passed is True
        assert result.proposed_margin_percent == 12.0
    
    def test_reject_margin_below_floor(self):
        """Test action is rejected when margin falls below floor."""
        checker = MarginSafetyChecker(margin_floor_percent=12.0)
        
        input_data = MarginCheckInput(
            sku_id=1,
            sku_code="TEST-001",
            our_current_price=100.0,
            cost=90.0,  # 10% margin currently
            competitor_price=85.0,
            proposed_action="MATCH",
            proposed_new_price=85.0  # Would give ~5.9% margin (below floor)
        )
        
        result = checker.check_margin_safety(input_data)
        
        assert result.passed is False
        assert result.proposed_margin_percent < 12.0
        assert "REJECTED" in result.reason
        assert "margin" in result.reason.lower()
    
    def test_reject_negative_margin(self):
        """Test action is rejected when margin is negative (selling at loss)."""
        checker = MarginSafetyChecker(margin_floor_percent=12.0)
        
        input_data = MarginCheckInput(
            sku_id=1,
            sku_code="TEST-001",
            our_current_price=100.0,
            cost=95.0,
            competitor_price=90.0,
            proposed_action="MATCH",
            proposed_new_price=90.0  # Would give -5.6% margin (loss!)
        )
        
        result = checker.check_margin_safety(input_data)
        
        assert result.passed is False
        assert result.proposed_margin_percent < 0.0
        assert "REJECTED" in result.reason


class TestGapThresholdEnforcement:
    """Test that gap threshold is enforced."""
    
    def test_pass_gap_above_threshold(self):
        """Test action passes when gap is above threshold."""
        checker = MarginSafetyChecker(
            margin_floor_percent=12.0,
            gap_threshold_percent=5.0
        )
        
        input_data = MarginCheckInput(
            sku_id=1,
            sku_code="TEST-001",
            our_current_price=100.0,
            cost=60.0,
            competitor_price=90.0,  # 10% gap (above 5% threshold)
            proposed_action="MATCH",
            proposed_new_price=90.0
        )
        
        result = checker.check_margin_safety(input_data)
        
        assert result.passed is True
        assert result.competitor_gap_percent >= 5.0
    
    def test_reject_gap_below_threshold(self):
        """Test action is rejected when gap is below threshold."""
        checker = MarginSafetyChecker(
            margin_floor_percent=12.0,
            gap_threshold_percent=5.0
        )
        
        input_data = MarginCheckInput(
            sku_id=1,
            sku_code="TEST-001",
            our_current_price=100.0,
            cost=60.0,
            competitor_price=97.0,  # 3% gap (below 5% threshold)
            proposed_action="MATCH",
            proposed_new_price=97.0
        )
        
        result = checker.check_margin_safety(input_data)
        
        assert result.passed is False
        assert result.competitor_gap_percent < 5.0
        assert "REJECTED" in result.reason
        assert "gap" in result.reason.lower()


class TestHoldAction:
    """Test that HOLD action always passes."""
    
    def test_hold_always_passes(self):
        """Test HOLD action passes regardless of margin or gap."""
        checker = MarginSafetyChecker(
            margin_floor_percent=12.0,
            gap_threshold_percent=5.0
        )
        
        input_data = MarginCheckInput(
            sku_id=1,
            sku_code="TEST-001",
            our_current_price=100.0,
            cost=90.0,  # Only 10% margin (below floor)
            competitor_price=98.0,  # Only 2% gap (below threshold)
            proposed_action="HOLD",
            proposed_new_price=None  # No price change
        )
        
        result = checker.check_margin_safety(input_data)
        
        assert result.passed is True
        assert result.current_margin_percent == result.proposed_margin_percent
        assert "HOLD" in result.reason


class TestActionTypes:
    """Test all action types."""
    
    def test_match_action(self):
        """Test MATCH action (match competitor price)."""
        checker = MarginSafetyChecker(
            margin_floor_percent=12.0,
            gap_threshold_percent=5.0
        )
        
        input_data = MarginCheckInput(
            sku_id=1,
            sku_code="TEST-001",
            our_current_price=100.0,
            cost=60.0,
            competitor_price=90.0,
            proposed_action="MATCH",
            proposed_new_price=90.0
        )
        
        result = checker.check_margin_safety(input_data)
        
        assert result.passed is True
    
    def test_undercut_action(self):
        """Test UNDERCUT_50 action (undercut by $0.50)."""
        checker = MarginSafetyChecker(
            margin_floor_percent=12.0,
            gap_threshold_percent=5.0
        )
        
        input_data = MarginCheckInput(
            sku_id=1,
            sku_code="TEST-001",
            our_current_price=100.0,
            cost=60.0,
            competitor_price=90.0,
            proposed_action="UNDERCUT_50",
            proposed_new_price=89.50  # $0.50 below competitor
        )
        
        result = checker.check_margin_safety(input_data)
        
        assert result.passed is True


class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_missing_new_price_for_action(self):
        """Test rejection when action requires new_price but it's None."""
        checker = MarginSafetyChecker()
        
        input_data = MarginCheckInput(
            sku_id=1,
            sku_code="TEST-001",
            our_current_price=100.0,
            cost=60.0,
            competitor_price=90.0,
            proposed_action="MATCH",
            proposed_new_price=None  # Missing!
        )
        
        result = checker.check_margin_safety(input_data)
        
        assert result.passed is False
        assert "new_price" in result.reason.lower()
    
    def test_result_contains_all_fields(self):
        """Test that result contains all expected fields."""
        checker = MarginSafetyChecker()
        
        input_data = MarginCheckInput(
            sku_id=1,
            sku_code="TEST-001",
            our_current_price=100.0,
            cost=60.0,
            competitor_price=90.0,
            proposed_action="MATCH",
            proposed_new_price=90.0
        )
        
        result = checker.check_margin_safety(input_data)
        
        # Check all fields exist
        assert isinstance(result.passed, bool)
        assert isinstance(result.current_margin_percent, float)
        assert isinstance(result.proposed_margin_percent, float)
        assert isinstance(result.margin_floor_percent, float)
        assert isinstance(result.gap_threshold_percent, float)
        assert isinstance(result.competitor_gap_percent, float)
        assert isinstance(result.reason, str)
        assert isinstance(result.checked_at, datetime)


class TestConvenienceFunction:
    """Test the convenience function."""
    
    def test_convenience_function(self):
        """Test that convenience function works."""
        input_data = MarginCheckInput(
            sku_id=1,
            sku_code="TEST-001",
            our_current_price=100.0,
            cost=60.0,
            competitor_price=90.0,
            proposed_action="MATCH",
            proposed_new_price=90.0
        )
        
        result = check_margin_safety(input_data)
        
        assert isinstance(result, MarginCheckResult)
        assert result.passed is True


class TestRealWorldScenarios:
    """Test realistic scenarios from the spec."""
    
    def test_laptop_scenario_safe_match(self):
        """Test laptop pricing scenario - safe to match."""
        checker = MarginSafetyChecker(
            margin_floor_percent=12.0,
            gap_threshold_percent=5.0
        )
        
        # Laptop: our price $1,200, cost $900 (25% margin)
        # Competitor: $1,100 (8.3% gap)
        # Match would give 18.2% margin (safe)
        
        input_data = MarginCheckInput(
            sku_id=1,
            sku_code="LAP-001",
            our_current_price=1200.0,
            cost=900.0,
            competitor_price=1100.0,
            proposed_action="MATCH",
            proposed_new_price=1100.0
        )
        
        result = checker.check_margin_safety(input_data)
        
        assert result.passed is True
        assert result.proposed_margin_percent > 12.0
        assert result.competitor_gap_percent > 5.0
    
    def test_laptop_scenario_unsafe_match(self):
        """Test laptop pricing scenario - unsafe to match."""
        checker = MarginSafetyChecker(
            margin_floor_percent=12.0,
            gap_threshold_percent=5.0
        )
        
        # Laptop: our price $1,000, cost $920 (8% margin)
        # Competitor: $950 (5% gap)
        # Match would give 3.2% margin (UNSAFE - below 12% floor)
        
        input_data = MarginCheckInput(
            sku_id=1,
            sku_code="LAP-002",
            our_current_price=1000.0,
            cost=920.0,
            competitor_price=950.0,
            proposed_action="MATCH",
            proposed_new_price=950.0
        )
        
        result = checker.check_margin_safety(input_data)
        
        assert result.passed is False
        assert result.proposed_margin_percent < 12.0
        assert "REJECTED" in result.reason