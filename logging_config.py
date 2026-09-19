"""
Structured logging configuration for the competitive pricing system.

This module sets up structlog with:
- JSON formatting for production (machine-readable)
- Console formatting for development (human-readable)
- Timestamp inclusion
- Log level filtering
- Exception formatting
- Context preservation across async boundaries

All logs include structured data that can be:
- Searched/filtered in log aggregation systems
- Parsed programmatically
- Analyzed for system behavior
- Used for audit trails
"""

import logging
import sys
from typing import Any, Dict

import structlog
from structlog.types import Processor

from config import settings


def configure_logging():
    """
    Configure structured logging for the application.
    
    This sets up:
    1. Processors to add timestamps, format exceptions, etc.
    2. Renderer (JSON for production, console for dev)
    3. Log level filtering based on config
    4. Integration with standard library logging
    """
    
    # Determine if we should use JSON (production) or console (dev) rendering
    use_json = settings.structured_logs
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)
    
    # Standard processors for all configurations
    shared_processors: list[Processor] = [
        # Add log level to event dict
        structlog.stdlib.add_log_level,
        # Add timestamp
        structlog.processors.TimeStamper(fmt="iso"),
        # Add logger name
        structlog.stdlib.add_logger_name,
        # Format exceptions nicely
        structlog.processors.format_exc_info,
        # Add stack info if available
        structlog.processors.StackInfoRenderer(),
        # Convert positional args to a string
        structlog.processors.UnicodeDecoder(),
    ]
    
    # Choose renderer based on configuration
    if use_json:
        # Production: JSON output for log aggregation systems
        renderer = structlog.processors.JSONRenderer()
    else:
        # Development: Human-readable console output with colors
        renderer = structlog.dev.ConsoleRenderer(
            colors=True,
            exception_formatter=structlog.dev.plain_traceback
        )
    
    # Configure structlog
    structlog.configure(
        processors=shared_processors + [
            # Filter by log level
            structlog.stdlib.filter_by_level,
            # Final rendering
            renderer,
        ],
        # Context class for async-safe context management
        context_class=dict,
        # Logger factory
        logger_factory=structlog.stdlib.LoggerFactory(),
        # Cache logger instances
        cache_logger_on_first_use=True,
    )
    
    # Configure standard library logging (for libraries that use it)
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )
    
    # Create initial logger to confirm setup
    logger = structlog.get_logger(__name__)
    logger.info(
        "Logging configured",
        log_level=settings.log_level,
        structured_logs=settings.structured_logs,
        renderer="JSON" if use_json else "Console"
    )


def get_audit_logger() -> structlog.BoundLogger:
    """
    Get a logger specifically for audit trail events.
    
    Audit events include:
    - Pricing decisions
    - Watchlist changes
    - Safety check failures
    - Budget limit warnings
    - Rate limit adaptations
    
    Returns:
        Logger configured for audit trails
    """
    return structlog.get_logger("audit")


def log_pricing_decision(
    sku_id: int,
    sku_code: str,
    action: str,
    old_price: float,
    new_price: float,
    competitor_price: float,
    margin_check_passed: bool,
    reasoning: str,
    worker_tokens: int,
    decision_id: int
) -> None:
    """
    Log a pricing decision to the audit trail.
    
    Args:
        sku_id: Database ID of the SKU
        sku_code: SKU identifier (e.g., "SKU-001")
        action: Action taken (MATCH, UNDERCUT_50, HOLD)
        old_price: Previous price
        new_price: New price after decision
        competitor_price: Competitor's price
        margin_check_passed: Whether margin safety check passed
        reasoning: LLM reasoning for the decision
        worker_tokens: Tokens used in worker call
        decision_id: Database ID of the decision record
    """
    logger = get_audit_logger()
    
    logger.info(
        "pricing_decision",
        event_type="pricing_decision",
        sku_id=sku_id,
        sku_code=sku_code,
        action=action,
        old_price=old_price,
        new_price=new_price,
        competitor_price=competitor_price,
        margin_check_passed=margin_check_passed,
        reasoning_preview=reasoning[:100] if reasoning else None,
        worker_tokens=worker_tokens,
        decision_id=decision_id,
        price_change=new_price - old_price,
        price_change_percent=((new_price - old_price) / old_price * 100) if old_price > 0 else 0
    )


def log_watchlist_change(
    run_id: int,
    added_skus: list[str],
    removed_skus: list[str],
    new_watchlist_size: int,
    watchlist_cap: int,
    reasoning: str,
    orchestrator_tokens: int
) -> None:
    """
    Log a watchlist change to the audit trail.
    
    Args:
        run_id: Database ID of the orchestrator run
        added_skus: List of SKU codes added
        removed_skus: List of SKU codes removed
        new_watchlist_size: Size of watchlist after changes
        watchlist_cap: Current watchlist capacity
        reasoning: LLM reasoning for the changes
        orchestrator_tokens: Tokens used in orchestrator call
    """
    logger = get_audit_logger()
    
    logger.info(
        "watchlist_change",
        event_type="watchlist_change",
        run_id=run_id,
        added_count=len(added_skus),
        removed_count=len(removed_skus),
        added_skus=added_skus,
        removed_skus=removed_skus,
        new_watchlist_size=new_watchlist_size,
        watchlist_cap=watchlist_cap,
        utilization_percent=(new_watchlist_size / watchlist_cap * 100) if watchlist_cap > 0 else 0,
        reasoning_preview=reasoning[:100] if reasoning else None,
        orchestrator_tokens=orchestrator_tokens
    )


def log_safety_violation(
    event_type: str,
    sku_code: str,
    proposed_action: str,
    violation_reason: str,
    current_price: float,
    proposed_price: float,
    margin_percent: float,
    details: Dict[str, Any]
) -> None:
    """
    Log a safety check violation to the audit trail.
    
    Args:
        event_type: Type of violation (margin_floor, gap_threshold)
        sku_code: SKU identifier
        proposed_action: Action that was rejected
        violation_reason: Why it was rejected
        current_price: Current price
        proposed_price: Proposed price that was rejected
        margin_percent: Calculated margin percentage
        details: Additional context
    """
    logger = get_audit_logger()
    
    logger.warning(
        "safety_violation",
        event_type="safety_violation",
        violation_type=event_type,
        sku_code=sku_code,
        proposed_action=proposed_action,
        violation_reason=violation_reason,
        current_price=current_price,
        proposed_price=proposed_price,
        margin_percent=margin_percent,
        **details
    )


def log_budget_warning(
    warning_type: str,
    current_usage: int,
    limit: int,
    usage_percent: float,
    action_taken: str
) -> None:
    """
    Log a budget warning or limit reached event.
    
    Args:
        warning_type: Type of warning (daily, minute)
        current_usage: Current call count
        limit: Call limit
        usage_percent: Percentage of limit used
        action_taken: Action taken (paused, stopped, warning)
    """
    logger = get_audit_logger()
    
    logger.warning(
        "budget_warning",
        event_type="budget_warning",
        warning_type=warning_type,
        current_usage=current_usage,
        limit=limit,
        usage_percent=usage_percent,
        action_taken=action_taken,
        remaining=limit - current_usage
    )


def log_rate_limit_adaptation(
    headroom_percent: float,
    old_cap: int,
    new_cap: int,
    reason: str,
    rate_limit_data: Dict[str, Any]
) -> None:
    """
    Log a rate limit adaptation event.
    
    Args:
        headroom_percent: Current headroom percentage
        old_cap: Previous watchlist cap
        new_cap: New watchlist cap
        reason: Reason for adjustment
        rate_limit_data: Rate limit details from API
    """
    logger = get_audit_logger()
    
    logger.info(
        "rate_limit_adaptation",
        event_type="rate_limit_adaptation",
        headroom_percent=headroom_percent,
        old_cap=old_cap,
        new_cap=new_cap,
        cap_change=new_cap - old_cap,
        reason=reason,
        **rate_limit_data
    )


def log_system_cycle(
    cycle_number: int,
    orchestrator_runs: int,
    worker_runs: int,
    total_calls: int,
    session_cost: float,
    budget_status: str,
    rate_limit_cap: int
) -> None:
    """
    Log a complete system cycle summary.
    
    Args:
        cycle_number: Cycle number
        orchestrator_runs: Total orchestrator runs
        worker_runs: Total worker runs
        total_calls: Total API calls
        session_cost: Cost this session in USD
        budget_status: Budget status (SAFE, WARNING, etc.)
        rate_limit_cap: Current rate limit cap
    """
    logger = get_audit_logger()
    
    logger.info(
        "system_cycle",
        event_type="system_cycle",
        cycle_number=cycle_number,
        orchestrator_runs=orchestrator_runs,
        worker_runs=worker_runs,
        total_calls=total_calls,
        session_cost_usd=session_cost,
        budget_status=budget_status,
        rate_limit_cap=rate_limit_cap
    )


# Initialize logging on module import
configure_logging()
