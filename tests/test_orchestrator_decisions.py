"""
Unit tests for orchestrator agent logic with mocked LLM responses.

These tests verify orchestrator decision-making WITHOUT making real API calls.
All LLM responses are mocked to ensure tests are fast, free, and deterministic.

Run with: pytest tests/test_orchestrator_decisions.py -v
"""

import os
os.environ['USE_LOCAL_CONFIG'] = '1'

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import config
import config_local
config.settings = config_local.settings

from orchestrator_agent import OrchestratorAgent
from models import SKU, Watchlist, ConversionMetric, PricingDecision


@pytest.fixture
def mock_intelligence():
    """Mock market intelligence data."""
    return {
        "current_watchlist_size": 30,
        "current_watchlist_skus": [1, 2, 3, 4, 5],
        "watchlist_cap": 50,
        "declining_conversion_skus": [
            {
                "sku_id": 10,
                "sku_code": "LAP-0042",
                "avg_conversion": 8.5,
                "on_watchlist": False
            },
            {
                "sku_id": 11,
                "sku_code": "MON-0156",
                "avg_conversion": 9.2,
                "on_watchlist": False
            }
        ],
        "low_margin_skus": [
            {
                "sku_id": 20,
                "sku_code": "TAB-0089",
                "margin_percent": 15.5,
                "our_price": 399.99,
                "on_watchlist": False
            },
            {
                "sku_id": 21,
                "sku_code": "PHO-0234",
                "margin_percent": 16.8,
                "our_price": 799.99,
                "on_watchlist": True
            }
        ],
        "active_competition_skus": [
            {
                "sku_id": 30,
                "sku_code": "CAM-0067",
                "decision_count": 5,
                "on_watchlist": True
            },
            {
                "sku_id": 31,
                "sku_code": "HEA-0198",
                "decision_count": 3,
                "on_watchlist": False
            }
        ]
    }


@pytest.fixture
def agent():
    """Create orchestrator agent instance."""
    return OrchestratorAgent()


# Test 1: Parse valid LLM response with adds and removes
@pytest.mark.asyncio
async def test_parse_valid_llm_response(agent, mock_intelligence):
    """Test parsing a well-formed LLM response."""
    
    llm_response = """REASONING: Focusing on low-margin electronics where competitors are active. Removing stable high-margin items.
ADD: LAP-0042, MON-0156, TAB-0089
REMOVE: MOU-0234, KEY-0156
KEEP: 28 existing SKUs"""
    
    # Create mock SKUs in database
    with patch('orchestrator_agent.get_db_session') as mock_session:
        mock_db = MagicMock()
        mock_session.return_value.__enter__ = MagicMock(return_value=mock_db)
        mock_session.return_value.__exit__ = MagicMock(return_value=False)
        
        # Mock query for SKUs to add
        add_query_result = [
            MagicMock(id=10, sku="LAP-0042"),
            MagicMock(id=11, sku="MON-0156"),
            MagicMock(id=20, sku="TAB-0089"),
        ]
        
        # Mock query for SKUs to remove
        remove_query_result = [
            MagicMock(id=50, sku="MOU-0234"),
            MagicMock(id=51, sku="KEY-0156"),
        ]
        
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        
        # Set up filter to return different results based on input
        def filter_side_effect(*args, **kwargs):
            filter_mock = MagicMock()
            # Check if this is the add query or remove query based on call count
            if hasattr(filter_side_effect, 'call_count'):
                filter_side_effect.call_count += 1
            else:
                filter_side_effect.call_count = 1
            
            if filter_side_effect.call_count == 1:
                filter_mock.all.return_value = add_query_result
            else:
                filter_mock.all.return_value = remove_query_result
            return filter_mock
        
        mock_query.filter.side_effect = filter_side_effect
        
        # Parse response
        result = agent._parse_orchestrator_response(llm_response, mock_intelligence)
    
    # Verify parsing
    assert result['reasoning'].startswith("Focusing on low-margin electronics")
    assert len(result['skus_to_add']) == 3
    assert len(result['skus_to_remove']) == 2
    assert 10 in result['skus_to_add']
    assert 11 in result['skus_to_add']
    assert 20 in result['skus_to_add']


# Test 2: Parse LLM response with no changes
@pytest.mark.asyncio
async def test_parse_no_changes_response(agent, mock_intelligence):
    """Test parsing response when no changes are needed."""
    
    llm_response = """REASONING: Current watchlist is well-balanced. No changes needed.
ADD: None
REMOVE: None
KEEP: 30 existing SKUs"""
    
    with patch('orchestrator_agent.get_db_session') as mock_session:
        mock_db = MagicMock()
        mock_session.return_value.__enter__ = MagicMock(return_value=mock_db)
        mock_session.return_value.__exit__ = MagicMock(return_value=False)
        
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value.all.return_value = []
        
        result = agent._parse_orchestrator_response(llm_response, mock_intelligence)
    
    assert result['reasoning'].startswith("Current watchlist is well-balanced")
    assert len(result['skus_to_add']) == 0
    assert len(result['skus_to_remove']) == 0


# Test 3: Watchlist cap enforcement - reduces adds
@pytest.mark.asyncio
async def test_watchlist_cap_reduces_adds(agent):
    """Test that cap enforcement reduces additions when necessary."""
    
    # Mock LLM response that would exceed cap
    mock_llm_response = """REASONING: Adding many high-priority SKUs.
ADD: LAP-0042, MON-0156, TAB-0089, PHO-0234, CAM-0067, HEA-0198
REMOVE: None
KEEP: 48 existing SKUs"""
    
    # Mock current state: 48 SKUs, cap is 50, trying to add 6 (would be 54)
    mock_intelligence = {
        "current_watchlist_size": 48,
        "watchlist_cap": 50,
        "current_watchlist_skus": list(range(1, 49)),
        "declining_conversion_skus": [],
        "low_margin_skus": [],
        "active_competition_skus": []
    }
    
    with patch.object(agent, '_gather_market_intelligence', return_value=mock_intelligence):
        with patch.object(agent, '_build_orchestrator_prompt', return_value="mock prompt"):
            with patch.object(agent.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
                # Mock LLM response
                mock_response = MagicMock()
                mock_response.choices = [MagicMock(message=MagicMock(content=mock_llm_response))]
                mock_response.usage = MagicMock(total_tokens=300)
                mock_create.return_value = mock_response
                
                # Mock database queries
                with patch('orchestrator_agent.get_db_session') as mock_session:
                    mock_db = MagicMock()
                    mock_session.return_value.__enter__ = MagicMock(return_value=mock_db)
                    mock_session.return_value.__exit__ = MagicMock(return_value=False)
                    
                    # Mock 6 SKUs found for adding
                    mock_skus = [MagicMock(id=i) for i in range(10, 16)]
                    mock_query = MagicMock()
                    mock_db.query.return_value = mock_query
                    mock_query.filter.return_value.all.return_value = mock_skus
                    
                    # Make decision
                    decision = await agent.make_watchlist_decision()
    
    # Should reduce from 6 adds to 2 (48 + 2 = 50 = cap)
    assert len(decision['skus_to_add']) == 2
    assert decision['final_size'] == 50
    assert "[CAPPED:" in decision['reasoning']


# Test 4: Watchlist cap enforcement - blocks all adds
@pytest.mark.asyncio
async def test_watchlist_cap_blocks_all_adds(agent):
    """Test that cap blocks all additions when at capacity."""
    
    mock_llm_response = """REASONING: Adding critical SKUs.
ADD: LAP-0042, MON-0156
REMOVE: None
KEEP: 50 existing SKUs"""
    
    # Already at cap
    mock_intelligence = {
        "current_watchlist_size": 50,
        "watchlist_cap": 50,
        "current_watchlist_skus": list(range(1, 51)),
        "declining_conversion_skus": [],
        "low_margin_skus": [],
        "active_competition_skus": []
    }
    
    with patch.object(agent, '_gather_market_intelligence', return_value=mock_intelligence):
        with patch.object(agent, '_build_orchestrator_prompt', return_value="mock prompt"):
            with patch.object(agent.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
                mock_response = MagicMock()
                mock_response.choices = [MagicMock(message=MagicMock(content=mock_llm_response))]
                mock_response.usage = MagicMock(total_tokens=300)
                mock_create.return_value = mock_response
                
                with patch('orchestrator_agent.get_db_session') as mock_session:
                    mock_db = MagicMock()
                    mock_session.return_value.__enter__ = MagicMock(return_value=mock_db)
                    mock_session.return_value.__exit__ = MagicMock(return_value=False)
                    
                    mock_skus = [MagicMock(id=10), MagicMock(id=11)]
                    mock_query = MagicMock()
                    mock_db.query.return_value = mock_query
                    mock_query.filter.return_value.all.return_value = mock_skus
                    
                    decision = await agent.make_watchlist_decision()
    
    # No additions allowed
    assert len(decision['skus_to_add']) == 0
    assert decision['final_size'] == 50
    assert "No additions possible" in decision['reasoning']


# Test 5: Watchlist cap allows adds when removals create space
@pytest.mark.asyncio
async def test_watchlist_cap_allows_adds_with_removals(agent):
    """Test that removals create space for additions."""
    
    mock_llm_response = """REASONING: Swapping out stable SKUs for critical ones.
ADD: LAP-0042, MON-0156, TAB-0089
REMOVE: OLD-001, OLD-002, OLD-003, OLD-004
KEEP: 46 existing SKUs"""
    
    # At 49, removing 4, adding 3 = 48 (under cap)
    mock_intelligence = {
        "current_watchlist_size": 49,
        "watchlist_cap": 50,
        "current_watchlist_skus": list(range(1, 50)),
        "declining_conversion_skus": [],
        "low_margin_skus": [],
        "active_competition_skus": []
    }
    
    with patch.object(agent, '_gather_market_intelligence', return_value=mock_intelligence):
        with patch.object(agent, '_build_orchestrator_prompt', return_value="mock prompt"):
            with patch.object(agent.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
                mock_response = MagicMock()
                mock_response.choices = [MagicMock(message=MagicMock(content=mock_llm_response))]
                mock_response.usage = MagicMock(total_tokens=350)
                mock_create.return_value = mock_response
                
                with patch('orchestrator_agent.get_db_session') as mock_session:
                    mock_db = MagicMock()
                    mock_session.return_value.__enter__ = MagicMock(return_value=mock_db)
                    mock_session.return_value.__exit__ = MagicMock(return_value=False)
                    
                    def query_side_effect(*args):
                        mock_query = MagicMock()
                        if hasattr(query_side_effect, 'call_count'):
                            query_side_effect.call_count += 1
                        else:
                            query_side_effect.call_count = 1
                        
                        if query_side_effect.call_count == 1:
                            # First call: SKUs to add
                            mock_query.filter.return_value.all.return_value = [
                                MagicMock(id=10), MagicMock(id=11), MagicMock(id=12)
                            ]
                        else:
                            # Second call: SKUs to remove
                            mock_query.filter.return_value.all.return_value = [
                                MagicMock(id=100), MagicMock(id=101), 
                                MagicMock(id=102), MagicMock(id=103)
                            ]
                        return mock_query
                    
                    mock_db.query.side_effect = query_side_effect
                    
                    decision = await agent.make_watchlist_decision()
    
    # All 3 additions allowed (49 - 4 + 3 = 48)
    assert len(decision['skus_to_add']) == 3
    assert len(decision['skus_to_remove']) == 4
    assert decision['final_size'] == 48
    assert "[CAPPED:" not in decision['reasoning']


# Test 6: LLM call failure handling
@pytest.mark.asyncio
async def test_llm_call_failure_handling(agent):
    """Test graceful handling when LLM call fails."""
    
    mock_intelligence = {
        "current_watchlist_size": 30,
        "watchlist_cap": 50,
        "current_watchlist_skus": [],
        "declining_conversion_skus": [],
        "low_margin_skus": [],
        "active_competition_skus": []
    }
    
    with patch.object(agent, '_gather_market_intelligence', return_value=mock_intelligence):
        with patch.object(agent, '_build_orchestrator_prompt', return_value="mock prompt"):
            with patch.object(agent.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
                # Simulate API failure
                mock_create.side_effect = Exception("API connection failed")
                
                decision = await agent.make_watchlist_decision()
    
    # Should return safe defaults
    assert 'error' in decision
    assert len(decision['skus_to_add']) == 0
    assert len(decision['skus_to_remove']) == 0
    assert decision['final_size'] == 30  # Unchanged
    assert decision['tokens_used'] == 0


# Test 7: Verify prompt includes all intelligence sections
def test_build_orchestrator_prompt(agent, mock_intelligence):
    """Test that prompt includes all key market intelligence."""
    
    prompt = agent._build_orchestrator_prompt(mock_intelligence)
    
    # Check all sections present
    assert "CURRENT SITUATION" in prompt
    assert "Watchlist Size: 30/50" in prompt
    assert "LOW CONVERSION SKUs" in prompt
    assert "LOW MARGIN SKUs" in prompt
    assert "ACTIVE COMPETITION SKUs" in prompt
    assert "OUTPUT FORMAT" in prompt
    
    # Check specific SKUs mentioned
    assert "LAP-0042" in prompt
    assert "MON-0156" in prompt
    assert "TAB-0089" in prompt


# Test 8: Complete decision cycle (integration-like but mocked)
@pytest.mark.asyncio
async def test_complete_decision_cycle(agent):
    """Test complete decision flow from intelligence to final decision."""
    
    mock_llm_response = """REASONING: Adding low-margin SKUs with competitive pressure.
ADD: LAP-0042, TAB-0089
REMOVE: OLD-999
KEEP: 29 existing SKUs"""
    
    mock_intelligence = {
        "current_watchlist_size": 30,
        "watchlist_cap": 50,
        "current_watchlist_skus": [1, 2, 3],
        "declining_conversion_skus": [{"sku_id": 10, "sku_code": "LAP-0042", "avg_conversion": 8.5, "on_watchlist": False}],
        "low_margin_skus": [{"sku_id": 20, "sku_code": "TAB-0089", "margin_percent": 15.5, "our_price": 399.99, "on_watchlist": False}],
        "active_competition_skus": []
    }
    
    with patch.object(agent, '_gather_market_intelligence', return_value=mock_intelligence):
        with patch.object(agent, '_build_orchestrator_prompt', return_value="mock prompt"):
            with patch.object(agent.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
                mock_response = MagicMock()
                mock_response.choices = [MagicMock(message=MagicMock(content=mock_llm_response))]
                mock_response.usage = MagicMock(total_tokens=280)
                mock_create.return_value = mock_response
                
                with patch('orchestrator_agent.get_db_session') as mock_session:
                    mock_db = MagicMock()
                    mock_session.return_value.__enter__ = MagicMock(return_value=mock_db)
                    mock_session.return_value.__exit__ = MagicMock(return_value=False)
                    
                    def query_side_effect(*args):
                        mock_query = MagicMock()
                        if not hasattr(query_side_effect, 'call_count'):
                            query_side_effect.call_count = 0
                        query_side_effect.call_count += 1
                        
                        if query_side_effect.call_count == 1:
                            mock_query.filter.return_value.all.return_value = [
                                MagicMock(id=10), MagicMock(id=20)
                            ]
                        else:
                            mock_query.filter.return_value.all.return_value = [
                                MagicMock(id=999)
                            ]
                        return mock_query
                    
                    mock_db.query.side_effect = query_side_effect
                    
                    decision = await agent.make_watchlist_decision()
    
    # Verify complete decision
    assert 'error' not in decision
    assert len(decision['skus_to_add']) == 2
    assert len(decision['skus_to_remove']) == 1
    assert decision['final_size'] == 31  # 30 - 1 + 2
    assert decision['tokens_used'] == 280
    assert "low-margin" in decision['reasoning'].lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
