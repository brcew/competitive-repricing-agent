"""
Unit tests for cost tracker.

These tests verify cost calculation and tracking WITHOUT making real API calls.
All costs are calculated from mocked token usage data.

Run with: pytest tests/test_cost_tracker.py -v
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from cost_tracker import (
    CostTracker,
    CostRecord,
    ModelPricing,
    GROQ_PRICING
)


# Test 1: Model pricing accuracy
def test_groq_pricing_tables():
    """Test that pricing tables match Groq's 2026 rates."""
    
    # Llama 3.1 8B Instant
    pricing_8b = GROQ_PRICING["llama-3.1-8b-instant"]
    assert pricing_8b.input_cost_per_million == 0.05
    assert pricing_8b.output_cost_per_million == 0.08
    
    # Llama 3.3 70B Versatile
    pricing_70b = GROQ_PRICING["llama-3.3-70b-versatile"]
    assert pricing_70b.input_cost_per_million == 0.59
    assert pricing_70b.output_cost_per_million == 0.79


# Test 2: Calculate cost for 8B model
def test_calculate_cost_8b_model():
    """Test cost calculation for Llama 3.1 8B."""
    
    pricing = GROQ_PRICING["llama-3.1-8b-instant"]
    
    # 1000 input + 500 output tokens
    cost = pricing.calculate_cost(1000, 500)
    
    # Expected: (1000/1M * 0.05) + (500/1M * 0.08)
    # = 0.00005 + 0.00004 = 0.00009
    assert cost == pytest.approx(0.00009, rel=1e-6)


# Test 3: Calculate cost for 70B model
def test_calculate_cost_70b_model():
    """Test cost calculation for Llama 3.3 70B."""
    
    pricing = GROQ_PRICING["llama-3.3-70b-versatile"]
    
    # 1000 input + 500 output tokens
    cost = pricing.calculate_cost(1000, 500)
    
    # Expected: (1000/1M * 0.59) + (500/1M * 0.79)
    # = 0.00059 + 0.000395 = 0.000985
    assert cost == pytest.approx(0.000985, rel=1e-6)


# Test 4: Calculate cost for larger call
def test_calculate_cost_large_call():
    """Test cost calculation for a large API call."""
    
    pricing = GROQ_PRICING["llama-3.3-70b-versatile"]
    
    # 100,000 input + 2,000 output tokens (from Groq docs example)
    cost = pricing.calculate_cost(100000, 2000)
    
    # Expected: (100000/1M * 0.59) + (2000/1M * 0.79)
    # = 0.059 + 0.00158 = 0.06058
    assert cost == pytest.approx(0.06058, rel=1e-4)


# Test 5: Tracker calculates call cost correctly
def test_tracker_calculate_call_cost():
    """Test that tracker correctly calculates and records cost."""
    
    tracker = CostTracker()
    
    record = tracker.calculate_call_cost(
        model_name="llama-3.1-8b-instant",
        input_tokens=1000,
        output_tokens=500,
        call_type="worker"
    )
    
    assert record.model_name == "llama-3.1-8b-instant"
    assert record.input_tokens == 1000
    assert record.output_tokens == 500
    assert record.total_tokens == 1500
    assert record.total_cost_usd == pytest.approx(0.00009, rel=1e-6)
    assert record.call_type == "worker"


# Test 6: Tracker updates session counters
def test_tracker_session_counters():
    """Test that tracker updates session counters."""
    
    tracker = CostTracker()
    
    assert tracker.calls_this_session == 0
    assert tracker.cost_this_session == 0.0
    
    # Make two calls
    tracker.calculate_call_cost("llama-3.1-8b-instant", 1000, 500, "worker")
    tracker.calculate_call_cost("llama-3.3-70b-versatile", 1000, 500, "orchestrator")
    
    assert tracker.calls_this_session == 2
    assert tracker.cost_this_session == pytest.approx(0.00009 + 0.000985, rel=1e-5)


# Test 7: Get model pricing with groq/ prefix
def test_get_model_pricing_with_prefix():
    """Test getting pricing when model name has groq/ prefix."""
    
    tracker = CostTracker()
    
    pricing = tracker.get_model_pricing("groq/llama-3.1-8b-instant")
    
    assert pricing.model_name == "llama-3.1-8b-instant"
    assert pricing.input_cost_per_million == 0.05


# Test 8: Get model pricing fallback for unknown model
def test_get_model_pricing_fallback():
    """Test fallback pricing for unknown models."""
    
    tracker = CostTracker()
    
    pricing = tracker.get_model_pricing("unknown-model-xyz")
    
    # Should fallback to 8B pricing
    assert pricing.input_cost_per_million == 0.05
    assert pricing.output_cost_per_million == 0.08


# Test 9: Get worker costs from database
def test_get_worker_costs_from_db():
    """Test retrieving worker costs from database."""
    
    tracker = CostTracker()
    
    # Mock database session and query
    with patch('cost_tracker.get_db_session') as mock_session:
        mock_db = MagicMock()
        mock_session.return_value.__enter__ = MagicMock(return_value=mock_db)
        mock_session.return_value.__exit__ = MagicMock(return_value=False)
        
        # Mock 3 pricing decisions
        mock_decisions = [
            MagicMock(
                tokens_used=150,
                model_used="llama-3.1-8b-instant",
                decided_at=datetime.utcnow()
            ),
            MagicMock(
                tokens_used=200,
                model_used="llama-3.1-8b-instant",
                decided_at=datetime.utcnow()
            ),
            MagicMock(
                tokens_used=100,
                model_used="llama-3.1-8b-instant",
                decided_at=datetime.utcnow()
            )
        ]
        
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value.all.return_value = mock_decisions
        
        costs = tracker.get_worker_costs_from_db()
    
    assert costs['call_count'] == 3
    assert costs['total_tokens'] == 450  # 150 + 200 + 100
    assert costs['avg_tokens_per_call'] == 150
    assert costs['total_cost_usd'] > 0  # Should have some cost


# Test 10: Get orchestrator costs from database
def test_get_orchestrator_costs_from_db():
    """Test retrieving orchestrator costs from database."""
    
    tracker = CostTracker()
    
    with patch('cost_tracker.get_db_session') as mock_session:
        mock_db = MagicMock()
        mock_session.return_value.__enter__ = MagicMock(return_value=mock_db)
        mock_session.return_value.__exit__ = MagicMock(return_value=False)
        
        # Mock 2 orchestrator runs
        mock_runs = [
            MagicMock(
                tokens_used=300,
                model_used="llama-3.3-70b-versatile",
                started_at=datetime.utcnow()
            ),
            MagicMock(
                tokens_used=350,
                model_used="llama-3.3-70b-versatile",
                started_at=datetime.utcnow()
            )
        ]
        
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value.all.return_value = mock_runs
        
        costs = tracker.get_orchestrator_costs_from_db()
    
    assert costs['call_count'] == 2
    assert costs['total_tokens'] == 650  # 300 + 350
    assert costs['avg_tokens_per_call'] == 325
    assert costs['total_cost_usd'] > 0


# Test 11: Get total costs combines worker + orchestrator
def test_get_total_costs():
    """Test that total costs combines both agents."""
    
    tracker = CostTracker()
    
    with patch.object(tracker, 'get_worker_costs_from_db') as mock_worker:
        with patch.object(tracker, 'get_orchestrator_costs_from_db') as mock_orchestrator:
            mock_worker.return_value = {
                'call_count': 10,
                'total_tokens': 1500,
                'total_cost_usd': 0.0015
            }
            
            mock_orchestrator.return_value = {
                'call_count': 2,
                'total_tokens': 600,
                'total_cost_usd': 0.0005
            }
            
            costs = tracker.get_total_costs_from_db()
    
    assert costs['total_calls'] == 12
    assert costs['total_tokens'] == 2100
    assert costs['total_cost_usd'] == 0.002
    assert costs['avg_tokens_per_call'] == pytest.approx(175, rel=0.1)


# Test 12: Empty database returns zero costs
def test_empty_database_returns_zero():
    """Test that empty database returns zero costs gracefully."""
    
    tracker = CostTracker()
    
    with patch('cost_tracker.get_db_session') as mock_session:
        mock_db = MagicMock()
        mock_session.return_value.__enter__ = MagicMock(return_value=mock_db)
        mock_session.return_value.__exit__ = MagicMock(return_value=False)
        
        # Empty results
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value.all.return_value = []
        
        costs = tracker.get_worker_costs_from_db()
    
    assert costs['call_count'] == 0
    assert costs['total_tokens'] == 0
    assert costs['total_cost_usd'] == 0.0
    assert costs['avg_tokens_per_call'] == 0


# Test 13: Estimate daily cost projection
def test_estimate_daily_cost():
    """Test daily cost estimation based on current usage."""
    
    tracker = CostTracker()
    
    # Mock total costs (simulating 1 hour of data)
    with patch.object(tracker, 'get_total_costs_from_db') as mock_total:
        mock_total.return_value = {
            'period_start': datetime.utcnow() - timedelta(hours=1),
            'period_end': datetime.utcnow(),
            'total_calls': 10,
            'total_cost_usd': 0.01  # $0.01 in 1 hour
        }
        
        estimate = tracker.estimate_daily_cost()
    
    # $0.01/hour * 24 hours = $0.24/day
    assert estimate['estimated_daily_cost_usd'] == pytest.approx(0.24, rel=0.01)
    assert estimate['estimated_daily_calls'] == pytest.approx(240, rel=0.05)  # Allow 5% tolerance


# Test 14: Budget status - healthy
def test_budget_status_healthy():
    """Test budget status when well under budget."""
    
    tracker = CostTracker()
    
    with patch.object(tracker, 'estimate_daily_cost') as mock_estimate:
        mock_estimate.return_value = {
            'estimated_daily_cost_usd': 0.25,  # $0.25/day
            'estimated_daily_calls': 250
        }
        
        status = tracker.check_budget_status(daily_budget_usd=1.0)
    
    assert status['status'] == "HEALTHY"
    assert status['budget_used_percent'] == 25.0
    assert status['budget_remaining_usd'] == 0.75


# Test 15: Budget status - warning
def test_budget_status_warning():
    """Test budget status when approaching budget."""
    
    tracker = CostTracker()
    
    with patch.object(tracker, 'estimate_daily_cost') as mock_estimate:
        mock_estimate.return_value = {
            'estimated_daily_cost_usd': 0.65,  # $0.65/day
            'estimated_daily_calls': 650
        }
        
        status = tracker.check_budget_status(daily_budget_usd=1.0)
    
    assert status['status'] == "WARNING"
    assert status['budget_used_percent'] == 65.0


# Test 16: Budget status - critical
def test_budget_status_critical():
    """Test budget status when very close to budget."""
    
    tracker = CostTracker()
    
    with patch.object(tracker, 'estimate_daily_cost') as mock_estimate:
        mock_estimate.return_value = {
            'estimated_daily_cost_usd': 0.90,  # $0.90/day
            'estimated_daily_calls': 900
        }
        
        status = tracker.check_budget_status(daily_budget_usd=1.0)
    
    assert status['status'] == "CRITICAL"
    assert status['budget_used_percent'] == 90.0


# Test 17: Budget status - over budget
def test_budget_status_over():
    """Test budget status when over budget."""
    
    tracker = CostTracker()
    
    with patch.object(tracker, 'estimate_daily_cost') as mock_estimate:
        mock_estimate.return_value = {
            'estimated_daily_cost_usd': 1.20,  # $1.20/day
            'estimated_daily_calls': 1200
        }
        
        status = tracker.check_budget_status(daily_budget_usd=1.0)
    
    assert status['status'] == "OVER_BUDGET"
    assert status['budget_used_percent'] == 120.0
    assert status['budget_remaining_usd'] == pytest.approx(-0.20, rel=0.01)


# Test 18: Session summary
def test_get_session_summary():
    """Test getting session summary."""
    
    tracker = CostTracker()
    
    # Make some calls
    tracker.calculate_call_cost("llama-3.1-8b-instant", 1000, 500, "worker")
    tracker.calculate_call_cost("llama-3.1-8b-instant", 1000, 500, "worker")
    
    summary = tracker.get_session_summary()
    
    assert summary['calls_this_session'] == 2
    assert summary['cost_this_session_usd'] == pytest.approx(0.00018, rel=1e-5)
    assert summary['avg_cost_per_call'] == pytest.approx(0.00009, rel=1e-5)


# Test 19: Cost comparison - 70B vs 8B
def test_cost_comparison_70b_vs_8b():
    """Test cost difference between 70B and 8B models."""
    
    pricing_8b = GROQ_PRICING["llama-3.1-8b-instant"]
    pricing_70b = GROQ_PRICING["llama-3.3-70b-versatile"]
    
    # Same token usage
    tokens_in = 1000
    tokens_out = 500
    
    cost_8b = pricing_8b.calculate_cost(tokens_in, tokens_out)
    cost_70b = pricing_70b.calculate_cost(tokens_in, tokens_out)
    
    # 70B should be ~10x more expensive
    ratio = cost_70b / cost_8b
    assert ratio == pytest.approx(10.94, rel=0.1)  # 0.000985 / 0.00009


# Test 20: Zero tokens edge case
def test_zero_tokens_cost():
    """Test cost calculation with zero tokens."""
    
    pricing = GROQ_PRICING["llama-3.1-8b-instant"]
    
    cost = pricing.calculate_cost(0, 0)
    
    assert cost == 0.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
