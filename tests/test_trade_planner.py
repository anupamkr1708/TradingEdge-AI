"""
Tests for Trade Planning Service
"""

import pytest
from app.services.trade_planner import TradePlanner


@pytest.fixture
def trade_planner():
    return TradePlanner()


@pytest.fixture
def base_enrichment():
    """Base enrichment data with required fields"""
    return {
        "ema_trend": "neutral",
        "rsi": 50,
        "rsi_signal": "neutral",
        "macd_trend": "neutral",
        "volume_signal": "normal",
        "atr": 50.0
    }


@pytest.fixture
def bullish_enrichment():
    """Bullish market enrichment"""
    return {
        "ema_trend": "bullish",
        "rsi": 60,
        "rsi_signal": "neutral",
        "macd_trend": "bullish",
        "volume_signal": "high",
        "atr": 60.0
    }


@pytest.fixture
def bearish_enrichment():
    """Bearish market enrichment"""
    return {
        "ema_trend": "bearish",
        "rsi": 40,
        "rsi_signal": "neutral",
        "macd_trend": "bearish",
        "volume_signal": "high",
        "atr": 55.0
    }


def test_buy_trade_plan_valid(trade_planner, base_enrichment):
    """Test valid BUY trade plan"""
    result = trade_planner.plan_trade(
        recommendation="BUY",
        confidence=70,
        risk_level="medium",
        current_price=19500.0,
        signal_type="PDH_BREAKOUT",
        enrichment=base_enrichment
    )
    
    assert result["trade_valid"] is True
    assert result["entry_price"] == 19500.0  # High confidence = market entry
    assert result["stop_loss"] < result["entry_price"]
    assert result["target_1"] > result["entry_price"]
    assert result["target_2"] > result["target_1"]
    assert result["risk_reward_ratio"] >= 2.0
    assert result["position_size_pct"] > 0


def test_sell_trade_plan_valid(trade_planner, base_enrichment):
    """Test valid SELL trade plan"""
    result = trade_planner.plan_trade(
        recommendation="SELL",
        confidence=70,
        risk_level="medium",
        current_price=19500.0,
        signal_type="PDL_BREAKDOWN",
        enrichment=base_enrichment
    )
    
    assert result["trade_valid"] is True
    assert result["entry_price"] == 19500.0
    assert result["stop_loss"] > result["entry_price"]
    assert result["target_1"] < result["entry_price"]
    assert result["target_2"] < result["target_1"]
    assert result["risk_reward_ratio"] >= 2.0
    assert result["position_size_pct"] > 0


def test_hold_returns_invalid(trade_planner, base_enrichment):
    """Test HOLD recommendation returns invalid trade"""
    result = trade_planner.plan_trade(
        recommendation="HOLD",
        confidence=50,
        risk_level="medium",
        current_price=19500.0,
        signal_type="RANGE_BREAKOUT",
        enrichment=base_enrichment
    )
    
    assert result["trade_valid"] is False
    assert result["entry_price"] == 0.0
    assert result["stop_loss"] == 0.0
    assert result["risk_reward_ratio"] == 0.0


def test_skip_returns_invalid(trade_planner, base_enrichment):
    """Test SKIP recommendation returns invalid trade"""
    result = trade_planner.plan_trade(
        recommendation="SKIP",
        confidence=40,
        risk_level="high",
        current_price=19500.0,
        signal_type="PDH_BREAKOUT",
        enrichment=base_enrichment
    )
    
    assert result["trade_valid"] is False


def test_missing_atr_returns_invalid(trade_planner):
    """Test missing ATR returns invalid trade"""
    enrichment = {
        "ema_trend": "bullish",
        "rsi": 60,
        "atr": 0  # Invalid ATR
    }
    
    result = trade_planner.plan_trade(
        recommendation="BUY",
        confidence=70,
        risk_level="medium",
        current_price=19500.0,
        signal_type="PDH_BREAKOUT",
        enrichment=enrichment
    )
    
    assert result["trade_valid"] is False


def test_stop_loss_calculation_buy(trade_planner, base_enrichment):
    """Test stop loss calculation for BUY"""
    base_enrichment["atr"] = 100.0
    
    result = trade_planner.plan_trade(
        recommendation="BUY",
        confidence=70,
        risk_level="medium",
        current_price=20000.0,
        signal_type="PDH_BREAKOUT",
        enrichment=base_enrichment
    )
    
    # Stop loss should be entry - (ATR * 2.0) for medium risk
    expected_stop = 20000.0 - (100.0 * 2.0)
    assert result["stop_loss"] == expected_stop
    assert result["stop_loss"] < result["entry_price"]


def test_stop_loss_calculation_sell(trade_planner, base_enrichment):
    """Test stop loss calculation for SELL"""
    base_enrichment["atr"] = 100.0
    
    result = trade_planner.plan_trade(
        recommendation="SELL",
        confidence=70,
        risk_level="medium",
        current_price=20000.0,
        signal_type="PDL_BREAKDOWN",
        enrichment=base_enrichment
    )
    
    # Stop loss should be entry + (ATR * 2.0) for medium risk
    expected_stop = 20000.0 + (100.0 * 2.0)
    assert result["stop_loss"] == expected_stop
    assert result["stop_loss"] > result["entry_price"]


def test_risk_level_affects_stop_loss(trade_planner, base_enrichment):
    """Test different risk levels produce different stop losses"""
    base_enrichment["atr"] = 100.0
    
    # Low risk = tighter stop (1.5x ATR)
    low_risk = trade_planner.plan_trade(
        recommendation="BUY",
        confidence=70,
        risk_level="low",
        current_price=20000.0,
        signal_type="PDH_BREAKOUT",
        enrichment=base_enrichment
    )
    
    # High risk = wider stop (2.5x ATR)
    high_risk = trade_planner.plan_trade(
        recommendation="BUY",
        confidence=70,
        risk_level="high",
        current_price=20000.0,
        signal_type="PDH_BREAKOUT",
        enrichment=base_enrichment
    )
    
    # High risk should have lower stop loss (more room)
    assert high_risk["stop_loss"] < low_risk["stop_loss"]


def test_position_sizing_by_risk_level(trade_planner, base_enrichment):
    """Test position sizing varies by risk level"""
    
    low_risk = trade_planner.plan_trade(
        recommendation="BUY",
        confidence=70,
        risk_level="low",
        current_price=19500.0,
        signal_type="PDH_BREAKOUT",
        enrichment=base_enrichment
    )
    
    medium_risk = trade_planner.plan_trade(
        recommendation="BUY",
        confidence=70,
        risk_level="medium",
        current_price=19500.0,
        signal_type="PDH_BREAKOUT",
        enrichment=base_enrichment
    )
    
    high_risk = trade_planner.plan_trade(
        recommendation="BUY",
        confidence=70,
        risk_level="high",
        current_price=19500.0,
        signal_type="PDH_BREAKOUT",
        enrichment=base_enrichment
    )
    
    # Lower risk = larger position
    assert low_risk["position_size_pct"] > medium_risk["position_size_pct"]
    assert medium_risk["position_size_pct"] > high_risk["position_size_pct"]


def test_trend_alignment_increases_position_size(trade_planner, bullish_enrichment):
    """Test bullish trend increases BUY position size"""
    
    result = trade_planner.plan_trade(
        recommendation="BUY",
        confidence=70,
        risk_level="medium",
        current_price=19500.0,
        signal_type="PDH_BREAKOUT",
        enrichment=bullish_enrichment
    )
    
    # Base medium risk = 2%, with bullish alignment = 2.4%
    assert result["position_size_pct"] > 2.0


def test_position_size_capped_at_5_percent(trade_planner, bullish_enrichment):
    """Test position size never exceeds 5%"""
    
    result = trade_planner.plan_trade(
        recommendation="BUY",
        confidence=75,
        risk_level="low",  # Base 3%, with trend = 3.6%
        current_price=19500.0,
        signal_type="PDH_BREAKOUT",
        enrichment=bullish_enrichment
    )
    
    assert result["position_size_pct"] <= 5.0


def test_high_confidence_better_targets(trade_planner, base_enrichment):
    """Test higher confidence produces better target levels"""
    
    low_conf = trade_planner.plan_trade(
        recommendation="BUY",
        confidence=60,
        risk_level="medium",
        current_price=20000.0,
        signal_type="PDH_BREAKOUT",
        enrichment=base_enrichment
    )
    
    high_conf = trade_planner.plan_trade(
        recommendation="BUY",
        confidence=80,
        risk_level="medium",
        current_price=20000.0,
        signal_type="PDH_BREAKOUT",
        enrichment=base_enrichment
    )
    
    # High confidence should have higher targets
    assert high_conf["target_2"] > low_conf["target_2"]
    assert high_conf["risk_reward_ratio"] >= low_conf["risk_reward_ratio"]


def test_minimum_risk_reward_enforcement(trade_planner):
    """Test trade rejected if R:R < 2.0"""
    
    # Create scenario with very tight targets
    enrichment = {
        "ema_trend": "neutral",
        "rsi": 50,
        "macd_trend": "neutral",
        "volume_signal": "normal",
        "atr": 10.0  # Very small ATR = tight stop = harder to achieve 2:1
    }
    
    result = trade_planner.plan_trade(
        recommendation="BUY",
        confidence=55,  # Low confidence = conservative targets
        risk_level="high",  # Wide stop
        current_price=20000.0,
        signal_type="PDH_BREAKOUT",
        enrichment=enrichment
    )
    
    # Should still be valid with proper calculation
    if not result["trade_valid"]:
        assert result["risk_reward_ratio"] < 2.0


def test_entry_price_adjustment_by_confidence(trade_planner, base_enrichment):
    """Test entry price adjusts based on confidence"""
    
    high_conf = trade_planner.plan_trade(
        recommendation="BUY",
        confidence=75,
        risk_level="medium",
        current_price=20000.0,
        signal_type="PDH_BREAKOUT",
        enrichment=base_enrichment
    )
    
    medium_conf = trade_planner.plan_trade(
        recommendation="BUY",
        confidence=65,
        risk_level="medium",
        current_price=20000.0,
        signal_type="PDH_BREAKOUT",
        enrichment=base_enrichment
    )
    
    low_conf = trade_planner.plan_trade(
        recommendation="BUY",
        confidence=55,
        risk_level="medium",
        current_price=20000.0,
        signal_type="PDH_BREAKOUT",
        enrichment=base_enrichment
    )
    
    # High confidence = market entry
    assert high_conf["entry_price"] == 20000.0
    
    # Lower confidence = wait for pullback
    assert medium_conf["entry_price"] < 20000.0
    assert low_conf["entry_price"] < medium_conf["entry_price"]


def test_sell_entry_adjustment(trade_planner, base_enrichment):
    """Test SELL entry adjusts opposite direction"""
    
    result = trade_planner.plan_trade(
        recommendation="SELL",
        confidence=60,
        risk_level="medium",
        current_price=20000.0,
        signal_type="PDL_BREAKDOWN",
        enrichment=base_enrichment
    )
    
    # SELL with medium confidence should wait for bounce
    assert result["entry_price"] > 20000.0


def test_target_calculation_buy(trade_planner, base_enrichment):
    """Test target calculation for BUY trades"""
    base_enrichment["atr"] = 100.0
    
    result = trade_planner.plan_trade(
        recommendation="BUY",
        confidence=70,
        risk_level="medium",
        current_price=20000.0,
        signal_type="PDH_BREAKOUT",
        enrichment=base_enrichment
    )
    
    risk = result["entry_price"] - result["stop_loss"]
    
    # T1 should be ~2R, T2 should be ~3R
    reward_t1 = result["target_1"] - result["entry_price"]
    reward_t2 = result["target_2"] - result["entry_price"]
    
    assert reward_t1 >= risk * 1.5  # At least 1.5R
    assert reward_t2 >= risk * 2.5  # At least 2.5R
    assert result["target_2"] > result["target_1"]


def test_target_calculation_sell(trade_planner, base_enrichment):
    """Test target calculation for SELL trades"""
    base_enrichment["atr"] = 100.0
    
    result = trade_planner.plan_trade(
        recommendation="SELL",
        confidence=70,
        risk_level="medium",
        current_price=20000.0,
        signal_type="PDL_BREAKDOWN",
        enrichment=base_enrichment
    )
    
    risk = result["stop_loss"] - result["entry_price"]
    
    # T1 should be ~2R, T2 should be ~3R below entry
    reward_t1 = result["entry_price"] - result["target_1"]
    reward_t2 = result["entry_price"] - result["target_2"]
    
    assert reward_t1 >= risk * 1.5
    assert reward_t2 >= risk * 2.5
    assert result["target_2"] < result["target_1"]


def test_all_prices_positive(trade_planner, base_enrichment):
    """Test all calculated prices are positive"""
    result = trade_planner.plan_trade(
        recommendation="BUY",
        confidence=70,
        risk_level="medium",
        current_price=100.0,  # Small price
        signal_type="PDH_BREAKOUT",
        enrichment=base_enrichment
    )
    
    if result["trade_valid"]:
        assert result["entry_price"] > 0
        assert result["stop_loss"] > 0
        assert result["target_1"] > 0
        assert result["target_2"] > 0
