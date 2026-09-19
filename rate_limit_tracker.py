"""
Rate limit tracker for Groq API with dynamic watchlist cap adjustment.

This module monitors rate limit headers from Groq API responses and
dynamically adjusts the watchlist cap to stay within free tier limits.

Groq Free Tier Limits (2026):
- Requests Per Day (RPD): ~14,400
- Requests Per Minute (RPM): ~30
- Tokens Per Minute (TPM): varies by model (~12K for Llama 3.3 70B)
- Tokens Per Day (TPD): varies by model

Rate Limit Headers (standard):
- x-ratelimit-limit-requests
- x-ratelimit-remaining-requests
- x-ratelimit-limit-tokens
- x-ratelimit-remaining-tokens
- x-ratelimit-reset-requests
- x-ratelimit-reset-tokens

This is CRITICAL INFRASTRUCTURE for staying within free tier limits.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, Literal, Dict, Any

import structlog

from config import settings
from logging_config import log_rate_limit_adaptation

logger = structlog.get_logger(__name__)


RateLimitType = Literal["RPD", "RPM", "TPM", "TPD"]


@dataclass
class RateLimitStatus:
    """Current rate limit status from API headers."""
    
    # Request limits
    requests_limit: Optional[int] = None
    requests_remaining: Optional[int] = None
    requests_reset: Optional[datetime] = None
    
    # Token limits
    tokens_limit: Optional[int] = None
    tokens_remaining: Optional[int] = None
    tokens_reset: Optional[datetime] = None
    
    # Derived metrics
    requests_usage_percent: Optional[float] = None  # How much of quota used
    tokens_usage_percent: Optional[float] = None
    
    # Most constraining limit
    bottleneck: Optional[RateLimitType] = None
    
    # When captured
    captured_at: datetime = None
    
    def __post_init__(self):
        """Calculate derived metrics."""
        if self.captured_at is None:
            self.captured_at = datetime.now(timezone.utc)
        
        # Calculate usage percentages
        if self.requests_limit and self.requests_remaining is not None:
            used = self.requests_limit - self.requests_remaining
            self.requests_usage_percent = (used / self.requests_limit) * 100
        
        if self.tokens_limit and self.tokens_remaining is not None:
            used = self.tokens_limit - self.tokens_remaining
            self.tokens_usage_percent = (used / self.tokens_limit) * 100
        
        # Identify bottleneck (most constrained resource)
        self._identify_bottleneck()
    
    def _identify_bottleneck(self):
        """Identify which rate limit is most constraining."""
        usage_rates = []
        
        if self.requests_usage_percent is not None:
            usage_rates.append(("RPM", self.requests_usage_percent))
        
        if self.tokens_usage_percent is not None:
            usage_rates.append(("TPM", self.tokens_usage_percent))
        
        if usage_rates:
            # Bottleneck is the resource with highest usage
            self.bottleneck = max(usage_rates, key=lambda x: x[1])[0]


class RateLimitTracker:
    """
    Tracks rate limits and adjusts watchlist cap dynamically.
    
    Strategy:
    1. Parse rate limit headers from every API response
    2. Calculate headroom (how close we are to limits)
    3. If headroom < threshold, reduce watchlist cap
    4. Store rate limit context in orchestrator runs
    5. Gradually restore cap when headroom improves
    """
    
    def __init__(
        self,
        min_watchlist_cap: int = 5,
        max_watchlist_cap: int = None,
        headroom_threshold_percent: float = 20.0
    ):
        """
        Initialize rate limit tracker.
        
        Args:
            min_watchlist_cap: Minimum watchlist cap (safety floor)
            max_watchlist_cap: Maximum watchlist cap (from config)
            headroom_threshold_percent: Reduce cap if remaining < this %
        """
        self.min_watchlist_cap = min_watchlist_cap
        self.max_watchlist_cap = max_watchlist_cap or settings.watchlist_cap
        self.headroom_threshold_percent = headroom_threshold_percent
        
        self.current_cap = self.max_watchlist_cap
        self.last_status: Optional[RateLimitStatus] = None
        self.reduction_count = 0  # How many times we've reduced cap
        
        logger.info(
            "Rate limit tracker initialized",
            min_cap=self.min_watchlist_cap,
            max_cap=self.max_watchlist_cap,
            threshold=f"{headroom_threshold_percent}%"
        )
    
    def parse_rate_limit_headers(self, response_headers: Dict[str, str]) -> RateLimitStatus:
        """
        Parse rate limit headers from API response.
        
        Args:
            response_headers: HTTP headers from Groq API response
        
        Returns:
            RateLimitStatus with parsed values
        """
        # Parse headers (case-insensitive header lookup)
        headers_lower = {k.lower(): v for k, v in response_headers.items()}
        
        requests_limit = None
        requests_remaining = None
        tokens_limit = None
        tokens_remaining = None
        requests_reset = None
        tokens_reset = None
        
        # Requests
        if "x-ratelimit-limit-requests" in headers_lower:
            try:
                requests_limit = int(headers_lower["x-ratelimit-limit-requests"])
            except (ValueError, TypeError):
                pass
        
        if "x-ratelimit-remaining-requests" in headers_lower:
            try:
                requests_remaining = int(headers_lower["x-ratelimit-remaining-requests"])
            except (ValueError, TypeError):
                pass
        
        # Tokens
        if "x-ratelimit-limit-tokens" in headers_lower:
            try:
                tokens_limit = int(headers_lower["x-ratelimit-limit-tokens"])
            except (ValueError, TypeError):
                pass
        
        if "x-ratelimit-remaining-tokens" in headers_lower:
            try:
                tokens_remaining = int(headers_lower["x-ratelimit-remaining-tokens"])
            except (ValueError, TypeError):
                pass
        
        # Reset times (Unix timestamps)
        if "x-ratelimit-reset-requests" in headers_lower:
            try:
                timestamp = int(headers_lower["x-ratelimit-reset-requests"])
                requests_reset = datetime.fromtimestamp(timestamp)
            except (ValueError, TypeError):
                pass
        
        if "x-ratelimit-reset-tokens" in headers_lower:
            try:
                timestamp = int(headers_lower["x-ratelimit-reset-tokens"])
                tokens_reset = datetime.fromtimestamp(timestamp)
            except (ValueError, TypeError):
                pass
        
        # Create status (this will trigger __post_init__)
        status = RateLimitStatus(
            requests_limit=requests_limit,
            requests_remaining=requests_remaining,
            tokens_limit=tokens_limit,
            tokens_remaining=tokens_remaining,
            requests_reset=requests_reset,
            tokens_reset=tokens_reset
        )
        
        logger.debug(
            "Parsed rate limit headers",
            requests=f"{status.requests_remaining}/{status.requests_limit}",
            tokens=f"{status.tokens_remaining}/{status.tokens_limit}",
            requests_usage=f"{status.requests_usage_percent:.1f}%" if status.requests_usage_percent else "N/A",
            tokens_usage=f"{status.tokens_usage_percent:.1f}%" if status.tokens_usage_percent else "N/A"
        )
        
        return status
    
    def update_from_response(self, response: Any) -> RateLimitStatus:
        """
        Update rate limit status from API response object.
        
        Args:
            response: OpenAI API response object (has .headers or ._headers)
        
        Returns:
            RateLimitStatus with current limits
        """
        # Try to get headers from response
        headers = {}
        
        if hasattr(response, "headers"):
            headers = dict(response.headers) if response.headers else {}
        elif hasattr(response, "_headers"):
            headers = dict(response._headers) if response._headers else {}
        
        status = self.parse_rate_limit_headers(headers)
        self.last_status = status
        
        return status
    
    def calculate_headroom_percent(self, status: Optional[RateLimitStatus] = None) -> float:
        """
        Calculate rate limit headroom percentage.
        
        Headroom = minimum remaining percentage across all limits.
        Lower headroom = closer to hitting limits.
        
        Args:
            status: Rate limit status (uses last_status if None)
        
        Returns:
            Headroom percentage (0-100, lower is more constrained)
        """
        if status is None:
            status = self.last_status
        
        if status is None:
            return 100.0  # No data = assume full headroom
        
        remaining_percents = []
        
        if status.requests_remaining is not None and status.requests_limit:
            remaining_percent = (status.requests_remaining / status.requests_limit) * 100
            remaining_percents.append(remaining_percent)
        
        if status.tokens_remaining is not None and status.tokens_limit:
            remaining_percent = (status.tokens_remaining / status.tokens_limit) * 100
            remaining_percents.append(remaining_percent)
        
        if not remaining_percents:
            return 100.0  # No data
        
        # Headroom is the MINIMUM (most constrained resource)
        headroom = min(remaining_percents)
        
        return round(headroom, 2)
    
    def should_reduce_cap(self, headroom_percent: float) -> bool:
        """Check if watchlist cap should be reduced."""
        return (
            headroom_percent < self.headroom_threshold_percent
            and self.current_cap > self.min_watchlist_cap
        )
    
    def should_increase_cap(self, headroom_percent: float) -> bool:
        """Check if watchlist cap can be increased."""
        # Require higher threshold to increase (hysteresis)
        increase_threshold = self.headroom_threshold_percent + 30.0  # 50% if threshold is 20%
        
        return (
            headroom_percent > increase_threshold
            and self.current_cap < self.max_watchlist_cap
        )
    
    def adjust_watchlist_cap(
        self,
        status: Optional[RateLimitStatus] = None
    ) -> Dict[str, Any]:
        """
        Adjust watchlist cap based on rate limit status.
        
        Args:
            status: Rate limit status (uses last_status if None)
        
        Returns:
            Dict with adjustment details:
            - old_cap: Previous cap
            - new_cap: New cap
            - adjusted: Whether cap changed
            - reason: Explanation
            - headroom_percent: Current headroom
            - bottleneck: Most constrained resource
        """
        if status is None:
            status = self.last_status
        
        old_cap = self.current_cap
        headroom = self.calculate_headroom_percent(status)
        
        result = {
            "old_cap": old_cap,
            "new_cap": old_cap,
            "adjusted": False,
            "reason": "No adjustment needed",
            "headroom_percent": headroom,
            "bottleneck": status.bottleneck if status else None
        }
        
        # Check if we should reduce cap
        if self.should_reduce_cap(headroom):
            # Reduce by 20% (or to minimum)
            reduction = max(1, int(self.current_cap * 0.2))
            new_cap = max(self.min_watchlist_cap, self.current_cap - reduction)
            
            self.current_cap = new_cap
            self.reduction_count += 1
            
            result["new_cap"] = new_cap
            result["adjusted"] = True
            result["reason"] = (
                f"REDUCED: Headroom {headroom:.1f}% < {self.headroom_threshold_percent}% threshold. "
                f"Reduced cap by {old_cap - new_cap} to stay within rate limits."
            )
            
            logger.warning(
                "Watchlist cap reduced due to rate limits",
                old_cap=old_cap,
                new_cap=new_cap,
                headroom=f"{headroom:.1f}%",
                bottleneck=status.bottleneck if status else None,
                reduction_count=self.reduction_count
            )
            
            # Log to audit trail
            log_rate_limit_adaptation(
                headroom_percent=headroom,
                old_cap=old_cap,
                new_cap=new_cap,
                reason="Reduced due to low headroom",
                rate_limit_data={
                    "bottleneck": status.bottleneck if status else None,
                    "rpm_usage": f"{(status.requests_limit - status.requests_remaining) if status and status.requests_limit else 0}/{status.requests_limit if status and status.requests_limit else 0}" if status else None,
                    "tpm_usage": f"{(status.tokens_limit - status.tokens_remaining) if status and status.tokens_limit else 0}/{status.tokens_limit if status and status.tokens_limit else 0}" if status else None
                }
            )
        
        # Check if we can increase cap
        elif self.should_increase_cap(headroom):
            # Increase by 1 (conservative)
            new_cap = min(self.max_watchlist_cap, self.current_cap + 1)
            
            if new_cap > old_cap:
                self.current_cap = new_cap
                
                result["new_cap"] = new_cap
                result["adjusted"] = True
                result["reason"] = (
                    f"INCREASED: Headroom {headroom:.1f}% is healthy. "
                    f"Increased cap by {new_cap - old_cap}."
                )
                
                logger.info(
                    "Watchlist cap increased",
                    old_cap=old_cap,
                    new_cap=new_cap,
                    headroom=f"{headroom:.1f}%"
                )
        
        return result
    
    def get_current_cap(self) -> int:
        """Get current watchlist cap (may be reduced from configured max)."""
        return self.current_cap
    
    def get_status_summary(self) -> Dict[str, Any]:
        """Get current rate limit status summary."""
        status = self.last_status
        
        return {
            "current_cap": self.current_cap,
            "max_cap": self.max_watchlist_cap,
            "min_cap": self.min_watchlist_cap,
            "cap_reduced": self.current_cap < self.max_watchlist_cap,
            "reduction_count": self.reduction_count,
            "headroom_percent": self.calculate_headroom_percent(status),
            "bottleneck": status.bottleneck if status else None,
            "last_update": status.captured_at if status else None,
            "requests_remaining": status.requests_remaining if status else None,
            "tokens_remaining": status.tokens_remaining if status else None
        }


# Global tracker instance
_tracker = None


def get_rate_limit_tracker() -> RateLimitTracker:
    """Get or create the global rate limit tracker instance."""
    global _tracker
    if _tracker is None:
        _tracker = RateLimitTracker()
    return _tracker


# Convenience functions
def update_from_response(response: Any) -> RateLimitStatus:
    """Update rate limits from API response."""
    tracker = get_rate_limit_tracker()
    return tracker.update_from_response(response)


def adjust_watchlist_cap(status: Optional[RateLimitStatus] = None) -> Dict[str, Any]:
    """Adjust watchlist cap based on rate limits."""
    tracker = get_rate_limit_tracker()
    return tracker.adjust_watchlist_cap(status)


def get_current_cap() -> int:
    """Get current watchlist cap."""
    tracker = get_rate_limit_tracker()
    return tracker.get_current_cap()
