"""
Tests for Signal Enrichment Service
"""

import pytest
from app.services.signal_enrichment import SignalEnrichment


@pytest.fixture
def enrichment_service():
    return SignalEnrichment()


@pytest.fixture
def sample_candles():
    """Generate 250 sample candles for testing"""
    candles = []
    price = 100.0
    volume = 1000000
    
    for i in range(250):
        # Simulate price movement
        price_change = (i % 10 - 5) * 0.5
        price += price_change
        
        candles.append({
            "timestamp": i,
            "open": price,
            "high": price + 1.0,
            "low": price - 1.0,
            "close": price,
            "volume": volume + (i * 1000)
        })
    
    return candles


def test_enrichment_with_sufficient_data(enrichment_service, sample_candles):
    """Test enrichment with 250 candles"""
    result = enrichment_service.enrich(sample_candles)
    
    # Check all required fields exist
    assert "ema_20" in result
    assert "ema_50" in result
    assert "ema_200" in result
    assert "ema_trend" in result
    assert "rsi" in result
    assert "rsi_signal" in result
    assert "macd" in result
    assert "macd_signal" in result
    assert "macd_histogram" in result
    assert "macd_trend" in result
    assert "vwap" in result
    assert "vwap_position" in result
    assert "atr" in result
    assert "volume_ratio" in result
    assert "volume_signal" in result
    
    # Validate value ranges
    assert 0 <= result["rsi"] <= 100
    assert result["ema_trend"] in ["bullish", "bearish", "neutral"]
    assert result["rsi_signal"] in ["overbought", "oversold", "neutral"]
    assert result["macd_trend"] in ["bullish", "bearish", "neutral"]
    assert result["vwap_position"] in ["above", "below", "at"]
    assert result["volume_signal"] in ["high", "normal", "low"]
    assert result["volume_ratio"] > 0


def test_enrichment_with_minimal_data(enrichment_service):
    """Test enrichment with only 30 candles"""
    candles = [
        {
            "timestamp": i,
            "open": 100 + i,
            "high": 101 + i,
            "low": 99 + i,
            "close": 100 + i,
            "volume": 1000000
        }
        for i in range(30)
    ]
    
    result = enrichment_service.enrich(candles)
    
    # Should still return all fields even with limited data
    assert "ema_20" in result
    assert "rsi" in result
    assert "macd" in result
    assert "vwap" in result
    assert "atr" in result
    assert "volume_ratio" in result


def test_bullish_trend_detection(enrichment_service):
    """Test bullish trend detection with upward price movement"""
    candles = []
    for i in range(250):
        price = 100 + (i * 0.5)  # Steady uptrend
        candles.append({
            "timestamp": i,
            "open": price,
            "high": price + 1,
            "low": price - 0.5,
            "close": price,
            "volume": 1000000
        })
    
    result = enrichment_service.enrich(candles)
    
    assert result["ema_trend"] == "bullish"
    assert result["ema_20"] > result["ema_50"]
    assert result["ema_50"] > result["ema_200"]


def test_bearish_trend_detection(enrichment_service):
    """Test bearish trend detection with downward price movement"""
    candles = []
    for i in range(250):
        price = 200 - (i * 0.5)  # Steady downtrend
        candles.append({
            "timestamp": i,
            "open": price,
            "high": price + 0.5,
            "low": price - 1,
            "close": price,
            "volume": 1000000
        })
    
    result = enrichment_service.enrich(candles)
    
    assert result["ema_trend"] == "bearish"
    assert result["ema_20"] < result["ema_50"]
    assert result["ema_50"] < result["ema_200"]


def test_rsi_overbought(enrichment_service):
    """Test RSI overbought detection"""
    candles = []
    for i in range(50):
        price = 100 + (i * 2)  # Strong upward movement
        candles.append({
            "timestamp": i,
            "open": price,
            "high": price + 1,
            "low": price,
            "close": price,
            "volume": 1000000
        })
    
    result = enrichment_service.enrich(candles)
    
    assert result["rsi"] > 60  # Should be high
    assert result["rsi_signal"] in ["overbought", "neutral"]


def test_rsi_oversold(enrichment_service):
    """Test RSI oversold detection"""
    candles = []
    for i in range(50):
        price = 200 - (i * 2)  # Strong downward movement
        candles.append({
            "timestamp": i,
            "open": price,
            "high": price,
            "low": price - 1,
            "close": price,
            "volume": 1000000
        })
    
    result = enrichment_service.enrich(candles)
    
    assert result["rsi"] < 50  # Should be low
    assert result["rsi_signal"] in ["oversold", "neutral"]


def test_high_volume_detection(enrichment_service):
    """Test high volume signal detection"""
    candles = []
    for i in range(50):
        volume = 1000000 if i < 49 else 2000000  # Last candle has 2x volume
        candles.append({
            "timestamp": i,
            "open": 100,
            "high": 101,
            "low": 99,
            "close": 100,
            "volume": volume
        })
    
    result = enrichment_service.enrich(candles)
    
    assert result["volume_ratio"] > 1.5
    assert result["volume_signal"] == "high"


def test_vwap_calculation(enrichment_service):
    """Test VWAP calculation accuracy"""
    candles = [
        {"timestamp": 1, "open": 100, "high": 102, "low": 99, "close": 101, "volume": 1000},
        {"timestamp": 2, "open": 101, "high": 103, "low": 100, "close": 102, "volume": 1500},
        {"timestamp": 3, "open": 102, "high": 104, "low": 101, "close": 103, "volume": 2000},
    ]
    
    result = enrichment_service.enrich(candles)
    
    # VWAP should be somewhere around typical price weighted by volume
    assert 100 < result["vwap"] < 104
    assert result["vwap_position"] in ["above", "below", "at"]


def test_atr_calculation(enrichment_service):
    """Test ATR calculation"""
    candles = []
    for i in range(50):
        candles.append({
            "timestamp": i,
            "open": 100,
            "high": 105,  # 5 point range
            "low": 95,
            "close": 100,
            "volume": 1000000
        })
    
    result = enrichment_service.enrich(candles)
    
    # ATR should reflect the average true range
    assert result["atr"] > 0
    assert result["atr"] < 20  # Should be reasonable


def test_macd_bullish_crossover(enrichment_service):
    """Test MACD bullish trend detection"""
    candles = []
    
    # Flat then uptrend
    for i in range(100):
        if i < 50:
            price = 100
        else:
            price = 100 + ((i - 50) * 0.5)
        
        candles.append({
            "timestamp": i,
            "open": price,
            "high": price + 1,
            "low": price - 1,
            "close": price,
            "volume": 1000000
        })
    
    result = enrichment_service.enrich(candles)
    
    assert result["macd_trend"] in ["bullish", "neutral"]
    assert result["macd_histogram"] >= 0 or result["macd_trend"] == "neutral"


def test_empty_candles(enrichment_service):
    """Test behavior with empty candles"""
    with pytest.raises(Exception):
        enrichment_service.enrich([])
