"""
Pydantic Schemas

Data validation and serialization schemas.
"""

from datetime import datetime
from uuid import UUID
from typing import Any
from pydantic import BaseModel, Field, field_validator, model_validator


# Validation constants
MAX_SYMBOL_LENGTH = 20
MAX_SIGNAL_TYPE_LENGTH = 50
MAX_CANDLES = 1000
MAX_NEWS_ITEMS = 100
MAX_METADATA_SIZE = 10000
VALID_SIGNAL_TYPES = {
    "PDH_BREAKOUT", "PDL_BREAKDOWN", "PDH_REJECTION", "PDL_REJECTION",
    "RANGE_BREAKOUT", "SUPPORT_BOUNCE", "RESISTANCE_REJECTION", 
    "TREND_CONTINUATION", "REVERSAL"
}


class AgentRequest(BaseModel):
    """Request schema for agent execution"""
    
    symbol: str = Field(..., min_length=1, max_length=MAX_SYMBOL_LENGTH)
    signal_type: str = Field(..., max_length=MAX_SIGNAL_TYPE_LENGTH)
    signal_data: dict[str, Any] = Field(default_factory=dict)
    context: dict[str, Any] = Field(default_factory=dict, description="Shared context from other agents")
    
    @field_validator("symbol")
    @classmethod
    def uppercase_symbol(cls, v: str) -> str:
        return v.upper()


class AgentResponse(BaseModel):
    """Response schema from agent execution"""
    
    agent_name: str = Field(..., min_length=1, max_length=50)
    success: bool
    reasoning: str = Field(..., min_length=1, max_length=5000)
    confidence: int = Field(ge=0, le=100)
    metadata: dict[str, Any] = Field(default_factory=dict)
    latency_ms: int = Field(ge=0)
    tokens_used: int | None = Field(None, ge=0)
    llm_model: str | None = Field(None, max_length=100)
    error: str | None = Field(None, max_length=1000)


class RecommendationCreate(BaseModel):
    """Schema for creating recommendations"""
    
    symbol: str = Field(..., min_length=1, max_length=MAX_SYMBOL_LENGTH)
    signal_type: str = Field(..., max_length=MAX_SIGNAL_TYPE_LENGTH)
    recommendation: str = Field(..., pattern="^(BUY|SELL|HOLD|SKIP)$")
    confidence: int = Field(ge=0, le=100)
    reasoning: str = Field(..., min_length=1, max_length=5000)
    entry_price: float | None = Field(None, gt=0)
    target_price: float | None = Field(None, gt=0)
    stop_loss: float | None = Field(None, gt=0)
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
    llm_model: str | None
    created_at: datetime
    
    model_config = {"from_attributes": True}


class SignalRequest(BaseModel):
    """Request schema for signal processing"""
    
    symbol: str = Field(..., min_length=1, max_length=MAX_SYMBOL_LENGTH)
    signal_type: str = Field(..., max_length=MAX_SIGNAL_TYPE_LENGTH)
    signal_data: dict[str, Any] = Field(..., description="Price, volume, support, resistance")
    candles: list[dict[str, Any]] | None = Field(None, max_length=MAX_CANDLES)
    news_items: list[dict[str, Any]] | None = Field(None, max_length=MAX_NEWS_ITEMS)
    
    @field_validator("symbol")
    @classmethod
    def uppercase_symbol(cls, v: str) -> str:
        return v.upper()
    
    @field_validator("signal_type")
    @classmethod
    def validate_signal_type(cls, v: str) -> str:
        v_upper = v.upper()
        if v_upper not in VALID_SIGNAL_TYPES:
            raise ValueError(f"Invalid signal_type. Must be one of: {', '.join(VALID_SIGNAL_TYPES)}")
        return v_upper
    
    @field_validator("signal_data")
    @classmethod
    def validate_signal_data(cls, v: dict) -> dict:
        """Validate required fields and price constraints"""
        if not v:
            raise ValueError("signal_data cannot be empty")
        
        # Validate price fields if present
        price_fields = ["price", "entry", "support", "resistance"]
        for field in price_fields:
            if field in v and v[field] is not None:
                price = float(v[field])
                if price <= 0:
                    raise ValueError(f"{field} must be positive")
        
        # Validate confidence if present
        if "confidence" in v:
            conf = int(v["confidence"])
            if not 0 <= conf <= 100:
                raise ValueError("confidence must be between 0 and 100")
        
        return v
    
    @field_validator("candles")
    @classmethod
    def validate_candles(cls, v: list | None) -> list | None:
        """Validate candle data structure"""
        if not v:
            return v
        
        required_fields = {"open", "high", "low", "close", "volume"}
        for i, candle in enumerate(v):
            missing = required_fields - set(candle.keys())
            if missing:
                raise ValueError(f"Candle {i}: missing fields {missing}")
            
            # Validate OHLC relationship
            o, h, l, c = candle["open"], candle["high"], candle["low"], candle["close"]
            if not (l <= o <= h and l <= c <= h):
                raise ValueError(f"Candle {i}: invalid OHLC relationship")
        
        return v


class RecommendationDetailResponse(BaseModel):
    """Detailed recommendation with agent outputs"""
    
    recommendation: RecommendationResponse
    agent_outputs: list[AgentOutputResponse]
    trade_plan: dict[str, Any]
