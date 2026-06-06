"""Tests for News Intelligence Agent"""

import pytest
from unittest.mock import AsyncMock, Mock

from app.agents.news_agent import NewsAgent
from app.core.schemas import AgentRequest


@pytest.fixture
def mock_llm_client():
    """Mock Groq LLM client"""
    client = Mock()
    client.generate = AsyncMock(return_value={
        "content": '{"sentiment": "positive", "impact": "high", "relevance": "relevant", "key_signals": ["earnings beat"], "risks": [], "reasoning": "Strong earnings report", "confidence": 80}',
        "tokens_total": 120,
        "model": "deepseek-r1-distill-llama-70b"
    })
    return client


@pytest.fixture
def news_agent(mock_llm_client):
    """News agent instance"""
    return NewsAgent(llm_client=mock_llm_client)


@pytest.mark.asyncio
async def test_news_agent_positive_sentiment(news_agent):
    """Test agent with positive news"""
    request = AgentRequest(
        symbol="RELIANCE",
        signal_type="PDH_BREAKOUT",
        context={
            "news": [
                {"headline": "Reliance posts record quarterly profit", "source": "ET"},
                {"headline": "Strong growth in retail segment", "source": "MC"}
            ]
        }
    )
    
    response = await news_agent.execute(request)
    
    assert response.success is True
    assert response.agent_name == "news_intelligence"
    assert response.confidence > 0
    assert response.metadata.get("sentiment") in ["positive", "neutral", "negative"]


@pytest.mark.asyncio
async def test_news_agent_negative_sentiment(news_agent, mock_llm_client):
    """Test agent with negative news"""
    mock_llm_client.generate = AsyncMock(return_value={
        "content": '{"sentiment": "negative", "impact": "medium", "relevance": "relevant", "key_signals": ["regulatory concerns"], "risks": ["compliance issues"], "reasoning": "Regulatory scrutiny", "confidence": 70}',
        "tokens_total": 100,
        "model": "deepseek-r1-distill-llama-70b"
    })
    
    request = AgentRequest(
        symbol="INFY",
        signal_type="PDL_BREAKDOWN",
        context={
            "news": [
                {"headline": "Infosys faces regulatory scrutiny", "source": "ET"}
            ]
        }
    )
    
    response = await news_agent.execute(request)
    
    assert response.success is True
    assert response.metadata.get("sentiment") == "negative"


@pytest.mark.asyncio
async def test_news_agent_no_news(news_agent):
    """Test agent with no news available"""
    request = AgentRequest(
        symbol="TCS",
        signal_type="RANGE_BREAKOUT",
        context={}
    )
    
    response = await news_agent.execute(request)
    
    assert response.success is True
    assert response.confidence <= 50  # Low confidence with no news
    assert response.metadata.get("sentiment") == "neutral"


@pytest.mark.asyncio
async def test_news_agent_mixed_sentiment(news_agent):
    """Test agent with mixed news"""
    request = AgentRequest(
        symbol="HDFC",
        signal_type="PDH_BREAKOUT",
        context={
            "news": [
                {"headline": "HDFC reports strong profit growth", "source": "ET"},
                {"headline": "Concerns over loan quality", "source": "MC"},
                {"headline": "Market share gains in retail", "source": "YF"}
            ]
        }
    )
    
    response = await news_agent.execute(request)
    
    assert response.success is True
    assert response.confidence > 0


@pytest.mark.asyncio
async def test_news_agent_llm_failure_fallback(news_agent, mock_llm_client):
    """Test fallback to deterministic analysis on LLM failure"""
    mock_llm_client.generate.side_effect = Exception("LLM failed")
    
    request = AgentRequest(
        symbol="WIPRO",
        signal_type="PDL_REJECTION",
        context={
            "news": [
                {"headline": "Wipro announces strong growth outlook", "source": "ET"}
            ]
        }
    )
    
    response = await news_agent.execute(request)
    
    assert response.success is True
    assert "fallback" in response.metadata
    assert response.confidence > 0


@pytest.mark.asyncio
async def test_news_agent_confidence_bounds(news_agent):
    """Test confidence is within valid bounds"""
    request = AgentRequest(
        symbol="BAJAJ",
        signal_type="TREND_CONTINUATION",
        context={
            "news": [
                {"headline": "Bajaj Auto reports record sales", "source": "MC"}
            ]
        }
    )
    
    response = await news_agent.execute(request)
    
    assert 0 <= response.confidence <= 100


@pytest.mark.asyncio
async def test_news_agent_empty_headlines(news_agent):
    """Test agent handles empty headlines gracefully"""
    request = AgentRequest(
        symbol="MARUTI",
        signal_type="PDH_BREAKOUT",
        context={
            "news": []
        }
    )
    
    response = await news_agent.execute(request)
    
    assert response.success is True
    assert response.metadata.get("sentiment") == "neutral"
