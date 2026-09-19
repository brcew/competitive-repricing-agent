"""
Demo launcher for competitive pricing system.

This script runs the system in DEMO_MODE with compressed timing:
- Worker runs every 15 seconds (vs 15 minutes in production)
- Orchestrator runs every 1 minute (vs 60 minutes in production)

This enables rapid testing and demonstration without waiting for production intervals.

Usage:
    python run_demo.py
"""

import os

# Force DEMO_MODE before importing config
os.environ['DEMO_MODE'] = 'true'
os.environ['USE_LOCAL_CONFIG'] = '1'

import asyncio
import sys
from datetime import datetime

import structlog

logger = structlog.get_logger(__name__)


async def main():
    """Run the system in demo mode."""
    logger.info("=" * 70)
    logger.info("🚀 LAUNCHING COMPETITIVE PRICING SYSTEM IN DEMO MODE")
    logger.info("=" * 70)
    logger.info("Demo mode features:")
    logger.info("  • Worker interval: 15 seconds (vs 15 min production)")
    logger.info("  • Orchestrator interval: 1 minute (vs 60 min production)")
    logger.info("  • All safety checks still active (margin floor, budget guard)")
    logger.info("  • Full audit trail in database")
    logger.info("")
    logger.info("⚠️  This is for testing/demo only - uses compressed timing")
    logger.info("=" * 70)
    logger.info("")
    
    # Import main system (after env vars are set)
    from main import main as run_system
    
    try:
        await run_system()
    except KeyboardInterrupt:
        logger.info("\n⏹️  Demo stopped by user")
    except Exception as e:
        logger.error(f"Demo error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("DEMO MODE - Competitive Pricing System")
    print("=" * 70)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("Press Ctrl+C to stop")
    print("=" * 70 + "\n")
    
    asyncio.run(main())
