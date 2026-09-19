"""
Unit tests for budget guard.

These tests verify budget monitoring and stopping logic WITHOUT making real API calls.
All scenarios are simulated with mocked call counts.

Run with: pytest tests/test_budget_guard.py -v
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch

from budget_guard import (
    BudgetGuard,
    BudgetLimits,
    BudgetState
)


# Test 1: Initialize with default limits
def test_init_default_limits():
    """Test initialization with default Groq free tier limits."""
    
    guard = BudgetGuard()
    
    assert guard.limits.daily_limit == 14400
    assert guard.limits.daily_buffer == 50
    assert guard.limits.minute_limit == 30
    assert guard.limits.minute_buffer == 5
    assert guard.daily_calls == 0
    assert guard.minute_calls == 0
    assert guard.stopped == False


# Test 2: Initialize with custom limits
def test_init_custom_limits():
    """Test initialization with custom limits."""
    
    limits = BudgetLimits(
        daily_limit=1000,
        daily_buffer=20,
        minute_limit=10,
        minute_buffer=2
    )
    
    guard = BudgetGuard(limits)
    
    assert guard.limits.daily_limit == 1000
    assert guard.limits.daily_buffer == 20
    assert guard.limits.minute_limit == 10
    assert guard.limits.minute_buffer == 2


# Test 3: Record calls increments counters
def test_record_call_increments():
    """Test that recording calls increments both counters."""
    
    guard = BudgetGuard()
    
    assert guard.daily_calls == 0
    assert guard.minute_calls == 0
    
    guard.record_call()
    
    assert guard.daily_calls == 1
    assert guard.minute_calls == 1
    
    guard.record_call()
    guard.record_call()
    
    assert guard.daily_calls == 3
    assert guard.minute_calls == 3


# Test 4: Check budget when safe
def test_check_budget_safe():
    """Test budget check when well within limits."""
    
    guard = BudgetGuard()
    guard.daily_calls = 100  # Well under 14400
    guard.minute_calls = 5   # Well under 30
    
    state = guard.check_budget()
    
    assert state.status == "SAFE"
    assert state.can_make_call == True
    assert state.calls_today == 100
    assert state.calls_this_minute == 5
    assert "healthy" in state.reason.lower()


# Test 5: Check budget at warning threshold (daily)
def test_check_budget_warning_daily():
    """Test budget warning when approaching daily limit."""
    
    guard = BudgetGuard()
    guard.daily_calls = 11520  # 80% of 14400
    guard.minute_calls = 5
    
    state = guard.check_budget()
    
    assert state.status == "WARNING"
    assert state.can_make_call == True
    assert state.daily_usage_percent >= 80.0


# Test 6: Check budget at warning threshold (minute)
def test_check_budget_warning_minute():
    """Test budget warning when approaching minute limit."""
    
    guard = BudgetGuard()
    guard.daily_calls = 100
    guard.minute_calls = 21  # 70% of 30
    
    state = guard.check_budget()
    
    assert state.status == "WARNING"
    assert state.can_make_call == True
    assert state.minute_usage_percent >= 70.0


# Test 7: Daily budget exhausted (stop threshold reached)
def test_daily_budget_exhausted():
    """Test that guard stops at daily threshold (limit - buffer)."""
    
    guard = BudgetGuard()
    guard.daily_calls = 14350  # 14400 - 50 = 14350
    guard.minute_calls = 5
    
    state = guard.check_budget()
    
    assert state.status == "EXHAUSTED"
    assert state.can_make_call == False
    assert guard.stopped == True
    assert "daily budget exhausted" in state.reason.lower()
    assert "50 call buffer" in state.reason.lower()


# Test 8: Minute rate limit reached
def test_minute_rate_limit_reached():
    """Test that guard pauses at minute threshold (limit - buffer)."""
    
    guard = BudgetGuard()
    guard.daily_calls = 100
    guard.minute_calls = 25  # 30 - 5 = 25
    
    state = guard.check_budget()
    
    assert state.status == "CRITICAL"
    assert state.can_make_call == False
    assert guard.stopped == False  # Minute limits don't permanently stop
    assert "minute rate limit" in state.reason.lower()


# Test 9: Can make call returns correct status
def test_can_make_call_safe():
    """Test can_make_call when budget is safe."""
    
    guard = BudgetGuard()
    guard.daily_calls = 100
    guard.minute_calls = 5
    
    allowed, reason = guard.can_make_call()
    
    assert allowed == True
    assert "healthy" in reason.lower()


# Test 10: Can make call blocked when exhausted
def test_can_make_call_blocked():
    """Test can_make_call when budget is exhausted."""
    
    guard = BudgetGuard()
    guard.daily_calls = 14350  # At stop threshold
    guard.minute_calls = 5
    
    allowed, reason = guard.can_make_call()
    
    assert allowed == False
    assert "exhausted" in reason.lower()


# Test 11: Daily counter resets on new day
def test_daily_counter_resets():
    """Test that daily counter resets when day changes."""
    
    guard = BudgetGuard()
    guard.daily_calls = 1000
    guard.last_reset_day = datetime.utcnow().date() - timedelta(days=1)  # Yesterday
    
    # Check budget should trigger reset
    state = guard.check_budget()
    
    assert guard.daily_calls == 0
    assert guard.last_reset_day == datetime.utcnow().date()


# Test 12: Minute counter resets on new minute
def test_minute_counter_resets():
    """Test that minute counter resets when minute changes."""
    
    guard = BudgetGuard()
    guard.minute_calls = 20
    guard.last_reset_minute = datetime.utcnow().replace(second=0, microsecond=0) - timedelta(minutes=1)
    
    # Check budget should trigger reset
    state = guard.check_budget()
    
    assert guard.minute_calls == 0


# Test 13: Stop state persists within same day
def test_stop_persists_same_day():
    """Test that stop state persists for same day."""
    
    guard = BudgetGuard()
    guard.daily_calls = 14350  # At threshold
    
    # First check - stops
    state1 = guard.check_budget()
    assert state1.can_make_call == False
    assert guard.stopped == True
    
    # Second check - still stopped
    state2 = guard.check_budget()
    assert state2.can_make_call == False
    assert guard.stopped == True


# Test 14: Stop state resets on new day
def test_stop_resets_new_day():
    """Test that stop state resets when day changes."""
    
    guard = BudgetGuard()
    guard.daily_calls = 14350  # At threshold
    guard.stopped = True
    guard.stop_reason = "Daily budget exhausted"
    guard.last_reset_day = datetime.utcnow().date() - timedelta(days=1)
    
    # Check budget on new day
    state = guard.check_budget()
    
    assert guard.daily_calls == 0
    assert guard.stopped == False
    assert state.can_make_call == True


# Test 15: Minute limit recovers after minute
def test_minute_limit_recovers():
    """Test that minute limit block recovers after minute passes."""
    
    guard = BudgetGuard()
    guard.daily_calls = 100
    guard.minute_calls = 25  # At minute threshold
    guard.last_reset_minute = datetime.utcnow().replace(second=0, microsecond=0) - timedelta(minutes=1)
    
    # Check budget - should reset minute counter
    state = guard.check_budget()
    
    assert guard.minute_calls == 0
    assert state.can_make_call == True


# Test 16: Daily stop threshold calculation
def test_daily_stop_threshold():
    """Test that daily stop threshold is correctly calculated."""
    
    limits = BudgetLimits(daily_limit=14400, daily_buffer=50)
    
    threshold = limits.get_daily_stop_threshold()
    
    assert threshold == 14350  # 14400 - 50


# Test 17: Minute stop threshold calculation
def test_minute_stop_threshold():
    """Test that minute stop threshold is correctly calculated."""
    
    limits = BudgetLimits(minute_limit=30, minute_buffer=5)
    
    threshold = limits.get_minute_stop_threshold()
    
    assert threshold == 25  # 30 - 5


# Test 18: Get status summary
def test_get_status_summary():
    """Test getting status summary dict."""
    
    guard = BudgetGuard()
    guard.daily_calls = 1000
    guard.minute_calls = 10
    
    summary = guard.get_status_summary()
    
    assert summary['status'] in ['SAFE', 'WARNING', 'CRITICAL', 'EXHAUSTED']
    assert 'daily' in summary
    assert 'minute' in summary
    assert summary['daily']['calls'] == 1000
    assert summary['minute']['calls'] == 10
    assert 'can_make_call' in summary
    assert 'reason' in summary


# Test 19: Manual reset
def test_manual_reset():
    """Test manual reset of budget guard."""
    
    guard = BudgetGuard()
    guard.daily_calls = 1000
    guard.minute_calls = 20
    guard.stopped = True
    guard.stop_reason = "Test"
    guard.warnings_issued = {'daily': True, 'minute': True}
    
    guard.reset()
    
    assert guard.daily_calls == 0
    assert guard.minute_calls == 0
    assert guard.stopped == False
    assert guard.stop_reason == None
    assert guard.warnings_issued == {'daily': False, 'minute': False}


# Test 20: Warning issued only once per period
def test_warning_issued_once():
    """Test that warnings are only issued once per period."""
    
    guard = BudgetGuard()
    guard.daily_calls = 11520  # 80% - triggers warning
    
    # First check - warning issued
    state1 = guard.check_budget()
    assert state1.status == "WARNING"
    assert guard.warnings_issued['daily'] == True
    
    # Second check - warning already issued
    guard.daily_calls = 12000  # Still in warning zone
    state2 = guard.check_budget()
    assert state2.status == "WARNING"
    # Warning flag should still be True (not reset)


# Test 21: Daily usage percent calculation
def test_daily_usage_percent():
    """Test daily usage percentage calculation."""
    
    guard = BudgetGuard()
    guard.daily_calls = 7200  # 50% of 14400
    
    state = guard.check_budget()
    
    assert state.daily_usage_percent == 50.0


# Test 22: Minute usage percent calculation
def test_minute_usage_percent():
    """Test minute usage percentage calculation."""
    
    guard = BudgetGuard()
    guard.minute_calls = 15  # 50% of 30
    
    state = guard.check_budget()
    
    assert state.minute_usage_percent == 50.0


# Test 23: Remaining calls calculation (daily)
def test_remaining_calls_daily():
    """Test remaining calls calculation for daily limit."""
    
    guard = BudgetGuard()
    guard.daily_calls = 14300
    
    state = guard.check_budget()
    
    assert state.daily_remaining == 100  # 14400 - 14300


# Test 24: Remaining calls calculation (minute)
def test_remaining_calls_minute():
    """Test remaining calls calculation for minute limit."""
    
    guard = BudgetGuard()
    guard.minute_calls = 22
    
    state = guard.check_budget()
    
    assert state.minute_remaining == 8  # 30 - 22


# Test 25: Both limits near threshold
def test_both_limits_near_threshold():
    """Test behavior when both daily and minute limits are near threshold."""
    
    guard = BudgetGuard()
    guard.daily_calls = 14340  # Near daily threshold (14350)
    guard.minute_calls = 24    # Near minute threshold (25)
    
    state = guard.check_budget()
    
    # Should still be able to make calls (not at threshold yet)
    assert state.can_make_call == True
    assert state.status == "WARNING"  # But should be in warning


# Test 26: Exactly at daily threshold
def test_exactly_at_daily_threshold():
    """Test behavior when exactly at daily stop threshold."""
    
    guard = BudgetGuard()
    guard.daily_calls = 14350  # Exactly at threshold
    
    state = guard.check_budget()
    
    assert state.can_make_call == False
    assert state.status == "EXHAUSTED"
    assert guard.stopped == True


# Test 27: One call below daily threshold
def test_one_below_daily_threshold():
    """Test behavior when one call below daily stop threshold."""
    
    guard = BudgetGuard()
    guard.daily_calls = 14349  # One below threshold (14350)
    
    state = guard.check_budget()
    
    assert state.can_make_call == True  # Still allowed
    assert state.status == "WARNING"  # But warning status


# Test 28: Zero calls edge case
def test_zero_calls():
    """Test budget check with zero calls."""
    
    guard = BudgetGuard()
    
    state = guard.check_budget()
    
    assert state.calls_today == 0
    assert state.calls_this_minute == 0
    assert state.can_make_call == True
    assert state.status == "SAFE"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
