"""
Tests for Agent Orchestrator
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.orchestrator import Orchestrator
from app.core.schemas import AgentResponse


@pytest.fixture
def mock_groq_client():
    return MagicMock()


@pytest.fixture
def orchestrator(mock_groq_client):
    return Orchestrator(groq_client=mock_groq_client)


@pytest.fixture
def sample_candles():
    """Generate sample candle data"""
    return [
        {"timestamp": i, "open": 100 + i, "high": 102 + i, "low": 99 + i, "close": 101 + i, "volume": 1000000}
        for i in range(250)
    ]


@pytest.fixture
def sample_news():
    """Sample news items"""
    return [
        {"headline": "Positive earnings reported", "source": "ET", "published_at": "2026-06-06"},
        {"headline": "FII buying continues", "source": "MC", "published_at": "2026-06-06"}
    ]


@pytest.mark.asyncio
async def test_full_pipeline_success(orchestrator, sample_candles, sample_news):
    """Test complete orchestrator pipeline"""
    
    # Mock agent responses
    with patch.object(orchestrator.technical_agent, 'execute', new_callable=AsyncMock) as mock_tech, \
         patch.object(orchestrator.news_agent, 'execute', new_callable=AsyncMock) as mock_news, \
         patch.object(orchestrator.decision_agent, 'execute', new_callable=AsyncMock) as mock_decision:
        
        mock_tech.return_value = AgentResponse(
            agent_name="technical_analysis",
            success=True,
            reasoning="Bullish breakout",
            confidence=70,
            metadata={"trend_strength": "strong"},
            latency_ms=100
        )
        
        mock_news.return_value = AgentResponse(
            agent_name="news_intelligence",
            success=True,
            reasoning="Positive sentiment",
            confidence=65,
            metadata={"sentiment": "positive", "impact": "medium", "relevance": "relevant"},
            latency_ms=150
        )
        
        mock_decision.return_value = AgentResponse(
            agent_name="decision_maker",
            success=True,
            reasoning="BUY recommendation",
            confidence=72,
            metadata={"recommendation": "BUY", "risk_level": "medium"},
            latency_ms=120
        )
        
        result = await orchestrator.process_signal(
            symbol="NIFTY",
            signal_type="PDH_BREAKOUT",
            signal_data={"price": 19500.0, "volume": 1000000},
            candles=sample_candles,
            news_items=sample_news
        )
        
        assert result["success"] is True
        assert result["symbol"] == "NIFTY"
        assert result["final_recommendation"] == "BUY"
        assert result["confidence"] == 72
        assert "enrichment" in result
        assert result["technical_analysis"] is not None
        assert result["news_analysis"] is not None
        assert result["decision"] is not None
        assert result["trade_plan"] is not None


@pytest.mark.asyncio
async def test_missing_candles_uses_defaults(orchestrator):
    """Test orchestrator handles missing candles gracefully"""
    
    with patch.object(orchestrator.technical_agent, 'execute', new_callable=AsyncMock) as mock_tech, \
         patch.object(orchestrator.news_agent, 'execute', new_callable=AsyncMock) as mock_news, \
         patch.object(orchestrator.decision_agent, 'execute', new_callable=AsyncMock) as mock_decision:
        
        mock_tech.return_value = AgentResponse(
            agent_name="technical_analysis", success=True, reasoning="Test",
            confidence=60, metadata={}, latency_ms=100
        )
        mock_news.return_value = AgentResponse(
            agent_name="news_intelligence", success=True, reasoning="Test",
            confidence=50, metadata={"sentiment": "neutral", "impact": "low", "relevance": "irrelevant"}, latency_ms=100
        )
        mock_decision.return_value = AgentResponse(
            agent_name="decision_maker", success=True, reasoning="Test",
            confidence=55, metadata={"recommendation": "SKIP", "risk_level": "high"}, latency_ms=100
        )
        
        result = await orchestrator.process_signal(
            symbol="NIFTY",
            signal_type="PDH_BREAKOUT",
            signal_data={"price": 19500.0},
            candles=None
        )
        
        assert result["success"] is True
        assert result["enrichment"]["ema_trend"] == "neutral"
        assert result["enrichment"]["rsi"] == 50


@pytest.mark.asyncio
async def test_news_agent_failure_continues(orchestrator, sample_candles):
    """Test orchestrator continues when news agent fails"""
    
    with patch.object(orchestrator.technical_agent, 'execute', new_callable=AsyncMock) as mock_tech, \
         patch.object(orchestrator.news_agent, 'execute', new_callable=AsyncMock) as mock_news, \
         patch.object(orchestrator.decision_agent, 'execute', new_callable=AsyncMock) as mock_decision:
        
        mock_tech.return_value = AgentResponse(
            agent_name="technical_analysis", success=True, reasoning="Test",
            confidence=70, metadata={}, latency_ms=100
        )
        
        # News agent throws exception
        mock_news.side_effect = Exception("News API down")
        
        mock_decision.return_value = AgentResponse(
            agent_name="decision_maker", success=True, reasoning="Test",
            confidence=65, metadata={"recommendation": "BUY", "risk_level": "medium"}, latency_ms=100
        )
        
        result = await orchestrator.process_signal(
            symbol="NIFTY",
            signal_type="PDH_BREAKOUT",
            signal_data={"price": 19500.0},
            candles=sample_candles
        )
        
        # Should succeed with neutral news
        assert result["success"] is True
        assert result["news_analysis"].success is False
        assert result["news_analysis"].metadata["sentiment"] == "neutral"


@pytest.mark.asyncio
async def test_trade_planner_failure_returns_invalid_plan(orchestrator, sample_candles):
    """Test orchestrator handles trade planner failure"""
    
    with patch.object(orchestrator.technical_agent, 'execute', new_callable=AsyncMock) as mock_tech, \
         patch.object(orchestrator.news_agent, 'execute', new_callable=AsyncMock) as mock_news, \
         patch.object(orchestrator.decision_agent, 'execute', new_callable=AsyncMock) as mock_decision, \
         patch.object(orchestrator.trade_planner, 'plan_trade') as mock_planner:
        
        mock_tech.return_value = AgentResponse(
            agent_name="technical_analysis", success=True, reasoning="Test",
            confidence=70, metadata={}, latency_ms=100
        )
        mock_news.return_value = AgentResponse(
            agent_name="news_intelligence", success=True, reasoning="Test",
            confidence=60, metadata={"sentiment": "positive", "impact": "medium", "relevance": "relevant"}, latency_ms=100
        )
        mock_decision.return_value = AgentResponse(
            agent_name="decision_maker", success=True, reasoning="Test",
            confidence=72, metadata={"recommendation": "BUY", "risk_level": "low"}, latency_ms=100
        )
        
        # Trade planner throws exception
        mock_planner.side_effect = Exception("Planner error")
        
        result = await orchestrator.process_signal(
            symbol="NIFTY",
            signal_type="PDH_BREAKOUT",
            signal_data={"price": 19500.0},
            candles=sample_candles
        )
        
        # Should succeed but with invalid trade plan
        assert result["success"] is True
        assert result["trade_plan"]["trade_valid"] is False


@pytest.mark.asyncio
async def test_critical_failure_returns_error(orchestrator):
    """Test orchestrator returns error on critical failure"""
    
    with patch.object(orchestrator.technical_agent, 'execute', new_callable=AsyncMock) as mock_tech:
        # Technical agent fails (critical)
        mock_tech.side_effect = Exception("Critical error")
        
        result = await orchestrator.process_signal(
            symbol="NIFTY",
            signal_type="PDH_BREAKOUT",
            signal_data={"price": 19500.0}
        )
        
        assert result["success"] is False
        assert result["final_recommendation"] == "SKIP"
        assert result["confidence"] == 0
        assert "error" in result


@pytest.mark.asyncio
async def test_skip_recommendation_invalid_trade(orchestrator, sample_candles):
    """Test SKIP recommendation produces invalid trade plan"""
    
    with patch.object(orchestrator.technical_agent, 'execute', new_callable=AsyncMock) as mock_tech, \
         patch.object(orchestrator.news_agent, 'execute', new_callable=AsyncMock) as mock_news, \
         patch.object(orchestrator.decision_agent, 'execute', new_callable=AsyncMock) as mock_decision:
        
        mock_tech.return_value = AgentResponse(
            agent_name="technical_analysis", success=True, reasoning="Test",
            confidence=50, metadata={}, latency_ms=100
        )
        mock_news.return_value = AgentResponse(
            agent_name="news_intelligence", success=True, reasoning="Test",
            confidence=45, metadata={"sentiment": "neutral", "impact": "low", "relevance": "irrelevant"}, latency_ms=100
        )
        mock_decision.return_value = AgentResponse(
            agent_name="decision_maker", success=True, reasoning="Low confidence",
            confidence=40, metadata={"recommendation": "SKIP", "risk_level": "high"}, latency_ms=100
        )
        
        result = await orchestrator.process_signal(
            symbol="NIFTY",
            signal_type="PDH_BREAKOUT",
            signal_data={"price": 19500.0},
            candles=sample_candles
        )
        
        assert result["success"] is True
        assert result["final_recommendation"] == "SKIP"
        assert result["trade_plan"]["trade_valid"] is False


@pytest.mark.asyncio
async def test_latency_tracking(orchestrator, sample_candles):
    """Test total latency is tracked"""
    
    with patch.object(orchestrator.technical_agent, 'execute', new_callable=AsyncMock) as mock_tech, \
         patch.object(orchestrator.news_agent, 'execute', new_callable=AsyncMock) as mock_news, \
         patch.object(orchestrator.decision_agent, 'execute', new_callable=AsyncMock) as mock_decision:
        
        mock_tech.return_value = AgentResponse(
            agent_name="technical_analysis", success=True, reasoning="Test",
            confidence=70, metadata={}, latency_ms=100
        )
        mock_news.return_value = AgentResponse(
            agent_name="news_intelligence", success=True, reasoning="Test",
            confidence=60, metadata={"sentiment": "neutral", "impact": "low", "relevance": "irrelevant"}, latency_ms=100
        )
        mock_decision.return_value = AgentResponse(
            agent_name="decision_maker", success=True, reasoning="Test",
            confidence=65, metadata={"recommendation": "BUY", "risk_level": "medium"}, latency_ms=100
        )
        
        result = await orchestrator.process_signal(
            symbol="NIFTY",
            signal_type="PDH_BREAKOUT",
            signal_data={"price": 19500.0},
            candles=sample_candles
        )
        
        assert result["total_latency_ms"] > 0
        assert isinstance(result["total_latency_ms"], int)
