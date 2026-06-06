"""
Tests for Recommendations API
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from fastapi.testclient import TestClient
from app.main import app
from app.db.models import Recommendation, AgentOutput


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def mock_orchestrator_success():
    """Mock successful orchestrator result"""
    return {
        "symbol": "NIFTY",
        "signal_type": "PDH_BREAKOUT",
        "enrichment": {"ema_trend": "bullish", "rsi": 65, "atr": 50.0},
        "technical_analysis": MagicMock(
            agent_name="technical_analysis",
            success=True,
            reasoning="Bullish breakout",
            confidence=70,
            metadata={"trend_strength": "strong"},
            latency_ms=100,
            tokens_used=200,
            model_used="llama-3.3-70b-versatile"
        ),
        "news_analysis": MagicMock(
            agent_name="news_intelligence",
            success=True,
            reasoning="Positive sentiment",
            confidence=65,
            metadata={"sentiment": "positive", "impact": "medium", "relevance": "relevant"},
            latency_ms=150,
            tokens_used=180,
            model_used="deepseek-r1-distill-llama-70b"
        ),
        "decision": MagicMock(
            agent_name="decision_maker",
            success=True,
            reasoning="BUY recommendation based on analysis",
            confidence=72,
            metadata={"recommendation": "BUY", "risk_level": "medium"},
            latency_ms=120,
            tokens_used=300,
            model_used="deepseek-r1-distill-llama-70b"
        ),
        "trade_plan": {
            "entry_price": 19500.0,
            "stop_loss": 19400.0,
            "target_1": 19700.0,
            "target_2": 19800.0,
            "risk_reward_ratio": 2.5,
            "position_size_pct": 2.4,
            "trade_valid": True
        },
        "final_recommendation": "BUY",
        "confidence": 72,
        "total_latency_ms": 370,
        "success": True
    }


@pytest.fixture
def sample_request():
    """Sample signal request"""
    return {
        "symbol": "NIFTY",
        "signal_type": "PDH_BREAKOUT",
        "signal_data": {
            "price": 19500.0,
            "support": 19450.0,
            "resistance": 19550.0,
            "volume": 1500000,
            "avg_volume": 1000000
        },
        "candles": [
            {"timestamp": i, "open": 19400 + i, "high": 19500 + i, "low": 19350 + i, "close": 19450 + i, "volume": 1000000}
            for i in range(250)
        ],
        "news_items": [
            {"headline": "Positive earnings", "source": "ET", "published_at": "2026-06-06"}
        ]
    }


def test_create_recommendation_success(client, sample_request, mock_orchestrator_success):
    """Test POST /recommendations with successful processing"""
    
    with patch("app.routers.recommendations.Orchestrator") as MockOrchestrator:
        mock_orch = MagicMock()
        mock_orch.process_signal = AsyncMock(return_value=mock_orchestrator_success)
        MockOrchestrator.return_value = mock_orch
        
        with patch("app.routers.recommendations.get_async_db") as mock_db:
            mock_session = MagicMock()
            mock_db.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_db.return_value.__aexit__ = AsyncMock()
            
            # Mock repository operations
            mock_rec = Recommendation(
                id=uuid4(),
                symbol="NIFTY",
                signal_type="PDH_BREAKOUT",
                recommendation="BUY",
                confidence=72,
                reasoning="BUY recommendation based on analysis",
                entry_price=19500.0,
                target_price=19700.0,
                stop_loss=19400.0,
                metadata_json={}
            )
            
            with patch("app.routers.recommendations.RecommendationRepository") as MockRecRepo, \
                 patch("app.routers.recommendations.AgentOutputRepository") as MockAgentRepo:
                
                mock_rec_repo = MagicMock()
                mock_rec_repo.create = AsyncMock(return_value=mock_rec)
                mock_rec_repo.commit = AsyncMock()
                MockRecRepo.return_value = mock_rec_repo
                
                mock_agent_repo = MagicMock()
                mock_agent_repo.create = AsyncMock(return_value=MagicMock(id=uuid4()))
                MockAgentRepo.return_value = mock_agent_repo
                
                response = client.post("/recommendations", json=sample_request)
    
    assert response.status_code == 201
    data = response.json()
    assert data["recommendation"]["symbol"] == "NIFTY"
    assert data["recommendation"]["recommendation"] == "BUY"
    assert data["trade_plan"]["trade_valid"] is True


def test_create_recommendation_orchestrator_failure(client, sample_request):
    """Test POST /recommendations with orchestrator failure"""
    
    with patch("app.routers.recommendations.Orchestrator") as MockOrchestrator:
        mock_orch = MagicMock()
        mock_orch.process_signal = AsyncMock(return_value={
            "success": False,
            "error": "Processing failed"
        })
        MockOrchestrator.return_value = mock_orch
        
        response = client.post("/recommendations", json=sample_request)
    
    assert response.status_code == 500


def test_list_recommendations(client):
    """Test GET /recommendations"""
    
    with patch("app.routers.recommendations.get_async_db") as mock_db:
        mock_session = MagicMock()
        mock_db.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_db.return_value.__aexit__ = AsyncMock()
        
        mock_recs = [
            Recommendation(
                id=uuid4(),
                symbol="NIFTY",
                signal_type="PDH_BREAKOUT",
                recommendation="BUY",
                confidence=70,
                reasoning="Test",
                metadata_json={}
            )
        ]
        
        with patch("app.routers.recommendations.RecommendationRepository") as MockRecRepo:
            mock_rec_repo = MagicMock()
            mock_rec_repo.get_latest = AsyncMock(return_value=mock_recs)
            MockRecRepo.return_value = mock_rec_repo
            
            response = client.get("/recommendations")
    
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_get_recommendation_by_id(client):
    """Test GET /recommendations/{id}"""
    
    rec_id = uuid4()
    
    with patch("app.routers.recommendations.get_async_db") as mock_db:
        mock_session = MagicMock()
        mock_db.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_db.return_value.__aexit__ = AsyncMock()
        
        mock_rec = Recommendation(
            id=rec_id,
            symbol="NIFTY",
            signal_type="PDH_BREAKOUT",
            recommendation="BUY",
            confidence=72,
            reasoning="Test",
            entry_price=19500.0,
            target_price=19700.0,
            stop_loss=19400.0,
            metadata_json={"trade_plan": {"trade_valid": True}}
        )
        
        with patch("app.routers.recommendations.RecommendationRepository") as MockRecRepo, \
             patch("app.routers.recommendations.AgentOutputRepository") as MockAgentRepo:
            
            mock_rec_repo = MagicMock()
            mock_rec_repo.get_by_id = AsyncMock(return_value=mock_rec)
            MockRecRepo.return_value = mock_rec_repo
            
            mock_agent_repo = MagicMock()
            mock_agent_repo.get_by_recommendation = AsyncMock(return_value=[])
            MockAgentRepo.return_value = mock_agent_repo
            
            response = client.get(f"/recommendations/{rec_id}")
    
    assert response.status_code == 200
    data = response.json()
    assert data["recommendation"]["symbol"] == "NIFTY"


def test_get_recommendation_not_found(client):
    """Test GET /recommendations/{id} with non-existent ID"""
    
    rec_id = uuid4()
    
    with patch("app.routers.recommendations.get_async_db") as mock_db:
        mock_session = MagicMock()
        mock_db.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_db.return_value.__aexit__ = AsyncMock()
        
        with patch("app.routers.recommendations.RecommendationRepository") as MockRecRepo:
            mock_rec_repo = MagicMock()
            mock_rec_repo.get_by_id = AsyncMock(return_value=None)
            MockRecRepo.return_value = mock_rec_repo
            
            response = client.get(f"/recommendations/{rec_id}")
    
    assert response.status_code == 404


def test_list_recommendations_with_filters(client):
    """Test GET /recommendations with filters"""
    
    with patch("app.routers.recommendations.get_async_db") as mock_db:
        mock_session = MagicMock()
        mock_db.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_db.return_value.__aexit__ = AsyncMock()
        
        mock_recs = [
            Recommendation(
                id=uuid4(),
                symbol="NIFTY",
                signal_type="PDH_BREAKOUT",
                recommendation="BUY",
                confidence=70,
                reasoning="Test",
                metadata_json={}
            )
        ]
        
        with patch("app.routers.recommendations.RecommendationRepository") as MockRecRepo:
            mock_rec_repo = MagicMock()
            mock_rec_repo.get_latest = AsyncMock(return_value=mock_recs)
            MockRecRepo.return_value = mock_rec_repo
            
            response = client.get("/recommendations?symbol=NIFTY&limit=10")
    
    assert response.status_code == 200
