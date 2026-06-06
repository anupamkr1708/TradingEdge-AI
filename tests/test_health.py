"""Tests for health check endpoints"""

import pytest


def test_root_endpoint(client):
    """Test root endpoint returns app info"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "TradeMind AI"
    assert data["version"] == "0.1.0"
    assert "status" in data


def test_liveness_probe(client):
    """Test liveness probe always returns 200"""
    response = client.get("/health/live")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "alive"
    assert "timestamp" in data


def test_health_check(client):
    """Test comprehensive health check"""
    response = client.get("/health")
    assert response.status_code in [200, 503]
    data = response.json()
    assert "status" in data
    assert "services" in data
    assert "timestamp" in data


def test_metrics_endpoint(client):
    """Test Prometheus metrics endpoint"""
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "trademind_" in response.text
