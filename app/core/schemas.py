"""
Pydantic Schemas

Data validation and serialization schemas.
"""

from datetime import datetime
from uuid import UUID
from typing import Any
from pydantic import BaseModel, Field, field_validator


class AgentRequest(BaseModel):
    """Request schema for agent execution"""
    
    symbol: str = Field(..., min_length=1, max_length=20)
    signal_type: str = Field(..., description="PDH_BREAKOUT, PDL_REJECTION, etc.")
    signal_data: dict[str, Any] = Field(default_factory=dict)
    context: dict[str, Any] = Field(default_factory=dict, description="Shared context from other agents")
    
    @field_validator("symbol")
    @classmethod
    def uppercase_symbol(cls, v: str) -> str:
        return v.upper()


class AgentResponse(BaseModel):
    """Response schema from agent execution"""
    
    agent_name: str
    success: bool
    reasoning: str
    confidence: int = Field(ge=0, le=100)
    metadata: dict[str, Any] = Field(default_factory=dict)
    latency_ms: int = Field(ge=0)
    tokens_used: int | None = None
    model_used: str | None = None
    error: str | None = None


class RecommendationCreate(BaseModel):
    """Schema for creating recommendations"""
    
    symbol: str
    signal_type: str
    recommendation: str = Field(..., pattern="^(BUY|SELL|HOLD|SKIP)$")
    confidence: int = Field(ge=0, le=100)
    reasoning: str
    entry_price: float | None = None
    target_price: float | None = None
    stop_loss: float | None = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class RecommendationResponse(BaseModel):
    """Response schema for recommendations"""
    
    id: UUID
    symbol: str
    signal_type: str
    recommendation: str
    confidence: int
    reasoning: str
    entry_price: float | None
    target_price: float | None
    stop_loss: float | None
    metadata_json: dict[str, Any]
    created_at: datetime
    
    model_config = {"from_attributes": True}


class AgentOutputResponse(BaseModel):
    """Response schema for agent outputs"""
    
    id: UUID
    recommendation_id: UUID
    agent_name: str
    reasoning: str
    confidence: int
    metadata_json: dict[str, Any]
    latency_ms: int
    tokens_used: int | None
    model_used: str | None
    created_at: datetime
    
    model_config = {"from_attributes": True}


class SignalRequest(BaseModel):
    """Request schema for signal processing"""
    
    symbol: str = Field(..., min_length=1, max_length=20)
    signal_type: str = Field(..., description="PDH_BREAKOUT, PDL_BREAKDOWN, etc.")
    signal_data: dict[str, Any] = Field(..., description="Price, volume, support, resistance")
    candles: list[dict[str, Any]] | None = Field(None, description="Historical OHLCV data")
    news_items: list[dict[str, Any]] | None = Field(None, description="Recent news headlines")
    
    @field_validator("symbol")
    @classmethod
    def uppercase_symbol(cls, v: str) -> str:
        return v.upper()


class RecommendationDetailResponse(BaseModel):
    """Detailed recommendation with agent outputs"""
    
    recommendation: RecommendationResponse
    agent_outputs: list[AgentOutputResponse]
    trade_plan: dict[str, Any]
