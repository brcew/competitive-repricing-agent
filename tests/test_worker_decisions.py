"""
Unit tests for worker agent decision logic with mocked LLM responses.

These tests run without real API calls for deterministic CI/CD.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock config before importing
os.environ['USE_LOCAL_CONFIG'] = '1'

from worker_agent import WorkerAgent
from models import SKU


class TestLLMResponseParsing:
    """Test parsing of LLM responses."""
    
    def setup_method(self):
        """Setup test agent."""
        with patch('worker_agent.AsyncOpenAI'):
            self.agent = WorkerAgent()
    
    def test_parse_match_decision(self):
        """Test parsing MATCH decision."""
        response = """DECISION: MATCH
REASONING: Competitor is $10 cheaper, we should match to stay competitive."""
        
        action, reasoning = self.agent._parse_llm_response(response)
        
        assert action == "MATCH"
        assert "competitive" in reasoning.lower()
    
    def test_parse_undercut_decision(self):
        """Test parsing UNDERCUT_50 decision."""
        response = """DECISION: UNDERCUT_50
REASONING: We can gain market share by undercutting slightly."""
        
        action, reasoning = self.agent._parse_llm_response(response)
        
        assert action == "UNDERCUT_50"
        assert "undercut" in reasoning.lower()
    
    def test_parse_hold_decision(self):
        """Test parsing HOLD decision."""
        response = """DECISION: HOLD
REASONING: We're already cheaper than competitor, no action needed."""
        
        action, reasoning = self.agent._parse_llm_response(response)
        
        assert action == "HOLD"
        assert "cheaper" in reasoning.lower()
    
    def test_parse_malformed_response_defaults_to_hold(self):
        """Test that malformed response defaults to HOLD."""
        response = """Some random text without proper format"""
        
        action, reasoning = self.agent._parse_llm_response(response)
        
        assert action == "HOLD"
    
    def test_parse_case_insensitive(self):
        """Test parsing is case-insensitive."""
        response = """decision: match
reasoning: Price match needed"""
        
        action, reasoning = self.agent._parse_llm_response(response)
        
        assert action == "MATCH"


class TestPromptBuilding:
    """Test decision prompt construction."""
    
    def setup_method(self):
        """Setup test agent."""
        with patch('worker_agent.AsyncOpenAI'):
            self.agent = WorkerAgent()
    
    def test_prompt_contains_key_information(self):
        """Test prompt includes all necessary information."""
        sku = SKU(
            id=1,
            sku="TEST-001",
            product_name="Test Product",
            category="Electronics",
            our_price=100.0,
            cost=60.0,
            margin_percent=40.0
        )
        
        prompt = self.agent._build_decision_prompt(
            sku=sku,
            our_price=100.0,
            competitor_price=90.0,
            competitor_available=True,
            current_margin_percent=40.0
        )
        
        # Check all key information is present
        assert "TEST-001" in prompt
        assert "Test Product" in prompt
        assert "$100.00" in prompt
        assert "$90.00" in prompt
        assert "40.0%" in prompt
        assert "MATCH" in prompt
        assert "UNDERCUT_50" in prompt
        assert "HOLD" in prompt
    
    def test_prompt_shows_gap_correctly(self):
        """Test prompt calculates and shows price gap."""
        sku = SKU(
            id=1,
            sku="TEST-001",
            product_name="Test Product",
            category="Electronics",
            our_price=110.0,
            cost=60.0,
            margin_percent=45.5
        )
        
        prompt = self.agent._build_decision_prompt(
            sku=sku,
            our_price=110.0,
            competitor_price=100.0,
            competitor_available=True,
            current_margin_percent=45.5
        )
        
        assert "+$10.00" in prompt or "$+10.00" in prompt or "$10.00" in prompt
        assert "expensive" in prompt.lower()


class TestDecisionFlow:
    """Test complete decision flow with mocks."""
    
    @pytest.mark.asyncio
    async def test_match_decision_flow(self):
        """Test MATCH decision flow."""
        # Create mock SKU
        sku = SKU(
            id=1,
            sku="TEST-001",
            product_name="Test Product",
            category="Electronics",
            our_price=100.0,
            cost=60.0,
            margin_percent=40.0
        )
        
        # Mock LLM response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = """DECISION: MATCH
REASONING: Competitor is cheaper, we should match."""
        mock_response.usage = Mock()
        mock_response.usage.total_tokens = 100
        
        # Mock client and dependencies
        with patch('worker_agent.AsyncOpenAI') as mock_client_class, \
             patch('worker_agent.fetch_and_store_price') as mock_fetch, \
             patch('worker_agent.check_margin_safety') as mock_margin:
            
            # Setup mocks
            mock_client = AsyncMock()
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client
            
            mock_comp_price = Mock()
            mock_comp_price.competitor_price = 90.0
            mock_comp_price.is_available = True
            mock_fetch.return_value = mock_comp_price
            
            mock_margin_result = Mock()
            mock_margin_result.passed = True
            mock_margin_result.proposed_margin_percent = 33.3
            mock_margin_result.reason = "Approved"
            mock_margin.return_value = mock_margin_result
            
            # Create agent and make decision
            agent = WorkerAgent()
            decision = await agent.make_pricing_decision(sku)
            
            # Verify decision
            assert decision['action'] == "MATCH"
            assert decision['new_price'] == 90.0
            assert decision['margin_check_passed'] is True
            assert decision['tokens_used'] == 100
    
    @pytest.mark.asyncio
    async def test_margin_check_rejection_overrides_to_hold(self):
        """Test that failed margin check overrides action to HOLD."""
        sku = SKU(
            id=1,
            sku="TEST-001",
            product_name="Test Product",
            category="Electronics",
            our_price=100.0,
            cost=90.0,  # High cost = low margin
            margin_percent=10.0
        )
        
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = """DECISION: MATCH
REASONING: Let's match competitor price."""
        mock_response.usage = Mock()
        mock_response.usage.total_tokens = 100
        
        with patch('worker_agent.AsyncOpenAI') as mock_client_class, \
             patch('worker_agent.fetch_and_store_price') as mock_fetch, \
             patch('worker_agent.check_margin_safety') as mock_margin:
            
            mock_client = AsyncMock()
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client
            
            mock_comp_price = Mock()
            mock_comp_price.competitor_price = 85.0
            mock_comp_price.is_available = True
            mock_fetch.return_value = mock_comp_price
            
            # Margin check FAILS
            mock_margin_result = Mock()
            mock_margin_result.passed = False
            mock_margin_result.proposed_margin_percent = 5.9
            mock_margin_result.reason = "REJECTED: Margin 5.9% < floor 12.0%"
            mock_margin.return_value = mock_margin_result
            
            agent = WorkerAgent()
            decision = await agent.make_pricing_decision(sku)
            
            # Decision should be overridden to HOLD
            assert decision['action'] == "HOLD"
            assert decision['new_price'] is None
            assert decision['margin_check_passed'] is False
            assert "OVERRIDDEN" in decision['reasoning']
    
    @pytest.mark.asyncio
    async def test_undercut_decision_flow(self):
        """Test UNDERCUT_50 decision flow."""
        sku = SKU(
            id=1,
            sku="TEST-001",
            product_name="Test Product",
            category="Electronics",
            our_price=100.0,
            cost=50.0,
            margin_percent=50.0
        )
        
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = """DECISION: UNDERCUT_50
REASONING: We have good margins, can afford to undercut for market share."""
        mock_response.usage = Mock()
        mock_response.usage.total_tokens = 120
        
        with patch('worker_agent.AsyncOpenAI') as mock_client_class, \
             patch('worker_agent.fetch_and_store_price') as mock_fetch, \
             patch('worker_agent.check_margin_safety') as mock_margin:
            
            mock_client = AsyncMock()
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client
            
            mock_comp_price = Mock()
            mock_comp_price.competitor_price = 95.0
            mock_comp_price.is_available = True
            mock_fetch.return_value = mock_comp_price
            
            mock_margin_result = Mock()
            mock_margin_result.passed = True
            mock_margin_result.proposed_margin_percent = 47.1
            mock_margin_result.reason = "Approved"
            mock_margin.return_value = mock_margin_result
            
            agent = WorkerAgent()
            decision = await agent.make_pricing_decision(sku)
            
            assert decision['action'] == "UNDERCUT_50"
            assert decision['new_price'] == 94.50  # 95.0 - 0.50
            assert decision['margin_check_passed'] is True


class TestErrorHandling:
    """Test error handling in worker agent."""
    
    @pytest.mark.asyncio
    async def test_competitor_price_fetch_failure_returns_hold(self):
        """Test that fetch failure results in HOLD."""
        sku = SKU(
            id=1,
            sku="TEST-001",
            product_name="Test Product",
            category="Electronics",
            our_price=100.0,
            cost=60.0,
            margin_percent=40.0
        )
        
        with patch('worker_agent.AsyncOpenAI'), \
             patch('worker_agent.fetch_and_store_price') as mock_fetch:
            
            # Simulate fetch failure
            mock_fetch.side_effect = Exception("Network error")
            
            agent = WorkerAgent()
            decision = await agent.make_pricing_decision(sku)
            
            # Should fall back to HOLD
            assert decision['action'] == "HOLD"
            assert "Failed to fetch" in decision['reasoning']
            assert 'error' in decision
    
    @pytest.mark.asyncio
    async def test_llm_call_failure_returns_hold(self):
        """Test that LLM failure results in HOLD."""
        sku = SKU(
            id=1,
            sku="TEST-001",
            product_name="Test Product",
            category="Electronics",
            our_price=100.0,
            cost=60.0,
            margin_percent=40.0
        )
        
        with patch('worker_agent.AsyncOpenAI') as mock_client_class, \
             patch('worker_agent.fetch_and_store_price') as mock_fetch:
            
            mock_client = AsyncMock()
            mock_client.chat.completions.create = AsyncMock(
                side_effect=Exception("API error")
            )
            mock_client_class.return_value = mock_client
            
            mock_comp_price = Mock()
            mock_comp_price.competitor_price = 90.0
            mock_comp_price.is_available = True
            mock_fetch.return_value = mock_comp_price
            
            agent = WorkerAgent()
            decision = await agent.make_pricing_decision(sku)
            
            assert decision['action'] == "HOLD"
            assert "LLM call failed" in decision['reasoning']