"""
Trade Planning Service

Converts trading recommendations into actionable trade plans with
entry, stop loss, targets, and position sizing.
"""

from typing import Any
from app.core.logging import get_logger
from app.monitoring.metrics import metrics

logger = get_logger(__name__)


class TradePlanner:
    """
    Trade Planning Service
    
    Calculates trade execution parameters:
    - Entry price
    - Stop loss
    - Target levels (T1, T2)
    - Risk/reward ratio
    - Position sizing
    """
    
    # Position sizing by risk level (% of capital)
    POSITION_SIZE_MAP = {
        "low": 3.0,      # 3% per trade
        "medium": 2.0,   # 2% per trade
        "high": 1.0      # 1% per trade
    }
    
    # ATR multipliers for stop loss
    STOP_LOSS_ATR_MULTIPLE = {
        "low": 1.5,
        "medium": 2.0,
        "high": 2.5
    }
    
    # Minimum R:R threshold
    MIN_RISK_REWARD = 2.0
    
    def __init__(self):
        self.logger = get_logger(__name__)
    
    def plan_trade(
        self,
        recommendation: str,
        confidence: int,
        risk_level: str,
        current_price: float,
        signal_type: str,
        enrichment: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Calculate trade plan from recommendation.
        
        Args:
            recommendation: BUY/SELL/HOLD/SKIP
            confidence: 0-100
            risk_level: low/medium/high
            current_price: Current market price
            signal_type: PDH_BREAKOUT, etc.
            enrichment: Signal enrichment output with ATR, trend, etc.
        
        Returns:
            {
                "entry_price": float,
                "stop_loss": float,
                "target_1": float,
                "target_2": float,
                "risk_reward_ratio": float,
                "position_size_pct": float,
                "trade_valid": bool
            }
        """
        
        # Only plan for BUY/SELL
        if recommendation not in ["BUY", "SELL"]:
            return self._invalid_trade()
        
        # Extract enrichment data
        atr = enrichment.get("atr", 0)
        ema_trend = enrichment.get("ema_trend", "neutral")
        rsi = enrichment.get("rsi", 50)
        macd_trend = enrichment.get("macd_trend", "neutral")
        
        # Validate ATR exists
        if atr <= 0:
            self.logger.warning("Invalid ATR, cannot calculate trade plan")
            return self._invalid_trade()
        
        # Calculate entry price
        entry_price = self._calculate_entry(
            current_price=current_price,
            recommendation=recommendation,
            confidence=confidence
        )
        
        # Calculate stop loss
        stop_loss = self._calculate_stop_loss(
            entry_price=entry_price,
            recommendation=recommendation,
            atr=atr,
            risk_level=risk_level
        )
        
        # Calculate targets
        target_1, target_2 = self._calculate_targets(
            entry_price=entry_price,
            stop_loss=stop_loss,
            recommendation=recommendation,
            confidence=confidence,
            trend_strength=ema_trend
        )
        
        # Calculate risk/reward
        risk = abs(entry_price - stop_loss)
        reward_t1 = abs(target_1 - entry_price)
        reward_t2 = abs(target_2 - entry_price)
        
        rr_t1 = reward_t1 / risk if risk > 0 else 0
        rr_t2 = reward_t2 / risk if risk > 0 else 0
        
        # Average R:R
        risk_reward_ratio = round((rr_t1 + rr_t2) / 2, 2)
        
        # Validate minimum R:R
        trade_valid = risk_reward_ratio >= self.MIN_RISK_REWARD
        
        # Position sizing
        position_size_pct = self.POSITION_SIZE_MAP.get(risk_level, 2.0)
        
        # Adjust for trend alignment
        if recommendation == "BUY" and ema_trend == "bullish":
            position_size_pct *= 1.2
        elif recommendation == "SELL" and ema_trend == "bearish":
            position_size_pct *= 1.2
        
        # Cap position size
        position_size_pct = min(position_size_pct, 5.0)
        
        if not trade_valid:
            self.logger.info(
                f"Trade rejected: R:R {risk_reward_ratio} < {self.MIN_RISK_REWARD}"
            )
        
        # Record metrics
        metrics.record_cache_operation("trade_planning", "calculated")
        
        return {
            "entry_price": round(entry_price, 2),
            "stop_loss": round(stop_loss, 2),
            "target_1": round(target_1, 2),
            "target_2": round(target_2, 2),
            "risk_reward_ratio": risk_reward_ratio,
            "position_size_pct": round(position_size_pct, 2),
            "trade_valid": trade_valid
        }
    
    def _calculate_entry(
        self,
        current_price: float,
        recommendation: str,
        confidence: int
    ) -> float:
        """Calculate entry price"""
        # High confidence = immediate entry at market
        # Lower confidence = wait for slight pullback/bounce
        
        if confidence >= 70:
            return current_price
        elif confidence >= 60:
            # Small buffer (0.2%)
            adjustment = 0.002 if recommendation == "BUY" else -0.002
            return current_price * (1 + adjustment)
        else:
            # Larger buffer (0.5%)
            adjustment = 0.005 if recommendation == "BUY" else -0.005
            return current_price * (1 + adjustment)
    
    def _calculate_stop_loss(
        self,
        entry_price: float,
        recommendation: str,
        atr: float,
        risk_level: str
    ) -> float:
        """Calculate stop loss using ATR"""
        
        atr_multiple = self.STOP_LOSS_ATR_MULTIPLE.get(risk_level, 2.0)
        stop_distance = atr * atr_multiple
        
        if recommendation == "BUY":
            stop_loss = entry_price - stop_distance
        else:  # SELL
            stop_loss = entry_price + stop_distance
        
        return stop_loss
    
    def _calculate_targets(
        self,
        entry_price: float,
        stop_loss: float,
        recommendation: str,
        confidence: int,
        trend_strength: str
    ) -> tuple[float, float]:
        """Calculate target levels"""
        
        risk = abs(entry_price - stop_loss)
        
        # Base targets: 2R and 3R
        base_t1_multiple = 2.0
        base_t2_multiple = 3.0
        
        # Adjust for confidence
        if confidence >= 75:
            base_t1_multiple = 2.5
            base_t2_multiple = 4.0
        elif confidence >= 65:
            base_t1_multiple = 2.0
            base_t2_multiple = 3.5
        
        # Adjust for trend strength
        if trend_strength == "strong":
            base_t2_multiple *= 1.2
        
        if recommendation == "BUY":
            target_1 = entry_price + (risk * base_t1_multiple)
            target_2 = entry_price + (risk * base_t2_multiple)
        else:  # SELL
            target_1 = entry_price - (risk * base_t1_multiple)
            target_2 = entry_price - (risk * base_t2_multiple)
        
        return target_1, target_2
    
    def _invalid_trade(self) -> dict[str, Any]:
        """Return invalid trade plan"""
        return {
            "entry_price": 0.0,
            "stop_loss": 0.0,
            "target_1": 0.0,
            "target_2": 0.0,
            "risk_reward_ratio": 0.0,
            "position_size_pct": 0.0,
            "trade_valid": False
        }
