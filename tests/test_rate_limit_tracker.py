"""
Unit tests for rate limit tracker and dynamic watchlist cap adjustment.

These tests verify the rate limit monitoring WITHOUT making real API calls.
All rate limit headers are mocked.

Run with: pytest tests/test_rate_limit_tracker.py -v
"""

import pytest
from datetime import datetime
from unittest.mock import MagicMock

from rate_limit_tracker import (
    RateLimitStatus,
    RateLimitTracker
)


# Test 1: Parse rate limit headers with all fields present
def test_parse_complete_headers():
    """Test parsing headers with all rate limit fields."""
    
    headers = {
        "x-ratelimit-limit-requests": "30",
        "x-ratelimit-remaining-requests": "25",
        "x-ratelimit-limit-tokens": "12000",
        "x-ratelimit-remaining-tokens": "10000",
        "x-ratelimit-reset-requests": "1722556800",  # Unix timestamp
        "x-ratelimit-reset-tokens": "1722556800"
    }
    
    tracker = RateLimitTracker()
    status = tracker.parse_rate_limit_headers(headers)
    
    assert status.requests_limit == 30
    assert status.requests_remaining == 25
    assert status.tokens_limit == 12000
    assert status.tokens_remaining == 10000
    assert status.requests_usage_percent == pytest.approx(16.67, rel=0.01)  # Used 5/30
    assert status.tokens_usage_percent == pytest.approx(16.67, rel=0.01)    # Used 2000/12000


# Test 2: Parse headers with missing fields (partial data)
def test_parse_partial_headers():
    """Test parsing headers with some fields missing."""
    
    headers = {
        "x-ratelimit-limit-requests": "30",
        "x-ratelimit-remaining-requests": "10"
        # Missing token headers
    }
    
    tracker = RateLimitTracker()
    status = tracker.parse_rate_limit_headers(headers)
    
    assert status.requests_limit == 30
    assert status.requests_remaining == 10
    assert status.tokens_limit is None
    assert status.tokens_remaining is None
    assert status.requests_usage_percent == pytest.approx(66.67, rel=0.01)  # Used 20/30


# Test 3: Parse headers with case-insensitive keys
def test_parse_case_insensitive_headers():
    """Test that header parsing is case-insensitive."""
    
    headers = {
        "X-RateLimit-Limit-Requests": "30",  # Capital letters
        "x-ratelimit-remaining-requests": "20"  # Lowercase
    }
    
    tracker = RateLimitTracker()
    status = tracker.parse_rate_limit_headers(headers)
    
    assert status.requests_limit == 30
    assert status.requests_remaining == 20


# Test 4: Calculate headroom with healthy limits
def test_calculate_headroom_healthy():
    """Test headroom calculation when plenty of quota remaining."""
    
    status = RateLimitStatus(
        requests_limit=30,
        requests_remaining=28,  # 93% remaining
        tokens_limit=12000,
        tokens_remaining=11000  # 92% remaining
    )
    
    tracker = RateLimitTracker()
    headroom = tracker.calculate_headroom_percent(status)
    
    # Headroom is minimum of both = 92%
    assert headroom == pytest.approx(91.67, rel=0.01)


# Test 5: Calculate headroom when approaching limits
def test_calculate_headroom_low():
    """Test headroom calculation when close to limits."""
    
    status = RateLimitStatus(
        requests_limit=30,
        requests_remaining=3,  # 10% remaining
        tokens_limit=12000,
        tokens_remaining=6000  # 50% remaining
    )
    
    tracker = RateLimitTracker()
    headroom = tracker.calculate_headroom_percent(status)
    
    # Headroom is minimum = 10%
    assert headroom == 10.0


# Test 6: Should reduce cap when headroom low
def test_should_reduce_cap():
    """Test that cap reduction triggers when headroom below threshold."""
    
    tracker = RateLimitTracker(
        min_watchlist_cap=5,
        max_watchlist_cap=15,
        headroom_threshold_percent=20.0
    )
    
    # 15% headroom < 20% threshold
    assert tracker.should_reduce_cap(15.0) is True
    
    # 25% headroom > 20% threshold
    assert tracker.should_reduce_cap(25.0) is False
    
    # Already at minimum cap - can't reduce further
    tracker.current_cap = 5
    assert tracker.should_reduce_cap(15.0) is False


# Test 7: Should increase cap when headroom improves
def test_should_increase_cap():
    """Test that cap increase triggers when headroom improves."""
    
    tracker = RateLimitTracker(
        min_watchlist_cap=5,
        max_watchlist_cap=15,
        headroom_threshold_percent=20.0
    )
    
    tracker.current_cap = 10  # Reduced from max
    
    # 60% headroom > 50% increase threshold (20% + 30% hysteresis)
    assert tracker.should_increase_cap(60.0) is True
    
    # 40% headroom < 50% increase threshold
    assert tracker.should_increase_cap(40.0) is False
    
    # Already at max - can't increase further
    tracker.current_cap = 15
    assert tracker.should_increase_cap(60.0) is False


# Test 8: Adjust cap reduction
def test_adjust_cap_reduction():
    """Test that cap is reduced when headroom is low."""
    
    tracker = RateLimitTracker(
        min_watchlist_cap=5,
        max_watchlist_cap=15,
        headroom_threshold_percent=20.0
    )
    
    # Start at max cap
    assert tracker.current_cap == 15
    
    # Create low headroom status
    status = RateLimitStatus(
        requests_limit=30,
        requests_remaining=3,  # 10% remaining
        tokens_limit=12000,
        tokens_remaining=10000
    )
    
    result = tracker.adjust_watchlist_cap(status)
    
    assert result['adjusted'] is True
    assert result['old_cap'] == 15
    assert result['new_cap'] == 12  # Reduced by 20% (3 SKUs)
    assert tracker.current_cap == 12
    assert "REDUCED" in result['reason']


# Test 9: Adjust cap increase
def test_adjust_cap_increase():
    """Test that cap increases gradually when headroom improves."""
    
    tracker = RateLimitTracker(
        min_watchlist_cap=5,
        max_watchlist_cap=15,
        headroom_threshold_percent=20.0
    )
    
    # Start with reduced cap
    tracker.current_cap = 10
    
    # Create healthy headroom status
    status = RateLimitStatus(
        requests_limit=30,
        requests_remaining=28,  # 93% remaining
        tokens_limit=12000,
        tokens_remaining=11000  # 92% remaining
    )
    
    result = tracker.adjust_watchlist_cap(status)
    
    assert result['adjusted'] is True
    assert result['old_cap'] == 10
    assert result['new_cap'] == 11  # Increased by 1 (conservative)
    assert tracker.current_cap == 11
    assert "INCREASED" in result['reason']


# Test 10: No adjustment when headroom moderate
def test_no_adjustment_moderate_headroom():
    """Test that cap stays unchanged when headroom is moderate."""
    
    tracker = RateLimitTracker(
        min_watchlist_cap=5,
        max_watchlist_cap=15,
        headroom_threshold_percent=20.0
    )
    
    # Moderate headroom (between 20% and 50%)
    status = RateLimitStatus(
        requests_limit=30,
        requests_remaining=12,  # 40% remaining
        tokens_limit=12000,
        tokens_remaining=5000  # 42% remaining
    )
    
    result = tracker.adjust_watchlist_cap(status)
    
    assert result['adjusted'] is False
    assert result['old_cap'] == 15
    assert result['new_cap'] == 15
    assert tracker.current_cap == 15


# Test 11: Cap cannot go below minimum
def test_cap_minimum_floor():
    """Test that cap never goes below configured minimum."""
    
    tracker = RateLimitTracker(
        min_watchlist_cap=5,
        max_watchlist_cap=15,
        headroom_threshold_percent=20.0
    )
    
    tracker.current_cap = 6
    
    # Very low headroom
    status = RateLimitStatus(
        requests_limit=30,
        requests_remaining=1,  # 3% remaining
        tokens_limit=12000,
        tokens_remaining=500
    )
    
    result = tracker.adjust_watchlist_cap(status)
    
    # Should reduce to minimum, not below
    assert result['new_cap'] == 5
    assert tracker.current_cap == 5


# Test 12: Cap cannot go above maximum
def test_cap_maximum_ceiling():
    """Test that cap never goes above configured maximum."""
    
    tracker = RateLimitTracker(
        min_watchlist_cap=5,
        max_watchlist_cap=15,
        headroom_threshold_percent=20.0
    )
    
    tracker.current_cap = 14
    
    # Perfect headroom
    status = RateLimitStatus(
        requests_limit=30,
        requests_remaining=30,  # 100% remaining
        tokens_limit=12000,
        tokens_remaining=12000
    )
    
    result = tracker.adjust_watchlist_cap(status)
    
    # Should increase to maximum, not above
    assert result['new_cap'] == 15
    assert tracker.current_cap == 15


# Test 13: Identify bottleneck - requests constrained
def test_bottleneck_requests():
    """Test bottleneck identification when requests are most constrained."""
    
    status = RateLimitStatus(
        requests_limit=30,
        requests_remaining=2,   # 93% used
        tokens_limit=12000,
        tokens_remaining=6000   # 50% used
    )
    
    assert status.bottleneck == "RPM"


# Test 14: Identify bottleneck - tokens constrained
def test_bottleneck_tokens():
    """Test bottleneck identification when tokens are most constrained."""
    
    status = RateLimitStatus(
        requests_limit=30,
        requests_remaining=20,   # 33% used
        tokens_limit=12000,
        tokens_remaining=1000    # 92% used
    )
    
    assert status.bottleneck == "TPM"


# Test 15: Get status summary
def test_get_status_summary():
    """Test getting current tracker status summary."""
    
    tracker = RateLimitTracker(
        min_watchlist_cap=5,
        max_watchlist_cap=15
    )
    
    # Reduce cap
    tracker.current_cap = 10
    tracker.reduction_count = 2
    
    status = RateLimitStatus(
        requests_limit=30,
        requests_remaining=15,
        tokens_limit=12000,
        tokens_remaining=8000
    )
    tracker.last_status = status
    
    summary = tracker.get_status_summary()
    
    assert summary['current_cap'] == 10
    assert summary['max_cap'] == 15
    assert summary['min_cap'] == 5
    assert summary['cap_reduced'] is True
    assert summary['reduction_count'] == 2
    assert summary['headroom_percent'] == 50.0  # Min of 50% requests, 67% tokens
    assert summary['bottleneck'] == "RPM"


# Test 16: Multiple reductions compound
def test_multiple_reductions():
    """Test that cap can be reduced multiple times."""
    
    tracker = RateLimitTracker(
        min_watchlist_cap=5,
        max_watchlist_cap=15,
        headroom_threshold_percent=20.0
    )
    
    assert tracker.current_cap == 15
    
    # First reduction
    status1 = RateLimitStatus(
        requests_limit=30,
        requests_remaining=3,  # 10% remaining
        tokens_limit=12000,
        tokens_remaining=10000
    )
    tracker.adjust_watchlist_cap(status1)
    assert tracker.current_cap == 12  # Reduced by 3
    
    # Second reduction
    status2 = RateLimitStatus(
        requests_limit=30,
        requests_remaining=2,  # 7% remaining
        tokens_limit=12000,
        tokens_remaining=10000
    )
    tracker.adjust_watchlist_cap(status2)
    assert tracker.current_cap == 10  # Reduced by 2 more
    
    assert tracker.reduction_count == 2


# Test 17: Update from API response object
def test_update_from_response():
    """Test updating tracker from API response object."""
    
    tracker = RateLimitTracker()
    
    # Mock response object
    mock_response = MagicMock()
    mock_response.headers = {
        "x-ratelimit-limit-requests": "30",
        "x-ratelimit-remaining-requests": "20",
        "x-ratelimit-limit-tokens": "12000",
        "x-ratelimit-remaining-tokens": "10000"
    }
    
    status = tracker.update_from_response(mock_response)
    
    assert status.requests_limit == 30
    assert status.requests_remaining == 20
    assert tracker.last_status == status


# Test 18: Graceful handling of missing headers
def test_missing_headers_graceful():
    """Test that tracker handles responses with no rate limit headers."""
    
    tracker = RateLimitTracker()
    
    # Response with no rate limit headers
    mock_response = MagicMock()
    mock_response.headers = {}
    
    status = tracker.update_from_response(mock_response)
    
    # Should not crash, all fields None
    assert status.requests_limit is None
    assert status.requests_remaining is None
    
    # Headroom should default to 100% (no constraints known)
    headroom = tracker.calculate_headroom_percent(status)
    assert headroom == 100.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
