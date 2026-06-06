"""Tests for Technical Analysis Agent"""

import pytest
from unittest.mock import AsyncMock, Mock

from app.agents.technical_agent import TechnicalAgent
from app.core.schemas import AgentRequest


@pytest.fixture
def mock_llm_client():
    """Mock Groq LLM client"""
    client = Mock()
    client.generate = AsyncMock(return_value={
        "content": '{"pattern": "breakout", "trend_strength": "strong", "volume_confirmation": "confirmed", "level_strength": "strong", "key_risks": [], "reasoning": "Strong breakout with volume", "confidence": 75}',
        "tokens_total": 150,
        "model": "llama-3.3-70b-versatile"
    })
    return client


@pytest.fixture
def technical_agent(mock_llm_client):
    """Technical agent instance"""
    return TechnicalAgent(llm_client=mock_llm_client)


@pytest.mark.asyncio
async def test_technical_agent_execution(technical_agent):
    """Test agent executes successfully"""
    request = AgentRequest(
        symbol="RELIANCE",
        signal_type="PDH_BREAKOUT",
        signal_data={
            "price": 2500,
            "support": 2450,
            "resistance": 2550,
            "volume": 1500000,
            "avg_volume": 1000000
        }
    )
    
    response = await technical_agent.execute(request)
    
    assert response.success is True
    assert response.agent_name == "technical_analysis"
    assert response.confidence >= 0
    assert response.confidence <= 100
    assert len(response.reasoning) > 0


@pytest.mark.asyncio
async def test_technical_agent_deterministic_fallback(technical_agent, mock_llm_client):
    """Test fallback to deterministic analysis on LLM failure"""
    mock_llm_client.generate.side_effect = Exception("LLM failed")
    
    request = AgentRequest(
        symbol="INFY",
        signal_type="PDL_BREAKDOWN",
        signal_data={
            "price": 1400,
            "volume": 800000,
            "avg_volume": 1000000
        }
    )
    
    response = await technical_agent.execute(request)
    
    assert response.success is True
    assert response.confidence > 0
    assert "fallback" in response.metadata


@pytest.mark.asyncio
async def test_technical_agent_confidence_bounds(technical_agent):
    """Test confidence is always within valid bounds"""
    request = AgentRequest(
        symbol="TCS",
        signal_type="RANGE_BREAKOUT",
        signal_data={"price": 3500, "volume": 500000, "avg_volume": 600000}
    )
    
    response = await technical_agent.execute(request)
    
    assert 0 <= response.confidence <= 100


@pytest.mark.asyncio
async def test_technical_agent_unknown_signal_type(technical_agent):
    """Test agent handles unknown signal types gracefully"""
    request = AgentRequest(
        symbol="HDFC",
        signal_type="UNKNOWN_SIGNAL",
        signal_data={"price": 1600}
    )
    
    response = await technical_agent.execute(request)
    
    assert response.success is True
    assert response.confidence > 0
