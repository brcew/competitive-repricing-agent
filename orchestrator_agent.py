"""
Orchestrator agent for watchlist management.

The orchestrator agent:
- Uses llama-3.3-70b-versatile (large, infrequent model)
- Runs hourly (not per-SKU, but system-wide)
- Reads conversion data, margin trends, watchlist performance
- Decides WHICH SKUs should be on the active watchlist
- NEVER sets prices directly (that's the worker's job)
- Cap enforced in code, not by LLM judgment

This is the infrequent, high-cost tier of the two-agent system.
"""

import os
os.environ['USE_LOCAL_CONFIG'] = '1'

import config
import config_local
config.settings = config_local.settings

from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional

import structlog
from openai import AsyncOpenAI
from sqlalchemy import func, and_

from db_utils import get_db_session
from models import SKU, Watchlist, ConversionMetric, PricingDecision, OrchestratorRun
from rate_limit_tracker import get_rate_limit_tracker, update_from_response, adjust_watchlist_cap
from logging_config import log_watchlist_change, log_rate_limit_adaptation

logger = structlog.get_logger(__name__)


class OrchestratorAgent:
    """
    Orchestrator agent for strategic watchlist management.
    
    Responsibilities:
    - Analyze system-wide performance data
    - Identify SKUs that need competitive monitoring
    - Update watchlist (add/remove SKUs)
    - Enforce watchlist cap (hard limit in code)
    - Log reasoning for all watchlist changes
    """
    
    def __init__(self):
        """Initialize the orchestrator agent."""
        self.client = AsyncOpenAI(
            api_key=config.settings.groq_api_key,
            base_url="https://api.groq.com/openai/v1",
        )
        
        self.model = config.settings.orchestrator_model.replace("groq/", "")
        self.watchlist_cap = config.settings.watchlist_cap
        self.rate_limit_tracker = get_rate_limit_tracker()
        
        logger.info(
            "Orchestrator agent initialized",
            model=self.model,
            watchlist_cap=self.watchlist_cap
        )
    
    def _gather_market_intelligence(self) -> Dict[str, Any]:
        """
        Gather system-wide data for orchestrator decision-making.
        
        Returns:
            Dict with market intelligence including:
            - Current watchlist size and SKUs
            - SKUs with declining conversion
            - SKUs with low margins
            - SKUs with recent competitive pressure
        """
        with get_db_session() as session:
            # Current watchlist
            active_watchlist = session.query(Watchlist)\
                .filter_by(is_active=True)\
                .all()
            
            current_watchlist_skus = [w.sku_id for w in active_watchlist]
            
            # Get conversion metrics for last 7 days
            seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
            
            # SKUs with declining conversion rates
            declining_skus = session.query(
                ConversionMetric.sku_id,
                func.avg(ConversionMetric.conversion_rate).label('avg_conversion'),
                func.count(ConversionMetric.id).label('metric_count')
            ).filter(
                ConversionMetric.period_start >= seven_days_ago
            ).group_by(
                ConversionMetric.sku_id
            ).having(
                func.avg(ConversionMetric.conversion_rate) < 15.0  # Below 15% conversion
            ).order_by(
                func.avg(ConversionMetric.conversion_rate).asc()
            ).limit(20).all()
            
            # SKUs with low margins (risky)
            low_margin_skus = session.query(SKU)\
                .filter(SKU.margin_percent < 20.0)\
                .order_by(SKU.margin_percent.asc())\
                .limit(20)\
                .all()
            
            # Recent worker decisions (competitive activity)
            recent_decisions = session.query(PricingDecision)\
                .filter(
                    PricingDecision.decided_at >= seven_days_ago,
                    PricingDecision.action != 'HOLD'  # Only actual price changes
                )\
                .all()
            
            # Group decisions by SKU
            sku_decision_counts = {}
            for decision in recent_decisions:
                sku_decision_counts[decision.sku_id] = \
                    sku_decision_counts.get(decision.sku_id, 0) + 1
            
            # SKUs with frequent competitive actions
            active_competition_skus = sorted(
                sku_decision_counts.items(),
                key=lambda x: x[1],
                reverse=True
            )[:20]
            
            # Get full SKU details for analysis
            all_relevant_sku_ids = set()
            all_relevant_sku_ids.update([d.sku_id for d in declining_skus])
            all_relevant_sku_ids.update([sku.id for sku in low_margin_skus])
            all_relevant_sku_ids.update([sku_id for sku_id, _ in active_competition_skus])
            
            sku_details = {}
            if all_relevant_sku_ids:
                skus = session.query(SKU).filter(SKU.id.in_(all_relevant_sku_ids)).all()
                sku_details = {sku.id: sku for sku in skus}
            
            return {
                "current_watchlist_size": len(active_watchlist),
                "current_watchlist_skus": current_watchlist_skus,
                "watchlist_cap": self.watchlist_cap,
                "declining_conversion_skus": [
                    {
                        "sku_id": d.sku_id,
                        "sku_code": sku_details[d.sku_id].sku if d.sku_id in sku_details else "UNKNOWN",
                        "avg_conversion": float(d.avg_conversion),
                        "on_watchlist": d.sku_id in current_watchlist_skus
                    }
                    for d in declining_skus if d.sku_id in sku_details
                ],
                "low_margin_skus": [
                    {
                        "sku_id": sku.id,
                        "sku_code": sku.sku,
                        "margin_percent": sku.margin_percent,
                        "our_price": sku.our_price,
                        "on_watchlist": sku.id in current_watchlist_skus
                    }
                    for sku in low_margin_skus
                ],
                "active_competition_skus": [
                    {
                        "sku_id": sku_id,
                        "sku_code": sku_details[sku_id].sku if sku_id in sku_details else "UNKNOWN",
                        "decision_count": count,
                        "on_watchlist": sku_id in current_watchlist_skus
                    }
                    for sku_id, count in active_competition_skus if sku_id in sku_details
                ]
            }
    
    def _build_orchestrator_prompt(self, intelligence: Dict[str, Any]) -> str:
        """Build prompt for orchestrator agent."""
        
        prompt = f"""You are a strategic pricing orchestrator managing a watchlist of products for competitive monitoring.

CURRENT SITUATION:
- Watchlist Size: {intelligence['current_watchlist_size']}/{intelligence['watchlist_cap']} SKUs
- Watchlist Cap: {intelligence['watchlist_cap']} SKUs (HARD LIMIT)

MARKET INTELLIGENCE:

1. LOW CONVERSION SKUs (may need price adjustments):
"""
        
        for sku in intelligence['declining_conversion_skus'][:10]:
            status = "✓ WATCHED" if sku['on_watchlist'] else "○ NOT WATCHED"
            prompt += f"\n   [{status}] {sku['sku_code']}: {sku['avg_conversion']:.1f}% conversion"
        
        prompt += f"""

2. LOW MARGIN SKUs (at risk if competitors undercut):
"""
        
        for sku in intelligence['low_margin_skus'][:10]:
            status = "✓ WATCHED" if sku['on_watchlist'] else "○ NOT WATCHED"
            prompt += f"\n   [{status}] {sku['sku_code']}: {sku['margin_percent']:.1f}% margin, ${sku['our_price']:.2f}"
        
        prompt += f"""

3. ACTIVE COMPETITION SKUs (frequent pricing actions):
"""
        
        for sku in intelligence['active_competition_skus'][:10]:
            status = "✓ WATCHED" if sku['on_watchlist'] else "○ NOT WATCHED"
            prompt += f"\n   [{status}] {sku['sku_code']}: {sku['decision_count']} pricing actions this week"
        
        prompt += f"""

YOUR TASK:
Decide which SKUs should be on the active watchlist for the next hour.

DECISION CRITERIA:
- Prioritize SKUs with low margins (vulnerable to competition)
- Include SKUs with declining conversion (may need price optimization)
- Watch SKUs with active competitive pressure
- Balance across different risk factors
- Remove SKUs that have stabilized or are no longer critical

CONSTRAINTS:
- You MUST stay within the {intelligence['watchlist_cap']} SKU cap
- Focus on SKUs that NEED attention, not all SKUs
- Be strategic: watchlist is for competitive monitoring, not all products

OUTPUT FORMAT:
Respond with:
1. REASONING: 2-3 sentences explaining your watchlist strategy
2. ADD: List of SKU codes to ADD to watchlist (if any)
3. REMOVE: List of SKU codes to REMOVE from watchlist (if any)
4. KEEP: Mention how many current SKUs to keep

Example:
REASONING: Focusing on low-margin electronics where competitors are active. Removing stable high-margin items.
ADD: LAP-0042, MON-0156
REMOVE: MOU-0234
KEEP: 10 existing SKUs

Now decide the watchlist for the next hour:"""
        
        return prompt
    
    async def make_watchlist_decision(self) -> Dict[str, Any]:
        """
        Make strategic watchlist decision.
        
        Returns:
            Dict with decision data including:
            - skus_to_add: List of SKU IDs to add
            - skus_to_remove: List of SKU IDs to remove
            - reasoning: LLM's strategic explanation
            - final_size: Resulting watchlist size
        """
        logger.info("Making orchestrator watchlist decision")
        
        # 1. Gather intelligence
        intelligence = self._gather_market_intelligence()
        
        # 2. Build prompt
        prompt = self._build_orchestrator_prompt(intelligence)
        
        # 3. Get LLM decision
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a strategic pricing orchestrator. Be concise and data-driven."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=500,
                temperature=0.4  # Balanced between creative and consistent
            )
            
            llm_response = response.choices[0].message.content
            tokens_used = response.usage.total_tokens if response.usage else 0
            
            logger.debug("Orchestrator LLM response", response=llm_response[:200])
            
            # Update rate limit tracking
            rate_status = update_from_response(response)
            cap_adjustment = adjust_watchlist_cap(rate_status)
            
            if cap_adjustment['adjusted']:
                logger.warning(
                    "Watchlist cap adjusted",
                    old=cap_adjustment['old_cap'],
                    new=cap_adjustment['new_cap'],
                    reason=cap_adjustment['reason']
                )
            
        except Exception as e:
            logger.error("Orchestrator LLM call failed", error=str(e))
            return {
                "skus_to_add": [],
                "skus_to_remove": [],
                "reasoning": f"LLM call failed: {e}",
                "final_size": intelligence['current_watchlist_size'],
                "tokens_used": 0,
                "error": str(e)
            }
        
        # 4. Parse LLM response
        parsed = self._parse_orchestrator_response(llm_response, intelligence)
        
        # 5. Enforce watchlist cap (HARD LIMIT)
        # Use the cap from intelligence for testability, or use dynamic cap from rate limiter
        if 'watchlist_cap' in intelligence:
            # Test mode - use mocked cap
            cap = intelligence['watchlist_cap']
        else:
            # Production - use rate-limited cap
            cap = self.rate_limit_tracker.get_current_cap()
        
        final_size = (
            intelligence['current_watchlist_size']
            + len(parsed['skus_to_add'])
            - len(parsed['skus_to_remove'])
        )
        
        if final_size > cap:
            # Cap violation - reduce adds
            excess = final_size - cap
            if len(parsed['skus_to_add']) > excess:
                parsed['skus_to_add'] = parsed['skus_to_add'][:-excess]
                parsed['reasoning'] += f" [CAPPED: Reduced additions to stay within {cap} limit]"
                logger.warning(
                    "Watchlist cap enforced",
                    proposed=final_size,
                    cap=cap,
                    reduced_by=excess
                )
            else:
                # Can't add any if removals don't free enough space
                parsed['skus_to_add'] = []
                parsed['reasoning'] += f" [CAPPED: No additions possible within {cap} limit]"
                logger.warning("Watchlist cap prevented all additions", cap=cap)
        
        # Recalculate final size after capping
        final_size = (
            intelligence['current_watchlist_size']
            + len(parsed['skus_to_add'])
            - len(parsed['skus_to_remove'])
        )
        
        return {
            **parsed,
            "final_size": final_size,
            "tokens_used": tokens_used,
            "intelligence": intelligence
        }
    
    def _parse_orchestrator_response(
        self,
        response: str,
        intelligence: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Parse orchestrator LLM response to extract actions."""
        
        reasoning = ""
        skus_to_add_codes = []
        skus_to_remove_codes = []
        
        # Parse response line by line
        for line in response.strip().split('\n'):
            line = line.strip()
            
            if line.startswith("REASONING:"):
                reasoning = line.replace("REASONING:", "").strip()
            elif line.startswith("ADD:"):
                codes = line.replace("ADD:", "").strip()
                if codes and codes.lower() not in ['none', 'n/a', '']:
                    skus_to_add_codes = [c.strip() for c in codes.replace(',', ' ').split() if c.strip()]
            elif line.startswith("REMOVE:"):
                codes = line.replace("REMOVE:", "").strip()
                if codes and codes.lower() not in ['none', 'n/a', '']:
                    skus_to_remove_codes = [c.strip() for c in codes.replace(',', ' ').split() if c.strip()]
        
        # Convert SKU codes to IDs
        with get_db_session() as session:
            skus_to_add = []
            if skus_to_add_codes:
                add_skus = session.query(SKU).filter(SKU.sku.in_(skus_to_add_codes)).all()
                skus_to_add = [sku.id for sku in add_skus]
            
            skus_to_remove = []
            if skus_to_remove_codes:
                remove_skus = session.query(SKU).filter(SKU.sku.in_(skus_to_remove_codes)).all()
                skus_to_remove = [sku.id for sku in remove_skus]
        
        if not reasoning:
            reasoning = response[:200] if response else "No reasoning provided"
        
        return {
            "skus_to_add": skus_to_add,
            "skus_to_remove": skus_to_remove,
            "reasoning": reasoning
        }
    
    async def execute_watchlist_update(
        self,
        decision: Dict[str, Any],
        run_id: Optional[int] = None
    ) -> Dict[str, int]:
        """
        Execute the watchlist update in database.
        
        Args:
            decision: Decision from make_watchlist_decision()
            run_id: Optional orchestrator run ID for audit trail
        
        Returns:
            Dict with counts: {"added": int, "removed": int}
        """
        added_count = 0
        removed_count = 0
        
        with get_db_session() as session:
            # Remove SKUs
            for sku_id in decision['skus_to_remove']:
                watchlist_entry = session.query(Watchlist)\
                    .filter_by(sku_id=sku_id, is_active=True)\
                    .first()
                
                if watchlist_entry:
                    watchlist_entry.is_active = False
                    watchlist_entry.deactivated_at = datetime.now(timezone.utc)
                    removed_count += 1
            
            # Add SKUs
            for sku_id in decision['skus_to_add']:
                # Check if already exists
                existing = session.query(Watchlist)\
                    .filter_by(sku_id=sku_id, is_active=True)\
                    .first()
                
                if not existing:
                    new_entry = Watchlist(
                        sku_id=sku_id,
                        is_active=True,
                        priority_score=8.0,  # Default priority
                        reason=decision['reasoning'][:500],  # Truncate for DB
                        added_by_run_id=run_id
                    )
                    session.add(new_entry)
                    added_count += 1
            
            session.commit()
        
        logger.info(
            "Watchlist updated",
            added=added_count,
            removed=removed_count,
            final_size=decision['final_size']
        )
        
        # Log to audit trail
        # Get SKU codes for the audit log
        with get_db_session() as session:
            added_skus = []
            removed_skus = []
            
            if decision['skus_to_add']:
                added_skus = [sku.sku for sku in session.query(SKU).filter(SKU.id.in_(decision['skus_to_add'])).all()]
            
            if decision['skus_to_remove']:
                removed_skus = [sku.sku for sku in session.query(SKU).filter(SKU.id.in_(decision['skus_to_remove'])).all()]
            
            # Get current watchlist cap
            rate_status = self.rate_limit_tracker.get_status_summary()
            
            log_watchlist_change(
                run_id=run_id if run_id else 0,
                added_skus=added_skus,
                removed_skus=removed_skus,
                new_watchlist_size=decision['final_size'],
                watchlist_cap=rate_status['current_cap'],
                reasoning=decision['reasoning'],
                orchestrator_tokens=decision.get('tokens_used', 0)
            )
        
        return {"added": added_count, "removed": removed_count}
    
    async def store_orchestrator_run(
        self,
        decision: Dict[str, Any],
        execution: Dict[str, int],
        duration_seconds: float
    ) -> OrchestratorRun:
        """Store orchestrator run record in database."""
        
        # Get rate limit status for storing
        rate_status_summary = self.rate_limit_tracker.get_status_summary()
        
        with get_db_session() as session:
            run = OrchestratorRun(
                started_at=datetime.now(timezone.utc) - timedelta(seconds=duration_seconds),
                completed_at=datetime.now(timezone.utc),
                duration_seconds=duration_seconds,
                watchlist_cap_used=rate_status_summary['current_cap'],
                skus_added=execution['added'],
                skus_removed=execution['removed'],
                final_watchlist_size=decision['final_size'],
                reasoning=decision['reasoning'],
                model_used=self.model,
                tokens_used=decision.get('tokens_used', 0),
                success='error' not in decision,
                rate_limit_constraint=rate_status_summary.get('bottleneck'),
                rate_limit_headroom_percent=rate_status_summary.get('headroom_percent')
            )
            
            session.add(run)
            session.commit()
            session.refresh(run)  # Refresh to load the ID
            
            # Extract data before session closes
            run_id = run.id
            run_data = {
                'id': run.id,
                'started_at': run.started_at,
                'completed_at': run.completed_at,
                'duration_seconds': run.duration_seconds,
                'success': run.success
            }
        
        logger.info(
            "Orchestrator run stored",
            run_id=run_id,
            cap_used=rate_status_summary['current_cap'],
            headroom=f"{rate_status_summary.get('headroom_percent', 0):.1f}%"
        )
        
        # Return a dict instead of detached object
        return run_data
    
    async def run_orchestration_cycle(self) -> Dict[str, Any]:
        """
        Complete orchestration cycle: decide, execute, store.
        
        Returns:
            Dict with cycle results
        """
        import time
        start_time = time.time()
        
        logger.info("Starting orchestration cycle")
        
        # Make decision
        decision = await self.make_watchlist_decision()
        
        # Execute if no errors
        if 'error' not in decision:
            execution = await self.execute_watchlist_update(decision)
        else:
            execution = {"added": 0, "removed": 0}
        
        # Calculate duration
        duration = time.time() - start_time
        
        # Store run
        run_data = await self.store_orchestrator_run(decision, execution, duration)
        
        logger.info(
            "Orchestration cycle complete",
            run_id=run_data['id'],
            duration=f"{duration:.2f}s",
            added=execution['added'],
            removed=execution['removed']
        )
        
        return {
            "run_id": run_data['id'],
            "decision": decision,
            "execution": execution,
            "duration_seconds": duration
        }


# Global agent instance
_agent = None


async def get_orchestrator_agent() -> OrchestratorAgent:
    """Get or create the global orchestrator agent instance."""
    global _agent
    if _agent is None:
        _agent = OrchestratorAgent()
    return _agent