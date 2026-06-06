"""
Tests for Decision Agent
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from app.agents.decision_agent import DecisionAgent
from app.core.schemas import AgentRequest, AgentResponse


@pytest.fixture
def mock_groq_client():
    """Mock Groq LLM client"""
    client = MagicMock()
    client.generate = AsyncMock()
    return client


@pytest.fixture
def decision_agent(mock_groq_client):
    """Create DecisionAgent instance"""
    return DecisionAgent(llm_client=mock_groq_client)


@pytest.fixture
def base_request():
    """Base agent request"""
    return AgentRequest(
        symbol="NIFTY",
        signal_type="PDH_BREAKOUT",
        signal_data={"price": 19500.0},
        context={}
    )


@pytest.fixture
def bullish_technical():
    """Bullish technical analysis output"""
    return AgentResponse(
        agent_name="technical_analysis",
        success=True,
        reasoning="Strong bullish breakout with volume confirmation",
        confidence=75,
        metadata={
            "trend_strength": "strong",
            "volume_confirmation": "confirmed",
            "pattern": "breakout"
        },
        latency_ms=150,
        tokens_used=200,
        model_used="llama-3.3-70b-versatile"
    )


@pytest.fixture
def bearish_technical():
    """Bearish technical analysis output"""
    return AgentResponse(
        agent_name="technical_analysis",
        success=True,
        reasoning="Bearish breakdown below support",
        confidence=70,
        metadata={
            "trend_strength": "strong",
            "volume_confirmation": "confirmed",
            "pattern": "breakdown"
        },
        latency_ms=140,
        tokens_used=180,
        model_used="llama-3.3-70b-versatile"
    )


@pytest.fixture
def positive_news():
    """Positive news sentiment output"""
    return AgentResponse(
        agent_name="news_intelligence",
        success=True,
        reasoning="Positive earnings and management guidance",
        confidence=65,
        metadata={
            "sentiment": "positive",
            "impact": "high",
            "relevance": "relevant"
        },
        latency_ms=200,
        tokens_used=150,
        model_used="deepseek-r1-distill-llama-70b"
    )


@pytest.fixture
def negative_news():
    """Negative news sentiment output"""
    return AgentResponse(
        agent_name="news_intelligence",
        success=True,
        reasoning="Regulatory concerns and analyst downgrades",
        confidence=70,
        metadata={
            "sentiment": "negative",
            "impact": "high",
            "relevance": "relevant"
        },
        latency_ms=210,
        tokens_used=160,
        model_used="deepseek-r1-distill-llama-70b"
    )


@pytest.fixture
def neutral_news():
    """Neutral news sentiment output"""
    return AgentResponse(
        agent_name="news_intelligence",
        success=True,
        reasoning="Mixed news with no clear direction",
        confidence=50,
        metadata={
            "sentiment": "neutral",
            "impact": "medium",
            "relevance": "partially_relevant"
        },
        latency_ms=180,
        tokens_used=140,
        model_used="llama-3.3-70b-versatile"
    )


@pytest.fixture
def enrichment_bullish():
    """Bullish enrichment data"""
    return {
        "ema_trend": "bullish",
        "rsi": 65,
        "rsi_signal": "neutral",
        "macd_trend": "bullish",
        "volume_signal": "high"
    }


@pytest.fixture
def enrichment_bearish():
    """Bearish enrichment data"""
    return {
        "ema_trend": "bearish",
        "rsi": 35,
        "rsi_signal": "neutral",
        "macd_trend": "bearish",
        "volume_signal": "high"
    }


@pytest.mark.asyncio
async def test_buy_recommendation_bullish_technical_positive_news(
    decision_agent,
    base_request,
    bullish_technical,
    positive_news,
    enrichment_bullish
):
    """Test BUY recommendation with aligned bullish signals"""
    base_request.context = {
        "technical_agent": bullish_technical,
        "news_agent": positive_news,
        "enrichment": enrichment_bullish
    }
    
    result = await decision_agent.analyze(base_request)
    
    assert result["recommendation"] == "BUY"
    assert result["confidence"] >= 55
    assert "metadata" in result
    assert result["metadata"]["risk_level"] in ["low", "medium"]


@pytest.mark.asyncio
async def test_sell_recommendation_bearish_technical_negative_news(
    decision_agent,
    base_request,
    bearish_technical,
    negative_news,
    enrichment_bearish
):
    """Test SELL recommendation with aligned bearish signals"""
    base_request.signal_type = "PDL_BREAKDOWN"
    base_request.context = {
        "technical_agent": bearish_technical,
        "news_agent": negative_news,
        "enrichment": enrichment_bearish
    }
    
    result = await decision_agent.analyze(base_request)
    
    assert result["recommendation"] == "SELL"
    assert result["confidence"] >= 55
    assert result["metadata"]["risk_level"] in ["low", "medium"]


@pytest.mark.asyncio
async def test_skip_conflicting_signals_bullish_tech_negative_news(
    decision_agent,
    base_request,
    bullish_technical,
    negative_news,
    enrichment_bullish
):
    """Test SKIP when bullish technical conflicts with negative news"""
    base_request.context = {
        "technical_agent": bullish_technical,
        "news_agent": negative_news,
        "enrichment": enrichment_bullish
    }
    
    result = await decision_agent.analyze(base_request)
    
    assert result["recommendation"] in ["SKIP", "HOLD"]
    assert "conflicts" in result["metadata"]


@pytest.mark.asyncio
async def test_skip_conflicting_signals_bearish_tech_positive_news(
    decision_agent,
    base_request,
    bearish_technical,
    positive_news,
    enrichment_bearish
):
    """Test SKIP when bearish technical conflicts with positive news"""
    base_request.signal_type = "PDL_BREAKDOWN"
    base_request.context = {
        "technical_agent": bearish_technical,
        "news_agent": positive_news,
        "enrichment": enrichment_bearish
    }
    
    result = await decision_agent.analyze(base_request)
    
    assert result["recommendation"] in ["SKIP", "HOLD"]


@pytest.mark.asyncio
async def test_hold_moderate_confidence(
    decision_agent,
    base_request,
    bullish_technical,
    neutral_news,
    enrichment_bullish
):
    """Test HOLD recommendation with moderate confidence"""
    # Lower technical confidence
    bullish_technical.confidence = 55
    
    base_request.context = {
        "technical_agent": bullish_technical,
        "news_agent": neutral_news,
        "enrichment": enrichment_bullish
    }
    
    result = await decision_agent.analyze(base_request)
    
    assert result["recommendation"] in ["HOLD", "SKIP", "BUY"]
    assert result["confidence"] <= 70


@pytest.mark.asyncio
async def test_missing_news_uses_defaults(
    decision_agent,
    base_request,
    bullish_technical,
    enrichment_bullish
):
    """Test decision with missing news agent output"""
    base_request.context = {
        "technical_agent": bullish_technical,
        "enrichment": enrichment_bullish
    }
    
    result = await decision_agent.analyze(base_request)
    
    # Should still make decision based on technical
    assert result["recommendation"] in ["BUY", "HOLD", "SKIP"]
    assert result["confidence"] >= 0


@pytest.mark.asyncio
async def test_missing_technical_returns_error(
    decision_agent,
    base_request,
    positive_news
):
    """Test error response when technical analysis is missing"""
    base_request.context = {
        "news_agent": positive_news
    }
    
    result = await decision_agent.analyze(base_request)
    
    assert result["recommendation"] == "SKIP"
    assert result["confidence"] == 0
    assert "error" in result["metadata"]


@pytest.mark.asyncio
async def test_llm_failure_uses_deterministic_fallback(
    decision_agent,
    mock_groq_client,
    base_request,
    bullish_technical,
    positive_news,
    enrichment_bullish
):
    """Test deterministic fallback when LLM fails"""
    # Mock LLM to raise exception
    mock_groq_client.generate.side_effect = Exception("LLM timeout")
    
    base_request.context = {
        "technical_agent": bullish_technical,
        "news_agent": positive_news,
        "enrichment": enrichment_bullish
    }
    
    result = await decision_agent.analyze(base_request)
    
    # Should still return valid recommendation
    assert result["recommendation"] in ["BUY", "SELL", "HOLD", "SKIP"]
    assert result["confidence"] >= 0
    assert result["metadata"].get("fallback") is True


@pytest.mark.asyncio
async def test_deterministic_buy_logic(
    decision_agent,
    base_request,
    bullish_technical,
    neutral_news,
    enrichment_bullish,
    mock_groq_client
):
    """Test deterministic BUY logic directly"""
    # Force deterministic path
    mock_groq_client.generate.side_effect = Exception("Force fallback")
    
    bullish_technical.confidence = 70
    base_request.context = {
        "technical_agent": bullish_technical,
        "news_agent": neutral_news,
        "enrichment": enrichment_bullish
    }
    
    result = await decision_agent.analyze(base_request)
    
    assert result["recommendation"] == "BUY"
    assert result["confidence"] >= 55


@pytest.mark.asyncio
async def test_deterministic_sell_logic(
    decision_agent,
    base_request,
    bearish_technical,
    neutral_news,
    enrichment_bearish,
    mock_groq_client
):
    """Test deterministic SELL logic directly"""
    # Force deterministic path
    mock_groq_client.generate.side_effect = Exception("Force fallback")
    
    base_request.signal_type = "PDL_BREAKDOWN"
    bearish_technical.confidence = 70
    base_request.context = {
        "technical_agent": bearish_technical,
        "news_agent": neutral_news,
        "enrichment": enrichment_bearish
    }
    
    result = await decision_agent.analyze(base_request)
    
    assert result["recommendation"] == "SELL"
    assert result["confidence"] >= 55


@pytest.mark.asyncio
async def test_low_confidence_skip(
    decision_agent,
    base_request,
    bullish_technical,
    neutral_news,
    enrichment_bullish,
    mock_groq_client
):
    """Test SKIP with low confidence"""
    # Force deterministic path
    mock_groq_client.generate.side_effect = Exception("Force fallback")
    
    # Low confidence technical
    bullish_technical.confidence = 40
    neutral_news.confidence = 35
    
    base_request.context = {
        "technical_agent": bullish_technical,
        "news_agent": neutral_news,
        "enrichment": enrichment_bullish
    }
    
    result = await decision_agent.analyze(base_request)
    
    assert result["recommendation"] == "SKIP"
    assert result["confidence"] <= 50


@pytest.mark.asyncio
async def test_confidence_clamping(
    decision_agent,
    base_request,
    bullish_technical,
    positive_news,
    enrichment_bullish,
    mock_groq_client
):
    """Test confidence is clamped to 0-100 range"""
    # Mock invalid LLM response
    mock_groq_client.generate.return_value = {
        "content": '{"recommendation": "BUY", "confidence": 150, "reasoning": "Test", "risk_level": "low", "key_factors": [], "conflicts": ""}',
        "tokens_total": 100,
        "model": "test"
    }
    
    base_request.context = {
        "technical_agent": bullish_technical,
        "news_agent": positive_news,
        "enrichment": enrichment_bullish
    }
    
    result = await decision_agent.analyze(base_request)
    
    assert 0 <= result["confidence"] <= 100


@pytest.mark.asyncio
async def test_invalid_recommendation_defaults_to_skip(
    decision_agent,
    base_request,
    bullish_technical,
    positive_news,
    enrichment_bullish,
    mock_groq_client
):
    """Test invalid recommendation defaults to SKIP"""
    # Mock invalid LLM response
    mock_groq_client.generate.return_value = {
        "content": '{"recommendation": "MAYBE", "confidence": 60, "reasoning": "Test", "risk_level": "low", "key_factors": [], "conflicts": ""}',
        "tokens_total": 100,
        "model": "test"
    }
    
    base_request.context = {
        "technical_agent": bullish_technical,
        "news_agent": positive_news,
        "enrichment": enrichment_bullish
    }
    
    result = await decision_agent.analyze(base_request)
    
    assert result["recommendation"] == "SKIP"
