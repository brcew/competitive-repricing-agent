"""
Worker agent for individual SKU pricing decisions.

The worker agent:
- Uses llama-3.1-8b-instant (small, frequent model)
- Makes one of three decisions: MATCH, UNDERCUT_50, or HOLD
- Runs every 15 minutes per active watchlist SKU
- NEVER enforces margin floor itself (delegated to margin_check_tool)
- All decisions pass through deterministic margin safety check

This is the frequent, low-cost tier of the two-agent system.
"""

import os
os.environ['USE_LOCAL_CONFIG'] = '1'

import config
import config_local
config.settings = config_local.settings

from datetime import datetime
from typing import Dict, Any, Optional, Literal

import structlog
from openai import AsyncOpenAI

from db_utils import get_db_session
from models import SKU, PricingDecision
from competitor_price_simulator import get_competitor_price, fetch_and_store_price
from margin_check_tool import check_margin_safety, MarginCheckInput
from logging_config import log_pricing_decision, log_safety_violation

logger = structlog.get_logger(__name__)


class WorkerAgent:
    """
    Worker agent for individual SKU pricing decisions.
    
    Responsibilities:
    - Fetch current competitor price
    - Analyze our price vs competitor price
    - Propose one action: MATCH, UNDERCUT_50, or HOLD
    - Submit to margin safety check
    - Log decision with full audit trail
    """
    
    def __init__(self):
        """Initialize the worker agent."""
        self.client = AsyncOpenAI(
            api_key=config.settings.groq_api_key,
            base_url="https://api.groq.com/openai/v1",
        )
        
        self.model = config.settings.worker_model.replace("groq/", "")
        
        logger.info("Worker agent initialized", model=self.model)
    
    def _build_decision_prompt(
        self,
        sku: SKU,
        our_price: float,
        competitor_price: float,
        competitor_available: bool,
        current_margin_percent: float
    ) -> str:
        """Build the prompt for the worker agent."""
        
        gap_dollars = our_price - competitor_price
        gap_percent = (gap_dollars / our_price * 100) if our_price > 0 else 0
        
        prompt = f"""You are a pricing agent making a competitive pricing decision for a single SKU.

PRODUCT INFORMATION:
- SKU: {sku.sku}
- Product: {sku.product_name}
- Category: {sku.category}
- Our Current Price: ${our_price:.2f}
- Current Margin: {current_margin_percent:.1f}%

COMPETITOR INFORMATION:
- Competitor: Amazon
- Their Price: ${competitor_price:.2f}
- In Stock: {"Yes" if competitor_available else "No"}
- Price Gap: ${gap_dollars:+.2f} ({gap_percent:+.1f}%)
  {"(We're more expensive)" if gap_dollars > 0 else "(We're cheaper)" if gap_dollars < 0 else "(Same price)"}

YOUR TASK:
Decide ONE of the following actions:

1. MATCH - Match competitor's exact price (${competitor_price:.2f})
2. UNDERCUT_50 - Undercut competitor by $0.50 (${competitor_price - 0.50:.2f})
3. HOLD - Keep our current price (${our_price:.2f})

DECISION CRITERIA:
- If competitor is out of stock: Consider HOLD (we have supply advantage)
- If we're already cheaper: Consider HOLD (already competitive)
- If we're more expensive by >$5: Consider MATCH or UNDERCUT_50
- If difference is small (<$2): Consider HOLD (not worth changing)
- Balance competitiveness with maintaining healthy margins

IMPORTANT NOTES:
- You propose the action; margin safety will be checked automatically
- Do NOT calculate margins yourself; just propose what makes business sense
- Be concise and clear in your reasoning
- Focus on competitive positioning, not detailed margin math

Respond in this EXACT format:
DECISION: [MATCH|UNDERCUT_50|HOLD]
REASONING: [Brief 1-2 sentence explanation of your decision]"""
        
        return prompt
    
    async def make_pricing_decision(self, sku: SKU) -> Dict[str, Any]:
        """
        Make a pricing decision for a SKU.
        
        Args:
            sku: The SKU to make a decision for
        
        Returns:
            Dict with decision details including:
            - action: MATCH, UNDERCUT_50, or HOLD
            - new_price: Proposed new price (None if HOLD)
            - reasoning: LLM's explanation
            - margin_check_passed: Whether safety check passed
            - margin_check_reason: Safety check explanation
        """
        logger.info("Making pricing decision", sku=sku.sku)
        
        # 1. Fetch current competitor price
        try:
            comp_price_record = fetch_and_store_price(sku)
            competitor_price = comp_price_record.competitor_price
            competitor_available = comp_price_record.is_available
        except Exception as e:
            logger.error("Failed to fetch competitor price", sku=sku.sku, error=str(e))
            # Fall back to HOLD if we can't get competitor data
            return {
                "action": "HOLD",
                "new_price": None,
                "reasoning": f"Failed to fetch competitor price: {e}",
                "margin_check_passed": True,
                "margin_check_reason": "HOLD requires no margin check",
                "tokens_used": 0,
                "error": str(e)
            }
        
        # 2. Calculate current margin
        current_margin = ((sku.our_price - sku.cost) / sku.our_price * 100) if sku.our_price > 0 else 0
        
        # 3. Get LLM decision
        prompt = self._build_decision_prompt(
            sku,
            sku.our_price,
            competitor_price,
            competitor_available,
            current_margin
        )
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a pricing strategy agent. Respond concisely with DECISION and REASONING only."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=150,
                temperature=0.3  # Lower temperature for more consistent decisions
            )
            
            llm_response = response.choices[0].message.content
            tokens_used = response.usage.total_tokens if response.usage else 0
            
            logger.debug("LLM response received", sku=sku.sku, response=llm_response[:100])
            
        except Exception as e:
            logger.error("LLM call failed", sku=sku.sku, error=str(e))
            return {
                "action": "HOLD",
                "new_price": None,
                "reasoning": f"LLM call failed: {e}",
                "margin_check_passed": True,
                "margin_check_reason": "HOLD requires no margin check",
                "tokens_used": 0,
                "error": str(e)
            }
        
        # 4. Parse LLM response
        action, reasoning = self._parse_llm_response(llm_response)
        
        # 5. Calculate proposed new price
        if action == "MATCH":
            new_price = competitor_price
        elif action == "UNDERCUT_50":
            new_price = competitor_price - 0.50
        else:  # HOLD
            new_price = None
        
        # 6. Run margin safety check
        margin_input = MarginCheckInput(
            sku_id=sku.id,
            sku_code=sku.sku,
            our_current_price=sku.our_price,
            cost=sku.cost,
            competitor_price=competitor_price,
            proposed_action=action,
            proposed_new_price=new_price
        )
        
        margin_result = check_margin_safety(margin_input)
        
        # 7. If margin check failed, override to HOLD
        if not margin_result.passed:
            logger.warning(
                "Margin check failed, overriding to HOLD",
                sku=sku.sku,
                proposed_action=action,
                reason=margin_result.reason
            )
            
            # Log safety violation to audit trail
            log_safety_violation(
                event_type="margin_check_failure",
                sku_code=sku.sku,
                proposed_action=action,
                violation_reason=margin_result.reason,
                current_price=sku.our_price,
                proposed_price=new_price if new_price else sku.our_price,
                margin_percent=margin_result.proposed_margin_percent or current_margin,
                details={
                    "cost": sku.cost,
                    "competitor_price": competitor_price,
                    "current_margin": current_margin
                }
            )
            
            action = "HOLD"
            new_price = None
            reasoning = f"[OVERRIDDEN] Original: {reasoning}. Rejected: {margin_result.reason}"
        
        return {
            "action": action,
            "new_price": new_price,
            "reasoning": reasoning,
            "margin_check_passed": margin_result.passed,
            "margin_check_reason": margin_result.reason,
            "tokens_used": tokens_used,
            "competitor_price": competitor_price,
            "competitor_available": competitor_available,
            "current_margin": current_margin,
            "proposed_margin": margin_result.proposed_margin_percent,
        }
    
    def _parse_llm_response(self, response: str) -> tuple[Literal["MATCH", "UNDERCUT_50", "HOLD"], str]:
        """
        Parse LLM response to extract decision and reasoning.
        
        Args:
            response: Raw LLM response
        
        Returns:
            Tuple of (action, reasoning)
        """
        lines = response.strip().split('\n')
        
        action = "HOLD"  # Default fallback
        reasoning = "Unable to parse LLM response"
        
        for line in lines:
            line = line.strip()
            
            if line.startswith("DECISION:"):
                decision_text = line.replace("DECISION:", "").strip().upper()
                if "MATCH" in decision_text and "UNDERCUT" not in decision_text:
                    action = "MATCH"
                elif "UNDERCUT" in decision_text:
                    action = "UNDERCUT_50"
                elif "HOLD" in decision_text:
                    action = "HOLD"
            
            elif line.startswith("REASONING:"):
                reasoning = line.replace("REASONING:", "").strip()
        
        # If still default, try to find action anywhere in response
        if action == "HOLD" and reasoning == "Unable to parse LLM response":
            response_upper = response.upper()
            if "UNDERCUT" in response_upper:
                action = "UNDERCUT_50"
            elif "MATCH" in response_upper:
                action = "MATCH"
            
            reasoning = response.strip() if response.strip() else "No reasoning provided"
        
        return action, reasoning
    
    async def store_decision(
        self,
        sku: SKU,
        decision_data: Dict[str, Any]
    ) -> PricingDecision:
        """
        Store pricing decision in database.
        
        Args:
            sku: The SKU
            decision_data: Decision data from make_pricing_decision()
        
        Returns:
            PricingDecision record
        """
        with get_db_session() as session:
            pricing_decision = PricingDecision(
                sku_id=sku.id,
                our_price_at_decision=sku.our_price,
                competitor_price_at_decision=decision_data["competitor_price"],
                margin_floor=config.settings.margin_floor_percent,
                action=decision_data["action"],
                new_price=decision_data["new_price"],
                reasoning=decision_data["reasoning"],
                margin_check_passed=decision_data["margin_check_passed"],
                margin_check_reason=decision_data["margin_check_reason"],
                executed=False,  # Not actually changing price in this demo
                model_used=self.model,
                tokens_used=decision_data["tokens_used"]
            )
            
            session.add(pricing_decision)
            session.commit()
            
            decision_id = pricing_decision.id
        
        logger.info(
            "Decision stored",
            sku=sku.sku,
            decision_id=decision_id,
            action=decision_data["action"],
            new_price=decision_data["new_price"]
        )
        
        # Log to audit trail for analysis
        log_pricing_decision(
            sku_id=sku.id,
            sku_code=sku.sku,
            action=decision_data["action"],
            old_price=sku.our_price,
            new_price=decision_data["new_price"] if decision_data["new_price"] else sku.our_price,
            competitor_price=decision_data["competitor_price"],
            margin_check_passed=decision_data["margin_check_passed"],
            reasoning=decision_data["reasoning"],
            worker_tokens=decision_data["tokens_used"],
            decision_id=decision_id
        )
        
        return pricing_decision
    
    async def process_sku(self, sku: SKU) -> Dict[str, Any]:
        """
        Complete workflow: decide and store.
        
        Args:
            sku: SKU to process
        
        Returns:
            Decision data
        """
        decision_data = await self.make_pricing_decision(sku)
        await self.store_decision(sku, decision_data)
        return decision_data
    
    async def process_sku_by_id(self, sku_id: int) -> Dict[str, Any]:
        """
        Complete workflow: load SKU by ID, decide, and store.
        
        Args:
            sku_id: ID of SKU to process
        
        Returns:
            Decision data
        """
        from db_utils import get_db_session
        
        # Load SKU in a fresh session
        with get_db_session() as session:
            sku = session.query(SKU).filter(SKU.id == sku_id).first()
            if not sku:
                raise ValueError(f"SKU with id {sku_id} not found")
            
            # Extract data we need before session closes
            sku_data = {
                'id': sku.id,
                'sku': sku.sku,
                'product_name': sku.product_name,
                'our_price': float(sku.our_price),
                'cost': float(sku.cost),
                'margin_percent': float(sku.margin_percent)
            }
        
        # Create a mock SKU object for processing
        mock_sku = type('SKU', (), sku_data)()
        
        decision_data = await self.make_pricing_decision(mock_sku)
        
        # Store decision with actual SKU ID
        with get_db_session() as session:
            sku = session.query(SKU).filter(SKU.id == sku_id).first()
            await self.store_decision(sku, decision_data)
        
        return decision_data


# Global agent instance
_agent = None


async def get_worker_agent() -> WorkerAgent:
    """Get or create the global worker agent instance."""
    global _agent
    if _agent is None:
        _agent = WorkerAgent()
    return _agent