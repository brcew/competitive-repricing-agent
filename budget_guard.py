"""
Budget guard to prevent exceeding Groq API free tier limits.

This module monitors API call counts and automatically stops the system
BEFORE hitting hard limits to prevent service interruption or unexpected charges.

Groq Free Tier Limits (2026):
- Requests Per Day (RPD): ~14,400
- Requests Per Minute (RPM): ~30

Safety Strategy:
- Stop within 50 calls of daily limit (buffer zone)
- Stop within 5 calls of minute limit (buffer zone)
- Proactive alerting at 80% thresholds
- Graceful degradation (HOLD actions only)

This is CRITICAL SAFETY INFRASTRUCTURE to protect against overages.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional, Literal, Dict, Any

import structlog

from config import settings
from logging_config import log_budget_warning

logger = structlog.get_logger(__name__)


BudgetStatus = Literal["SAFE", "WARNING", "CRITICAL", "EXHAUSTED"]


@dataclass
class BudgetLimits:
    """Budget limits configuration."""
    
    # Daily limits
    daily_limit: int = 14400  # Groq free tier RPD
    daily_buffer: int = 50    # Stop before hitting limit
    daily_warning_percent: float = 80.0  # Alert at 80%
    
    # Minute limits  
    minute_limit: int = 30    # Groq free tier RPM
    minute_buffer: int = 5    # Stop before hitting limit
    minute_warning_percent: float = 70.0  # Alert at 70%
    
    def get_daily_stop_threshold(self) -> int:
        """Get the call count at which to stop (daily)."""
        return self.daily_limit - self.daily_buffer
    
    def get_minute_stop_threshold(self) -> int:
        """Get the call count at which to stop (minute)."""
        return self.minute_limit - self.minute_buffer


@dataclass
class BudgetState:
    """Current budget state."""
    
    # Daily counters
    calls_today: int
    daily_limit: int
    daily_remaining: int
    daily_usage_percent: float
    
    # Minute counters
    calls_this_minute: int
    minute_limit: int
    minute_remaining: int
    minute_usage_percent: float
    
    # Status
    status: BudgetStatus
    can_make_call: bool
    reason: str
    
    # Thresholds
    daily_stop_threshold: int
    minute_stop_threshold: int
    
    # Metadata
    checked_at: datetime


class BudgetGuard:
    """
    Guards against exceeding API call budgets.
    
    Features:
    - Tracks daily and per-minute call counts
    - Proactive stopping BEFORE hitting limits
    - Warning alerts at configurable thresholds
    - Graceful degradation modes
    - Integration with cost tracker
    """
    
    def __init__(self, limits: Optional[BudgetLimits] = None):
        """
        Initialize budget guard.
        
        Args:
            limits: Budget limits configuration
        """
        self.limits = limits or BudgetLimits()
        
        # Call tracking
        self.daily_calls = 0
        self.minute_calls = 0
        self.last_reset_day = datetime.now(timezone.utc).date()
        self.last_reset_minute = datetime.now(timezone.utc).replace(second=0, microsecond=0)
        
        # State tracking
        self.warnings_issued = {
            'daily': False,
            'minute': False
        }
        self.stopped = False
        self.stop_reason = None
        
        logger.info(
            "Budget guard initialized",
            daily_limit=self.limits.daily_limit,
            daily_buffer=self.limits.daily_buffer,
            minute_limit=self.limits.minute_limit,
            minute_buffer=self.limits.minute_buffer
        )
    
    def _reset_if_needed(self):
        """Reset counters if time periods have elapsed."""
        now = datetime.now(timezone.utc)
        
        # Reset daily counter if new day
        if now.date() > self.last_reset_day:
            logger.info(
                "Resetting daily call counter",
                previous_calls=self.daily_calls,
                date=now.date()
            )
            self.daily_calls = 0
            self.last_reset_day = now.date()
            self.warnings_issued['daily'] = False
            
            # Also reset stopped state on new day
            if self.stopped and 'daily' in self.stop_reason.lower():
                self.stopped = False
                self.stop_reason = None
                logger.info("Budget guard re-enabled for new day")
        
        # Reset minute counter if new minute
        current_minute = now.replace(second=0, microsecond=0)
        if current_minute > self.last_reset_minute:
            if self.minute_calls > 0:
                logger.debug(
                    "Resetting minute call counter",
                    previous_calls=self.minute_calls
                )
            self.minute_calls = 0
            self.last_reset_minute = current_minute
            self.warnings_issued['minute'] = False
            
            # Reset stopped state if minute limit was the issue
            if self.stopped and 'minute' in self.stop_reason.lower():
                self.stopped = False
                self.stop_reason = None
                logger.debug("Budget guard re-enabled for new minute")
    
    def check_budget(self) -> BudgetState:
        """
        Check current budget state.
        
        Returns:
            BudgetState with current status and limits
        """
        self._reset_if_needed()
        
        # Calculate daily metrics
        daily_remaining = self.limits.daily_limit - self.daily_calls
        daily_usage_percent = (self.daily_calls / self.limits.daily_limit * 100) if self.limits.daily_limit > 0 else 0
        daily_stop_threshold = self.limits.get_daily_stop_threshold()
        
        # Calculate minute metrics
        minute_remaining = self.limits.minute_limit - self.minute_calls
        minute_usage_percent = (self.minute_calls / self.limits.minute_limit * 100) if self.limits.minute_limit > 0 else 0
        minute_stop_threshold = self.limits.get_minute_stop_threshold()
        
        # Determine status and whether we can make a call
        status, can_make_call, reason = self._evaluate_status(
            daily_stop_threshold,
            minute_stop_threshold,
            daily_usage_percent,
            minute_usage_percent
        )
        
        return BudgetState(
            calls_today=self.daily_calls,
            daily_limit=self.limits.daily_limit,
            daily_remaining=daily_remaining,
            daily_usage_percent=daily_usage_percent,
            calls_this_minute=self.minute_calls,
            minute_limit=self.limits.minute_limit,
            minute_remaining=minute_remaining,
            minute_usage_percent=minute_usage_percent,
            status=status,
            can_make_call=can_make_call,
            reason=reason,
            daily_stop_threshold=daily_stop_threshold,
            minute_stop_threshold=minute_stop_threshold,
            checked_at=datetime.now(timezone.utc)
        )
    
    def _evaluate_status(
        self,
        daily_stop_threshold: int,
        minute_stop_threshold: int,
        daily_usage_percent: float,
        minute_usage_percent: float
    ) -> tuple[BudgetStatus, bool, str]:
        """
        Evaluate budget status and determine if calls are allowed.
        
        Returns:
            Tuple of (status, can_make_call, reason)
        """
        # Check if already stopped
        if self.stopped:
            return "EXHAUSTED", False, self.stop_reason
        
        # Check daily limit
        if self.daily_calls >= daily_stop_threshold:
            status = "EXHAUSTED"
            can_make_call = False
            reason = f"Daily budget exhausted: {self.daily_calls}/{self.limits.daily_limit} calls (stopped at {daily_stop_threshold} with {self.limits.daily_buffer} call buffer)"
            
            self.stopped = True
            self.stop_reason = reason
            
            logger.error(
                "Budget guard STOPPED system",
                reason=reason,
                daily_calls=self.daily_calls,
                threshold=daily_stop_threshold
            )
            
            # Log to audit trail
            log_budget_warning(
                warning_type="daily_exhausted",
                current_usage=self.daily_calls,
                limit=self.limits.daily_limit,
                usage_percent=daily_usage_percent,
                action_taken="stopped"
            )
            
            return status, can_make_call, reason
        
        # Check minute limit
        if self.minute_calls >= minute_stop_threshold:
            status = "CRITICAL"
            can_make_call = False
            reason = f"Minute rate limit reached: {self.minute_calls}/{self.limits.minute_limit} calls this minute (stopped at {minute_stop_threshold} with {self.limits.minute_buffer} call buffer)"
            
            # Don't mark as permanently stopped for minute limits
            logger.warning(
                "Budget guard temporarily paused",
                reason=reason,
                minute_calls=self.minute_calls
            )
            
            # Log to audit trail
            log_budget_warning(
                warning_type="minute_critical",
                current_usage=self.minute_calls,
                limit=self.limits.minute_limit,
                usage_percent=minute_usage_percent,
                action_taken="paused"
            )
            
            return status, can_make_call, reason
        
        # Check daily warning threshold
        if daily_usage_percent >= self.limits.daily_warning_percent:
            if not self.warnings_issued['daily']:
                logger.warning(
                    "Daily budget warning",
                    usage_percent=f"{daily_usage_percent:.1f}%",
                    calls=self.daily_calls,
                    limit=self.limits.daily_limit
                )
                
                # Log to audit trail
                log_budget_warning(
                    warning_type="daily_warning",
                    current_usage=self.daily_calls,
                    limit=self.limits.daily_limit,
                    usage_percent=daily_usage_percent,
                    action_taken="warning"
                )
                
                self.warnings_issued['daily'] = True
            
            return "WARNING", True, f"Daily budget at {daily_usage_percent:.1f}% ({self.daily_calls}/{self.limits.daily_limit} calls)"
        
        # Check minute warning threshold
        if minute_usage_percent >= self.limits.minute_warning_percent:
            if not self.warnings_issued['minute']:
                logger.warning(
                    "Minute rate warning",
                    usage_percent=f"{minute_usage_percent:.1f}%",
                    calls=self.minute_calls,
                    limit=self.limits.minute_limit
                )
                self.warnings_issued['minute'] = True
            
            return "WARNING", True, f"Minute rate at {minute_usage_percent:.1f}% ({self.minute_calls}/{self.limits.minute_limit} calls)"
        
        # All good
        return "SAFE", True, "Budget healthy"
    
    def record_call(self):
        """
        Record an API call.
        
        This should be called AFTER successfully making an API call.
        """
        self._reset_if_needed()
        
        self.daily_calls += 1
        self.minute_calls += 1
        
        logger.debug(
            "API call recorded",
            daily=self.daily_calls,
            minute=self.minute_calls
        )
    
    def can_make_call(self) -> tuple[bool, str]:
        """
        Check if a call can be made.
        
        Returns:
            Tuple of (allowed, reason)
        """
        state = self.check_budget()
        return state.can_make_call, state.reason
    
    def get_status_summary(self) -> Dict[str, Any]:
        """Get current budget status summary."""
        state = self.check_budget()
        
        return {
            "status": state.status,
            "can_make_call": state.can_make_call,
            "stopped": self.stopped,
            "daily": {
                "calls": state.calls_today,
                "limit": state.daily_limit,
                "remaining": state.daily_remaining,
                "usage_percent": state.daily_usage_percent,
                "stop_threshold": state.daily_stop_threshold
            },
            "minute": {
                "calls": state.calls_this_minute,
                "limit": state.minute_limit,
                "remaining": state.minute_remaining,
                "usage_percent": state.minute_usage_percent,
                "stop_threshold": state.minute_stop_threshold
            },
            "reason": state.reason,
            "last_check": state.checked_at
        }
    
    def reset(self):
        """Reset budget guard (for testing or manual override)."""
        self.daily_calls = 0
        self.minute_calls = 0
        self.stopped = False
        self.stop_reason = None
        self.warnings_issued = {'daily': False, 'minute': False}
        
        logger.warning("Budget guard manually reset")


# Global guard instance
_guard = None


def get_budget_guard() -> BudgetGuard:
    """Get or create the global budget guard instance."""
    global _guard
    if _guard is None:
        _guard = BudgetGuard()
    return _guard


# Convenience functions
def check_budget() -> BudgetState:
    """Check current budget state."""
    guard = get_budget_guard()
    return guard.check_budget()


def can_make_call() -> tuple[bool, str]:
    """Check if a call can be made."""
    guard = get_budget_guard()
    return guard.can_make_call()


def record_call():
    """Record an API call."""
    guard = get_budget_guard()
    guard.record_call()


def get_status_summary() -> Dict[str, Any]:
    """Get budget status summary."""
    guard = get_budget_guard()
    return guard.get_status_summary()
