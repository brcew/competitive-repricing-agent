"""
Main entry point for the competitive pricing multi-agent system.

This module coordinates:
- Orchestrator agent (runs hourly, manages watchlist)
- Worker agents (run every 15 minutes per watchlist SKU)
- Budget monitoring (stops before hitting API limits)
- Cost tracking (monitors spend)
- Rate limiting (adapts to API constraints)

Architecture:
1. Orchestrator runs every hour to update watchlist
2. Workers run every 15 minutes for each watchlist SKU
3. All operations respect budget guard and rate limits
4. Full audit trail stored in database

Run with: python main.py
"""

import os
os.environ['USE_LOCAL_CONFIG'] = '1'

import config
import config_local
config.settings = config_local.settings

# Initialize structured logging first
import logging_config

import asyncio
import signal
import sys
from datetime import datetime, timedelta, timezone
from typing import Dict, Any

import structlog

from db_utils import get_db_session
from models import SKU, Watchlist
from worker_agent import get_worker_agent
from orchestrator_agent import get_orchestrator_agent
from budget_guard import get_budget_guard, can_make_call, record_call
from cost_tracker import get_cost_tracker
from rate_limit_tracker import get_rate_limit_tracker
from logging_config import log_system_cycle

logger = structlog.get_logger(__name__)


class CompetitivePricingSystem:
    """
    Main system coordinator for competitive pricing agents.
    
    Responsibilities:
    - Schedule and run orchestrator agent (hourly)
    - Schedule and run worker agents (every 15 min per SKU)
    - Monitor budget and gracefully degrade if needed
    - Track costs and rate limits
    - Handle shutdown signals
    """
    
    def __init__(self):
        """Initialize the competitive pricing system."""
        self.running = False
        
        # Get intervals from config (convert seconds to minutes for internal use)
        self.worker_interval_minutes = config.settings.effective_worker_interval / 60
        self.orchestrator_interval_minutes = config.settings.effective_orchestrator_interval / 60
        
        # Component initialization
        self.budget_guard = get_budget_guard()
        self.cost_tracker = get_cost_tracker()
        self.rate_tracker = get_rate_limit_tracker()
        
        # State tracking
        self.last_orchestrator_run = None
        self.last_worker_run = {}  # sku_id -> datetime
        self.total_cycles = 0
        self.orchestrator_runs = 0
        self.worker_runs = 0
        
        # Log mode and intervals
        mode = "DEMO MODE" if config.settings.demo_mode else "PRODUCTION MODE"
        logger.info(
            f"Competitive pricing system initialized - {mode}",
            worker_interval=f"{self.worker_interval_minutes:.1f}min",
            orchestrator_interval=f"{self.orchestrator_interval_minutes:.1f}min",
            demo_mode=config.settings.demo_mode
        )
    
    async def run_orchestrator_cycle(self) -> Dict[str, Any]:
        """
        Run one orchestrator cycle.
        
        Returns:
            Dict with cycle results
        """
        logger.info("=" * 70)
        logger.info("ORCHESTRATOR CYCLE STARTING")
        logger.info("=" * 70)
        
        # Check budget
        allowed, reason = can_make_call()
        if not allowed:
            logger.error(
                "Orchestrator cycle skipped - budget exhausted",
                reason=reason
            )
            return {
                "success": False,
                "reason": "budget_exhausted",
                "message": reason
            }
        
        try:
            # Get orchestrator agent
            orchestrator = await get_orchestrator_agent()
            
            # Run full orchestration cycle
            result = await orchestrator.run_orchestration_cycle()
            
            # Update state
            self.last_orchestrator_run = datetime.now(timezone.utc)
            self.orchestrator_runs += 1
            
            logger.info(
                "Orchestrator cycle completed",
                run_id=result.get('run_id'),
                added=result['execution']['added'],
                removed=result['execution']['removed'],
                duration=f"{result['duration_seconds']:.2f}s"
            )
            
            return {
                "success": True,
                "result": result
            }
            
        except Exception as e:
            logger.error(
                "Orchestrator cycle failed",
                error=str(e),
                exc_info=True
            )
            return {
                "success": False,
                "reason": "error",
                "error": str(e)
            }
    
    async def run_worker_cycle(self) -> Dict[str, Any]:
        """
        Run one worker cycle for all active watchlist SKUs.
        
        Returns:
            Dict with cycle results
        """
        logger.info("=" * 70)
        logger.info("WORKER CYCLE STARTING")
        logger.info("=" * 70)
        
        # Get active watchlist SKUs
        with get_db_session() as session:
            watchlist_entries = session.query(Watchlist, SKU)\
                .join(SKU)\
                .filter(Watchlist.is_active == True)\
                .all()
            
            # Extract data we need before session closes
            active_skus = []
            for entry, sku in watchlist_entries:
                sku_data = {
                    'id': sku.id,
                    'sku': sku.sku,
                    'product_name': sku.product_name,
                    'our_price': float(sku.our_price),
                    'cost': float(sku.cost),
                    'margin_percent': float(sku.margin_percent)
                }
                active_skus.append(sku_data)
        
        if not active_skus:
            logger.warning("No SKUs on active watchlist")
            return {
                "success": True,
                "skus_processed": 0,
                "message": "No active SKUs"
            }
        
        logger.info(f"Processing {len(active_skus)} watchlist SKUs")
        
        # Get worker agent
        worker = await get_worker_agent()
        
        # Process each SKU
        results = []
        skipped = 0
        
        for sku_data in active_skus:
            # Check if this SKU needs processing
            last_run = self.last_worker_run.get(sku_data['id'])
            if last_run:
                time_since_last = (datetime.now(timezone.utc) - last_run).total_seconds() / 60
                if time_since_last < self.worker_interval_minutes:
                    logger.debug(
                        "Skipping SKU - processed recently",
                        sku=sku_data['sku'],
                        minutes_ago=f"{time_since_last:.1f}"
                    )
                    skipped += 1
                    continue
            
            # Check budget before processing
            allowed, reason = can_make_call()
            if not allowed:
                logger.warning(
                    "Worker cycle paused - budget exhausted",
                    reason=reason,
                    processed=len(results),
                    remaining=len(active_skus) - len(results) - skipped
                )
                break
            
            # Process SKU
            try:
                logger.info(f"Processing SKU: {sku_data['sku']}")
                
                # Create a mock SKU object with the data worker needs
                # Worker agent will load from database using sku_id
                decision = await worker.process_sku_by_id(sku_data['id'])
                
                # Update state
                self.last_worker_run[sku_data['id']] = datetime.now(timezone.utc)
                self.worker_runs += 1
                
                results.append({
                    "sku_id": sku_data['id'],
                    "sku_code": sku_data['sku'],
                    "action": decision.get('action'),
                    "new_price": decision.get('new_price'),
                    "margin_check_passed": decision.get('margin_check_passed'),
                    "success": True
                })
                
                logger.info(
                    "SKU processed",
                    sku=sku_data['sku'],
                    action=decision.get('action'),
                    new_price=decision.get('new_price')
                )
                
            except Exception as e:
                logger.error(
                    "Failed to process SKU",
                    sku=sku_data['sku'],
                    error=str(e)
                )
                results.append({
                    "sku_id": sku_data['id'],
                    "sku_code": sku_data['sku'],
                    "success": False,
                    "error": str(e)
                })
        
        logger.info(
            "Worker cycle completed",
            processed=len(results),
            skipped=skipped,
            total_watchlist=len(active_skus)
        )
        
        return {
            "success": True,
            "skus_processed": len(results),
            "skus_skipped": skipped,
            "total_watchlist": len(active_skus),
            "results": results
        }
    
    async def run_main_loop(self):
        """
        Main execution loop.
        
        Runs continuously, coordinating orchestrator and worker cycles.
        """
        mode = "DEMO MODE" if config.settings.demo_mode else "PRODUCTION MODE"
        logger.info("=" * 70)
        logger.info(f"COMPETITIVE PRICING SYSTEM STARTED - {mode}")
        logger.info("=" * 70)
        logger.info(f"Worker interval: {self.worker_interval_minutes:.1f} minutes")
        logger.info(f"Orchestrator interval: {self.orchestrator_interval_minutes:.1f} minutes")
        if config.settings.demo_mode:
            logger.info("⚡ DEMO MODE ENABLED - Using compressed timing for rapid testing")
        logger.info("=" * 70)
        
        self.running = True
        
        # Run initial orchestrator cycle to set up watchlist
        logger.info("Running initial orchestrator cycle...")
        await self.run_orchestrator_cycle()
        
        while self.running:
            try:
                self.total_cycles += 1
                
                logger.info(f"\n{'=' * 70}")
                logger.info(f"CYCLE #{self.total_cycles}")
                logger.info(f"{'=' * 70}")
                
                # Check if orchestrator should run
                orchestrator_due = (
                    self.last_orchestrator_run is None
                    or (datetime.now(timezone.utc) - self.last_orchestrator_run).total_seconds() / 60
                        >= self.orchestrator_interval_minutes
                )
                
                if orchestrator_due:
                    await self.run_orchestrator_cycle()
                
                # Run worker cycle
                await self.run_worker_cycle()
                
                # Log system status
                self._log_system_status()
                
                # Wait before next cycle
                logger.info(f"Sleeping {self.worker_interval_minutes} minutes until next cycle...")
                await asyncio.sleep(self.worker_interval_minutes * 60)
                
            except asyncio.CancelledError:
                logger.info("Main loop cancelled, shutting down...")
                break
            except Exception as e:
                logger.error(
                    "Error in main loop",
                    error=str(e),
                    exc_info=True
                )
                # Continue running despite errors
                await asyncio.sleep(60)  # Wait 1 minute before retrying
    
    def _log_system_status(self):
        """Log current system status."""
        # Budget status
        budget_status = self.budget_guard.get_status_summary()
        
        # Cost status
        cost_session = self.cost_tracker.get_session_summary()
        
        # Rate limit status
        rate_status = self.rate_tracker.get_status_summary()
        
        logger.info("=" * 70)
        logger.info("SYSTEM STATUS")
        logger.info("=" * 70)
        logger.info(f"Total cycles: {self.total_cycles}")
        logger.info(f"Orchestrator runs: {self.orchestrator_runs}")
        logger.info(f"Worker runs: {self.worker_runs}")
        logger.info(f"")
        logger.info(f"Budget Status: {budget_status['status']}")
        logger.info(f"  Daily: {budget_status['daily']['calls']}/{budget_status['daily']['limit']} "
                   f"({budget_status['daily']['usage_percent']:.1f}%)")
        logger.info(f"  Minute: {budget_status['minute']['calls']}/{budget_status['minute']['limit']}")
        logger.info(f"")
        logger.info(f"Session Costs:")
        logger.info(f"  Calls: {cost_session['calls_this_session']}")
        logger.info(f"  Cost: ${cost_session['cost_this_session_usd']:.6f}")
        logger.info(f"")
        logger.info(f"Rate Limits:")
        logger.info(f"  Current cap: {rate_status['current_cap']}/{rate_status['max_cap']}")
        logger.info(f"  Headroom: {rate_status['headroom_percent']:.1f}%")
        if rate_status['bottleneck']:
            logger.info(f"  Bottleneck: {rate_status['bottleneck']}")
        logger.info("=" * 70)
        
        # Structured audit log for programmatic analysis
        log_system_cycle(
            cycle_number=self.total_cycles,
            orchestrator_runs=self.orchestrator_runs,
            worker_runs=self.worker_runs,
            total_calls=cost_session['calls_this_session'],
            session_cost=cost_session['cost_this_session_usd'],
            budget_status=budget_status['status'],
            rate_limit_cap=rate_status['current_cap']
        )
    
    async def shutdown(self):
        """Gracefully shutdown the system."""
        logger.info("=" * 70)
        logger.info("SHUTTING DOWN COMPETITIVE PRICING SYSTEM")
        logger.info("=" * 70)
        
        self.running = False
        
        # Log final stats
        self._log_system_status()
        
        logger.info("Shutdown complete")


# Global system instance
_system = None


async def get_system() -> CompetitivePricingSystem:
    """Get or create the global system instance."""
    global _system
    if _system is None:
        _system = CompetitivePricingSystem()
    return _system


async def main():
    """Main entry point."""
    system = await get_system()
    
    # Set up signal handlers for graceful shutdown
    def signal_handler(sig, frame):
        logger.info(f"Received signal {sig}, initiating shutdown...")
        asyncio.create_task(system.shutdown())
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        await system.run_main_loop()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    finally:
        await system.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
