"""
Signal Enrichment Service

Calculates quantitative indicators from OHLCV data.
Provides structured technical context for agents.
"""

from typing import Any
import numpy as np
import pandas as pd

from app.core.logging import get_logger
from app.monitoring.metrics import metrics

logger = get_logger(__name__)


class SignalEnrichment:
    """
    Signal Enrichment Service
    
    Calculates technical indicators from candle data:
    - EMA 20/50/200
    - RSI 14
    - MACD
    - VWAP
    - ATR
    - Volume Ratio
    """
    
    def __init__(self):
        self.logger = get_logger(__name__)
    
    def enrich(self, candles: list[dict]) -> dict[str, Any]:
        """
        Calculate all indicators from OHLCV candle data.
        
        Args:
            candles: List of dicts with keys: timestamp, open, high, low, close, volume
        
        Returns:
            {
                "ema_20": float,
                "ema_50": float,
                "ema_200": float,
                "ema_trend": str,  # "bullish", "bearish", "neutral"
                "rsi": float,
                "rsi_signal": str,  # "overbought", "oversold", "neutral"
                "macd": float,
                "macd_signal": float,
                "macd_histogram": float,
                "macd_trend": str,  # "bullish", "bearish", "neutral"
                "vwap": float,
                "vwap_position": str,  # "above", "below", "at"
                "atr": float,
                "volume_ratio": float,
                "volume_signal": str  # "high", "normal", "low"
            }
        """
        if len(candles) < 200:
            self.logger.warning(f"Insufficient candles: {len(candles)}, need 200+ for all indicators")
        
        df = self._to_dataframe(candles)
        
        result = {
            **self._calculate_ema(df),
            **self._calculate_rsi(df),
            **self._calculate_macd(df),
            **self._calculate_vwap(df),
            **self._calculate_atr(df),
            **self._calculate_volume(df)
        }
        
        # Record metrics
        metrics.record_cache_operation("enrichment", "calculated")
        
        return result
    
    def _to_dataframe(self, candles: list[dict]) -> pd.DataFrame:
        """Convert candle list to DataFrame"""
        df = pd.DataFrame(candles)
        df = df.sort_values("timestamp")
        return df
    
    def _calculate_ema(self, df: pd.DataFrame) -> dict:
        """Calculate EMA 20/50/200 and trend signal"""
        close = df["close"]
        
        ema_20 = close.ewm(span=20, adjust=False).mean().iloc[-1] if len(df) >= 20 else close.iloc[-1]
        ema_50 = close.ewm(span=50, adjust=False).mean().iloc[-1] if len(df) >= 50 else close.iloc[-1]
        ema_200 = close.ewm(span=200, adjust=False).mean().iloc[-1] if len(df) >= 200 else close.iloc[-1]
        
        # Trend determination
        if ema_20 > ema_50 > ema_200:
            trend = "bullish"
        elif ema_20 < ema_50 < ema_200:
            trend = "bearish"
        else:
            trend = "neutral"
        
        return {
            "ema_20": round(ema_20, 2),
            "ema_50": round(ema_50, 2),
            "ema_200": round(ema_200, 2),
            "ema_trend": trend
        }
    
    def _calculate_rsi(self, df: pd.DataFrame, period: int = 14) -> dict:
        """Calculate RSI 14"""
        if len(df) < period + 1:
            return {"rsi": 50.0, "rsi_signal": "neutral"}
        
        close = df["close"]
        delta = close.diff()
        
        gain = delta.where(delta > 0, 0.0)
        loss = -delta.where(delta < 0, 0.0)
        
        avg_gain = gain.rolling(window=period).mean()
        avg_loss = loss.rolling(window=period).mean()
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        rsi_value = rsi.iloc[-1]
        
        # Signal determination
        if rsi_value > 70:
            signal = "overbought"
        elif rsi_value < 30:
            signal = "oversold"
        else:
            signal = "neutral"
        
        return {
            "rsi": round(rsi_value, 2),
            "rsi_signal": signal
        }
    
    def _calculate_macd(self, df: pd.DataFrame) -> dict:
        """Calculate MACD (12, 26, 9)"""
        if len(df) < 26:
            return {
                "macd": 0.0,
                "macd_signal": 0.0,
                "macd_histogram": 0.0,
                "macd_trend": "neutral"
            }
        
        close = df["close"]
        
        ema_12 = close.ewm(span=12, adjust=False).mean()
        ema_26 = close.ewm(span=26, adjust=False).mean()
        
        macd_line = ema_12 - ema_26
        signal_line = macd_line.ewm(span=9, adjust=False).mean()
        histogram = macd_line - signal_line
        
        macd_value = macd_line.iloc[-1]
        signal_value = signal_line.iloc[-1]
        hist_value = histogram.iloc[-1]
        
        # Trend determination
        if hist_value > 0 and macd_value > signal_value:
            trend = "bullish"
        elif hist_value < 0 and macd_value < signal_value:
            trend = "bearish"
        else:
            trend = "neutral"
        
        return {
            "macd": round(macd_value, 2),
            "macd_signal": round(signal_value, 2),
            "macd_histogram": round(hist_value, 2),
            "macd_trend": trend
        }
    
    def _calculate_vwap(self, df: pd.DataFrame) -> dict:
        """Calculate VWAP for current session"""
        if len(df) == 0:
            return {"vwap": 0.0, "vwap_position": "at"}
        
        typical_price = (df["high"] + df["low"] + df["close"]) / 3
        vwap = (typical_price * df["volume"]).sum() / df["volume"].sum()
        
        current_price = df["close"].iloc[-1]
        
        # Position determination
        diff_pct = ((current_price - vwap) / vwap) * 100
        
        if diff_pct > 0.5:
            position = "above"
        elif diff_pct < -0.5:
            position = "below"
        else:
            position = "at"
        
        return {
            "vwap": round(vwap, 2),
            "vwap_position": position
        }
    
    def _calculate_atr(self, df: pd.DataFrame, period: int = 14) -> dict:
        """Calculate ATR 14"""
        if len(df) < period + 1:
            return {"atr": 0.0}
        
        high = df["high"]
        low = df["low"]
        close = df["close"]
        
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean().iloc[-1]
        
        return {"atr": round(atr, 2)}
    
    def _calculate_volume(self, df: pd.DataFrame, period: int = 20) -> dict:
        """Calculate volume ratio vs average"""
        if len(df) < period:
            return {"volume_ratio": 1.0, "volume_signal": "normal"}
        
        volume = df["volume"]
        avg_volume = volume.rolling(window=period).mean().iloc[-1]
        current_volume = volume.iloc[-1]
        
        ratio = current_volume / avg_volume if avg_volume > 0 else 1.0
        
        # Signal determination
        if ratio > 1.5:
            signal = "high"
        elif ratio < 0.7:
            signal = "low"
        else:
            signal = "normal"
        
        return {
            "volume_ratio": round(ratio, 2),
            "volume_signal": signal
        }
