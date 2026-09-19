"""
Competitor price simulator with realistic behavior patterns.

Simulates Amazon pricing with:
- Random walk (small daily fluctuations)
- Occasional aggressive undercuts
- Price noise and volatility
- Stock availability changes

This avoids scraping real Amazon data (ToS violation) while maintaining
a realistic interface that can be swapped for a real scraper later.
"""

import random
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

import structlog

from db_utils import get_db_session
from models import SKU, CompetitorPrice

logger = structlog.get_logger(__name__)


class CompetitorPriceSimulator:
    """
    Simulates competitor (Amazon) pricing behavior.
    
    Pricing model:
    - Base price: slightly below our price (competitive)
    - Random walk: ±1-3% daily fluctuations
    - Aggressive undercuts: 10-20% below us (5% probability)
    - Price recovery: gradual return to mean after undercuts
    - Availability: 95% in stock, occasional out-of-stock
    """
    
    def __init__(
        self,
        base_discount_percent: float = 5.0,  # Typically 5% below our price
        daily_volatility_percent: float = 2.0,  # ±2% daily random walk
        aggressive_undercut_probability: float = 0.05,  # 5% chance per fetch
        aggressive_undercut_range: tuple = (10.0, 20.0),  # 10-20% undercut
        availability_probability: float = 0.95,  # 95% in stock
        mean_reversion_factor: float = 0.1,  # 10% reversion to mean per period
    ):
        """Initialize the simulator with behavior parameters."""
        self.base_discount_percent = base_discount_percent
        self.daily_volatility_percent = daily_volatility_percent
        self.aggressive_undercut_probability = aggressive_undercut_probability
        self.aggressive_undercut_range = aggressive_undercut_range
        self.availability_probability = availability_probability
        self.mean_reversion_factor = mean_reversion_factor
        
        # Track state for each SKU to maintain continuity
        self._sku_state: Dict[int, Dict[str, Any]] = {}
    
    def _get_or_create_state(self, sku: SKU) -> Dict[str, Any]:
        """Get or initialize state for a SKU."""
        if sku.id not in self._sku_state:
            # Calculate base competitor price (typically below ours)
            discount_factor = 1.0 - (self.base_discount_percent / 100.0)
            base_price = sku.our_price * discount_factor
            
            self._sku_state[sku.id] = {
                "base_price": base_price,
                "current_price": base_price,
                "last_fetch": None,
                "in_aggressive_undercut": False,
                "undercut_recovery_target": None,
            }
        
        return self._sku_state[sku.id]
    
    def _apply_random_walk(self, price: float) -> float:
        """Apply small random fluctuation to price."""
        volatility = self.daily_volatility_percent / 100.0
        change_factor = 1.0 + random.uniform(-volatility, volatility)
        return price * change_factor
    
    def _apply_mean_reversion(self, current_price: float, target_price: float) -> float:
        """Gradually revert price toward target (mean reversion)."""
        difference = target_price - current_price
        adjustment = difference * self.mean_reversion_factor
        return current_price + adjustment
    
    def _should_trigger_aggressive_undercut(self) -> bool:
        """Randomly decide if an aggressive undercut should occur."""
        return random.random() < self.aggressive_undercut_probability
    
    def _calculate_aggressive_undercut(self, our_price: float) -> float:
        """Calculate a significant undercut price."""
        undercut_percent = random.uniform(*self.aggressive_undercut_range)
        discount_factor = 1.0 - (undercut_percent / 100.0)
        return our_price * discount_factor
    
    def _is_available(self) -> bool:
        """Randomly determine if product is in stock."""
        return random.random() < self.availability_probability
    
    def get_competitor_price(
        self,
        sku: SKU,
        competitor_name: str = "Amazon"
    ) -> Dict[str, Any]:
        """
        Get current competitor price for a SKU.
        
        Args:
            sku: The SKU to get competitor price for
            competitor_name: Name of competitor (default: "Amazon")
        
        Returns:
            Dict with competitor price data:
            {
                "competitor_name": str,
                "competitor_price": float,
                "is_available": bool,
                "confidence": float,
                "source": str,
                "fetched_at": datetime
            }
        """
        state = self._get_or_create_state(sku)
        
        # Check if in stock
        is_available = self._is_available()
        
        if not is_available:
            # Product out of stock - return unavailable
            logger.info(
                "Competitor out of stock",
                sku=sku.sku,
                competitor=competitor_name
            )
            return {
                "competitor_name": competitor_name,
                "competitor_price": state["current_price"],  # Last known price
                "is_available": False,
                "confidence": 0.8,  # Lower confidence for out-of-stock
                "source": "simulator",
                "fetched_at": datetime.utcnow()
            }
        
        # Determine current price based on state
        if state["in_aggressive_undercut"]:
            # Recovering from aggressive undercut - gradual mean reversion
            new_price = self._apply_mean_reversion(
                state["current_price"],
                state["undercut_recovery_target"]
            )
            
            # Check if recovered enough to exit undercut mode
            if abs(new_price - state["undercut_recovery_target"]) < 0.50:
                state["in_aggressive_undercut"] = False
                state["undercut_recovery_target"] = None
                logger.info(
                    "Recovered from aggressive undercut",
                    sku=sku.sku,
                    new_price=round(new_price, 2)
                )
        
        elif self._should_trigger_aggressive_undercut():
            # Trigger new aggressive undercut
            new_price = self._calculate_aggressive_undercut(sku.our_price)
            state["in_aggressive_undercut"] = True
            state["undercut_recovery_target"] = state["base_price"]
            
            logger.info(
                "Aggressive undercut triggered",
                sku=sku.sku,
                old_price=round(state["current_price"], 2),
                new_price=round(new_price, 2),
                undercut_percent=round((1 - new_price / sku.our_price) * 100, 1)
            )
        
        else:
            # Normal random walk
            new_price = self._apply_random_walk(state["current_price"])
            
            # Gentle mean reversion toward base price
            new_price = self._apply_mean_reversion(new_price, state["base_price"])
        
        # Ensure price stays positive and reasonable
        new_price = max(new_price, sku.cost * 0.8)  # Never below 80% of our cost
        new_price = min(new_price, sku.our_price * 1.2)  # Never more than 20% above us
        
        # Round to realistic cents
        new_price = round(new_price, 2)
        
        # Update state
        state["current_price"] = new_price
        state["last_fetch"] = datetime.utcnow()
        
        return {
            "competitor_name": competitor_name,
            "competitor_price": new_price,
            "is_available": True,
            "confidence": 1.0,
            "source": "simulator",
            "fetched_at": datetime.utcnow()
        }
    
    def fetch_and_store_price(
        self,
        sku: SKU,
        competitor_name: str = "Amazon"
    ) -> CompetitorPrice:
        """
        Fetch competitor price and store in database.
        
        Args:
            sku: The SKU to fetch price for
            competitor_name: Name of competitor
        
        Returns:
            CompetitorPrice database record
        """
        price_data = self.get_competitor_price(sku, competitor_name)
        
        with get_db_session() as session:
            comp_price = CompetitorPrice(
                sku_id=sku.id,
                competitor_name=price_data["competitor_name"],
                competitor_price=price_data["competitor_price"],
                is_available=price_data["is_available"],
                confidence=price_data["confidence"],
                fetched_at=price_data["fetched_at"],
                source=price_data["source"]
            )
            session.add(comp_price)
            session.commit()
            
            # Make object usable outside session
            comp_price_id = comp_price.id
            comp_price_price = comp_price.competitor_price
        
        logger.debug(
            "Stored competitor price",
            sku=sku.sku,
            competitor_price=comp_price_price,
            our_price=sku.our_price
        )
        
        # Return a detached copy with essential data
        result = CompetitorPrice(
            id=comp_price_id,
            sku_id=sku.id,
            competitor_name=price_data["competitor_name"],
            competitor_price=price_data["competitor_price"],
            is_available=price_data["is_available"],
            confidence=price_data["confidence"],
            fetched_at=price_data["fetched_at"],
            source=price_data["source"]
        )
        
        return result
    
    def get_latest_competitor_price(self, sku_id: int) -> Optional[CompetitorPrice]:
        """
        Get the most recent competitor price from database.
        
        Args:
            sku_id: ID of the SKU
        
        Returns:
            Latest CompetitorPrice record or None
        """
        with get_db_session() as session:
            latest = session.query(CompetitorPrice)\
                .filter_by(sku_id=sku_id)\
                .order_by(CompetitorPrice.fetched_at.desc())\
                .first()
            
            if latest:
                # Detach from session to use outside context
                session.expunge(latest)
            
            return latest


# Global simulator instance
_simulator = None


def get_simulator() -> CompetitorPriceSimulator:
    """Get or create the global simulator instance."""
    global _simulator
    if _simulator is None:
        _simulator = CompetitorPriceSimulator()
    return _simulator


# Convenience functions for easy access
def get_competitor_price(sku: SKU, competitor_name: str = "Amazon") -> Dict[str, Any]:
    """Get competitor price for a SKU (convenience function)."""
    simulator = get_simulator()
    return simulator.get_competitor_price(sku, competitor_name)


def fetch_and_store_price(sku: SKU, competitor_name: str = "Amazon") -> CompetitorPrice:
    """Fetch and store competitor price (convenience function)."""
    simulator = get_simulator()
    return simulator.fetch_and_store_price(sku, competitor_name)


def get_latest_price(sku_id: int) -> Optional[CompetitorPrice]:
    """Get latest competitor price from database (convenience function)."""
    simulator = get_simulator()
    return simulator.get_latest_competitor_price(sku_id)