"""
Tests for Production Hardening

Covers rate limiting, validation, error handling, correlation, and security.
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from uuid import uuid4
import time

from app.main import app
from app.middleware import RateLimiter, CorrelationMiddleware, SecurityHeadersMiddleware
from app.core.schemas import SignalRequest
from app.db.models import Recommendation


@pytest.fixture
def client():
    """Test client"""
    return TestClient(app)


@pytest.fixture
def mock_orchestrator_result():
    """Mock orchestrator successful result"""
    return {
        "symbol": "NIFTY",
        "signal_type": "PDH_BREAKOUT",
        "enrichment": {"rsi": 65},
        "technical_analysis": MagicMock(
            agent_name="technical_analysis",
            success=True,
            reasoning="Bullish",
            confidence=70,
            metadata={},
            latency_ms=100,
            tokens_used=200,
            llm_model="llama-3.3-70b-versatile"
        ),
        "news_analysis": MagicMock(
            agent_name="news_intelligence",
            success=True,
            reasoning="Positive",
            confidence=65,
            metadata={},
            latency_ms=150,
            tokens_used=180,
            llm_model="llama-3.3-70b-versatile"
        ),
        "decision": MagicMock(
            agent_name="decision_maker",
            success=True,
            reasoning="BUY recommendation",
            confidence=72,
            metadata={},
            latency_ms=120,
            tokens_used=300,
            llm_model="llama-3.3-70b-versatile"
        ),
        "trade_plan": {
            "entry_price": 22000.0,
            "stop_loss": 21900.0,
            "target_1": 22200.0,
            "target_2": 22300.0,
            "risk_reward_ratio": 2.0,
            "position_size_pct": 2.0,
            "trade_valid": True
        },
        "final_recommendation": "BUY",
        "confidence": 72,
        "total_latency_ms": 370,
        "success": True
    }


@pytest.fixture
def mock_redis():
    """Mock Redis for rate limiting"""
    from unittest.mock import MagicMock
    mock = MagicMock()
    mock.pipeline.return_value = mock
    mock.get.return_value = None
    mock.ttl.return_value = 60
    mock.execute.return_value = [None, 60]
    mock.incr.return_value = 1
    mock.expire.return_value = True
    return mock


@pytest.fixture
def mock_recommendation():
    """Mock recommendation database object"""
    from datetime import datetime, timezone
    return Recommendation(
        id=uuid4(),
        symbol="NIFTY",
        signal_type="PDH_BREAKOUT",
        recommendation="BUY",
        confidence=72,
        reasoning="BUY recommendation",
        entry_price=22000.0,
        target_price=22200.0,
        stop_loss=21900.0,
        metadata_json={},
        created_at=datetime.now(timezone.utc)
    )


@pytest.fixture
def mock_agent_output(mock_recommendation):
    """Mock agent output database object"""
    from datetime import datetime, timezone
    from app.db.models import AgentOutput
    return AgentOutput(
        id=uuid4(),
        recommendation_id=mock_recommendation.id,
        agent_name="technical_analysis",
        reasoning="Bullish analysis",
        confidence=70,
        metadata_json={"trend": "up"},
        latency_ms=100,
        tokens_used=200,
        llm_model="llama-3.3-70b-versatile",
        created_at=datetime.now(timezone.utc)
    )


class TestRateLimiting:
    """Rate limiting tests"""
    
    def test_rate_limit_enforced(self, client, mock_orchestrator_result, mock_recommendation, mock_redis, mock_agent_output):
        """Should enforce rate limits on recommendations endpoint"""
        with patch("app.routers.recommendations.Orchestrator") as MockOrch, \
             patch("app.routers.recommendations.RecommendationRepository") as MockRecRepo, \
             patch("app.routers.recommendations.AgentOutputRepository") as MockAgentRepo, \
             patch("app.integrations.redis_client.get_redis_sync", return_value=mock_redis):
            
            # Mock orchestrator
            mock_orch = MagicMock()
            mock_orch.process_signal = AsyncMock(return_value=mock_orchestrator_result)
            MockOrch.return_value = mock_orch
            
            # Mock repositories
            mock_rec_repo = MagicMock()
            mock_rec_repo.create = AsyncMock(return_value=mock_recommendation)
            MockRecRepo.return_value = mock_rec_repo
            
            mock_agent_repo = MagicMock()
            mock_agent_repo.create = AsyncMock(return_value=mock_agent_output)
            MockAgentRepo.return_value = mock_agent_repo
            
            # Configure Redis mock for rate limiting
            call_count = [0]
            def side_effect_execute(*args):
                call_count[0] += 1
                if call_count[0] % 2 == 1:  # get and ttl calls
                    count = min(call_count[0] // 2, 30)
                    return [str(count) if count > 0 else None, 60]
                else:  # incr and expire calls
                    return [call_count[0] // 2, True]
            
            mock_redis.execute.side_effect = side_effect_execute
            
            # Make requests up to limit (30)
            for i in range(30):
                response = client.post(
                    "/recommendations",
                    json={
                        "symbol": "NIFTY",
                        "signal_type": "PDH_BREAKOUT",
                        "signal_data": {"price": 22000}
                    }
                )
                assert response.status_code != 429, f"Request {i+1} was rate limited prematurely"
            
            # 31st request should be rate limited
            response = client.post(
                "/recommendations",
                json={
                    "symbol": "NIFTY",
                    "signal_type": "PDH_BREAKOUT",
                    "signal_data": {"price": 22000}
                }
            )
            assert response.status_code == 429
            data = response.json()
            assert data["code"] == "RATE_LIMIT_EXCEEDED"
            assert "retry_after" in data["details"]
    
    def test_rate_limit_per_client(self, client, mock_orchestrator_result, mock_recommendation, mock_redis, mock_agent_output):
        """Should rate limit per client (IP/API key)"""
        with patch("app.routers.recommendations.Orchestrator") as MockOrch, \
             patch("app.routers.recommendations.RecommendationRepository") as MockRecRepo, \
             patch("app.routers.recommendations.AgentOutputRepository") as MockAgentRepo, \
             patch("app.integrations.redis_client.get_redis_sync", return_value=mock_redis):
            
            mock_orch = MagicMock()
            mock_orch.process_signal = AsyncMock(return_value=mock_orchestrator_result)
            MockOrch.return_value = mock_orch
            
            mock_rec_repo = MagicMock()
            mock_rec_repo.create = AsyncMock(return_value=mock_recommendation)
            MockRecRepo.return_value = mock_rec_repo
            
            mock_agent_repo = MagicMock()
            mock_agent_repo.create = AsyncMock(return_value=mock_agent_output)
            MockAgentRepo.return_value = mock_agent_repo
            
            # Client 1 - exhaust rate limit
            call_count = [0]
            def side_effect_client1(*args):
                call_count[0] += 1
                if call_count[0] % 2 == 1:
                    count = min(call_count[0] // 2, 31)
                    return [str(count) if count > 0 else None, 60]
                else:
                    return [call_count[0] // 2, True]
            
            mock_redis.execute.side_effect = side_effect_client1
            
            for _ in range(30):
                client.post(
                    "/recommendations",
                    json={"symbol": "NIFTY", "signal_type": "PDH_BREAKOUT", "signal_data": {"price": 22000}}
                )
            
            # Client 1 rate limited
            response = client.post(
                "/recommendations",
                json={"symbol": "NIFTY", "signal_type": "PDH_BREAKOUT", "signal_data": {"price": 22000}}
            )
            assert response.status_code == 429
            
            # Client 2 (different API key) - reset counter
            mock_redis.execute.side_effect = None
            mock_redis.execute.return_value = [None, 60]
            
            response = client.post(
                "/recommendations",
                json={"symbol": "NIFTY", "signal_type": "PDH_BREAKOUT", "signal_data": {"price": 22000}},
                headers={"X-API-Key": "different-key"}
            )
            assert response.status_code != 429
    
    def test_rate_limit_retry_after_header(self, client, mock_orchestrator_result, mock_recommendation, mock_redis, mock_agent_output):
        """Should include Retry-After header"""
        with patch("app.routers.recommendations.Orchestrator") as MockOrch, \
             patch("app.routers.recommendations.RecommendationRepository") as MockRecRepo, \
             patch("app.routers.recommendations.AgentOutputRepository") as MockAgentRepo, \
             patch("app.integrations.redis_client.get_redis_sync", return_value=mock_redis):
            
            mock_orch = MagicMock()
            mock_orch.process_signal = AsyncMock(return_value=mock_orchestrator_result)
            MockOrch.return_value = mock_orch
            
            mock_rec_repo = MagicMock()
            mock_rec_repo.create = AsyncMock(return_value=mock_recommendation)
            MockRecRepo.return_value = mock_rec_repo
            
            mock_agent_repo = MagicMock()
            mock_agent_repo.create = AsyncMock(return_value=mock_agent_output)
            MockAgentRepo.return_value = mock_agent_repo
            
            # Simulate already at limit
            mock_redis.execute.return_value = ["30", 45]
            
            response = client.post(
                "/recommendations",
                json={"symbol": "NIFTY", "signal_type": "PDH_BREAKOUT", "signal_data": {"price": 22000}}
            )
            assert response.status_code == 429
            assert "Retry-After" in response.headers


class TestRequestValidation:
    """Validation tests"""
    
    def test_invalid_signal_type(self, client):
        """Should reject invalid signal types"""
        response = client.post(
            "/recommendations",
            json={
                "symbol": "NIFTY",
                "signal_type": "INVALID_SIGNAL",
                "signal_data": {"price": 22000}
            }
        )
        assert response.status_code == 422
        assert response.json()["code"] == "VALIDATION_ERROR"
    
    def test_negative_price(self, client):
        """Should reject negative prices"""
        response = client.post(
            "/recommendations",
            json={
                "symbol": "NIFTY",
                "signal_type": "PDH_BREAKOUT",
                "signal_data": {"price": -100}
            }
        )
        assert response.status_code == 422
        assert response.json()["code"] == "VALIDATION_ERROR"
    
    def test_invalid_confidence(self, client):
        """Should reject invalid confidence values"""
        response = client.post(
            "/recommendations",
            json={
                "symbol": "NIFTY",
                "signal_type": "PDH_BREAKOUT",
                "signal_data": {"price": 22000, "confidence": 150}
            }
        )
        assert response.status_code == 422
    
    def test_missing_signal_data(self, client):
        """Should reject missing signal_data"""
        response = client.post(
            "/recommendations",
            json={
                "symbol": "NIFTY",
                "signal_type": "PDH_BREAKOUT"
            }
        )
        assert response.status_code == 422
    
    def test_invalid_candles(self, client):
        """Should validate candle OHLC relationship"""
        response = client.post(
            "/recommendations",
            json={
                "symbol": "NIFTY",
                "signal_type": "PDH_BREAKOUT",
                "signal_data": {"price": 22000},
                "candles": [
                    {
                        "open": 100,
                        "high": 90,  # High < Open (invalid)
                        "low": 80,
                        "close": 95,
                        "volume": 1000
                    }
                ]
            }
        )
        assert response.status_code == 422
    
    def test_too_many_candles(self, client):
        """Should reject excessive candles"""
        candles = [
            {"open": 100, "high": 105, "low": 95, "close": 102, "volume": 1000}
            for _ in range(1001)
        ]
        response = client.post(
            "/recommendations",
            json={
                "symbol": "NIFTY",
                "signal_type": "PDH_BREAKOUT",
                "signal_data": {"price": 22000},
                "candles": candles
            }
        )
        assert response.status_code == 422


class TestErrorResponses:
    """Error response structure tests"""
    
    def test_validation_error_structure(self, client):
        """Should return structured validation errors"""
        response = client.post(
            "/recommendations",
            json={
                "symbol": "NIFTY",
                "signal_type": "INVALID"
            }
        )
        data = response.json()
        assert "error" in data
        assert "code" in data
        assert "details" in data
        assert data["code"] == "VALIDATION_ERROR"
    
    def test_rate_limit_error_structure(self, client, mock_orchestrator_result, mock_recommendation, mock_redis, mock_agent_output):
        """Should return structured rate limit errors"""
        with patch("app.routers.recommendations.Orchestrator") as MockOrch, \
             patch("app.routers.recommendations.RecommendationRepository") as MockRecRepo, \
             patch("app.routers.recommendations.AgentOutputRepository") as MockAgentRepo, \
             patch("app.integrations.redis_client.get_redis_sync", return_value=mock_redis):
            
            mock_orch = MagicMock()
            mock_orch.process_signal = AsyncMock(return_value=mock_orchestrator_result)
            MockOrch.return_value = mock_orch
            
            mock_rec_repo = MagicMock()
            mock_rec_repo.create = AsyncMock(return_value=mock_recommendation)
            MockRecRepo.return_value = mock_rec_repo
            
            mock_agent_repo = MagicMock()
            mock_agent_repo.create = AsyncMock(return_value=mock_agent_output)
            MockAgentRepo.return_value = mock_agent_repo
            
            # Simulate at rate limit
            mock_redis.execute.return_value = ["30", 60]
            
            response = client.post(
                "/recommendations",
                json={"symbol": "NIFTY", "signal_type": "PDH_BREAKOUT", "signal_data": {"price": 22000}}
            )
            data = response.json()
            assert "error" in data
            assert "code" in data
            assert "details" in data
            assert data["code"] == "RATE_LIMIT_EXCEEDED"


class TestCorrelationID:
    """Request correlation tests"""
    
    def test_correlation_id_generated(self, client):
        """Should generate request ID if not provided"""
        response = client.get("/health")
        assert "X-Request-ID" in response.headers
        assert len(response.headers["X-Request-ID"]) == 36  # UUID format
    
    def test_correlation_id_preserved(self, client):
        """Should preserve provided request ID"""
        request_id = "test-request-123"
        response = client.get("/health", headers={"X-Request-ID": request_id})
        assert response.headers["X-Request-ID"] == request_id
    
    def test_correlation_id_unique(self, client):
        """Should generate unique IDs for different requests"""
        response1 = client.get("/health")
        response2 = client.get("/health")
        assert response1.headers["X-Request-ID"] != response2.headers["X-Request-ID"]


class TestSecurityHeaders:
    """Security headers tests"""
    
    def test_security_headers_present(self, client):
        """Should include security headers"""
        response = client.get("/health")
        
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert response.headers["X-Frame-Options"] == "DENY"
        assert response.headers["X-XSS-Protection"] == "1; mode=block"
        assert "Content-Security-Policy" in response.headers
        assert response.headers["Referrer-Policy"] == "no-referrer"
        assert "Permissions-Policy" in response.headers
    
    def test_hsts_in_production(self):
        """Should include HSTS in production"""
        test_app = FastAPI()
        test_app.add_middleware(SecurityHeadersMiddleware, enable_hsts=True)
        
        @test_app.get("/test")
        def test_endpoint():
            return {"status": "ok"}
        
        client = TestClient(test_app)
        response = client.get("/test")
        
        assert "Strict-Transport-Security" in response.headers


class TestValidationSchemas:
    """Schema validation unit tests"""
    
    def test_signal_type_validation(self):
        """Should validate signal types against whitelist"""
        # Valid
        data = {
            "symbol": "NIFTY",
            "signal_type": "PDH_BREAKOUT",
            "signal_data": {"price": 22000}
        }
        request = SignalRequest(**data)
        assert request.signal_type == "PDH_BREAKOUT"
        
        # Invalid
        with pytest.raises(ValueError, match="Invalid signal_type"):
            SignalRequest(
                symbol="NIFTY",
                signal_type="INVALID_TYPE",
                signal_data={"price": 22000}
            )
    
    def test_symbol_uppercase(self):
        """Should convert symbol to uppercase"""
        request = SignalRequest(
            symbol="nifty",
            signal_type="PDH_BREAKOUT",
            signal_data={"price": 22000}
        )
        assert request.symbol == "NIFTY"
    
    def test_price_validation(self):
        """Should validate positive prices"""
        with pytest.raises(ValueError, match="must be positive"):
            SignalRequest(
                symbol="NIFTY",
                signal_type="PDH_BREAKOUT",
                signal_data={"price": -100}
            )
