"""
Recommendations API Router

REST endpoints for trading recommendations.
"""

from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.orchestrator import Orchestrator
from app.integrations.groq_client import GroqClient
from app.db.supabase import get_async_db
from app.db.repositories import RecommendationRepository, AgentOutputRepository
from app.core.schemas import (
    SignalRequest,
    RecommendationResponse,
    RecommendationDetailResponse,
    AgentOutputResponse,
    RecommendationCreate
)
from app.core.logging import get_logger
from app.monitoring.metrics import metrics

logger = get_logger(__name__)

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


def get_orchestrator() -> Orchestrator:
    """Dependency: Create orchestrator instance"""
    groq_client = GroqClient()
    return Orchestrator(groq_client=groq_client)


@router.post("", response_model=RecommendationDetailResponse, status_code=201)
async def create_recommendation(
    request: SignalRequest,
    db: AsyncSession = Depends(get_async_db),
    orchestrator: Orchestrator = Depends(get_orchestrator)
):
    """
    Process trading signal and generate recommendation.
    
    Workflow:
    1. Execute orchestrator pipeline
    2. Persist recommendation
    3. Persist agent outputs
    4. Return unified response
    """
    logger.info(f"Processing signal: {request.symbol} - {request.signal_type}")
    
    try:
        # Run orchestrator pipeline
        result = await orchestrator.process_signal(
            symbol=request.symbol,
            signal_type=request.signal_type,
            signal_data=request.signal_data,
            candles=request.candles,
            news_items=request.news_items
        )
        
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result.get("error", "Processing failed"))
        
        # Extract data for persistence
        decision = result["decision"]
        trade_plan = result["trade_plan"]
        
        # Map to recommendation model
        rec_data = RecommendationCreate(
            symbol=result["symbol"],
            signal_type=result["signal_type"],
            recommendation=result["final_recommendation"],
            confidence=result["confidence"],
            reasoning=decision.reasoning,
            entry_price=trade_plan.get("entry_price"),
            target_price=trade_plan.get("target_1"),  # Primary target
            stop_loss=trade_plan.get("stop_loss"),
            metadata_json={
                "enrichment": result["enrichment"],
                "trade_plan": trade_plan,
                "total_latency_ms": result["total_latency_ms"]
            }
        )
        
        # Persist recommendation
        rec_repo = RecommendationRepository(db)
        recommendation = await rec_repo.create(rec_data)
        
        # Persist agent outputs
        agent_repo = AgentOutputRepository(db)
        agent_outputs = []
        
        for agent_result in [result["technical_analysis"], result["news_analysis"], result["decision"]]:
            if agent_result and agent_result.success:
                output = await agent_repo.create(
                    recommendation_id=recommendation.id,
                    agent_name=agent_result.agent_name,
                    reasoning=agent_result.reasoning,
                    confidence=agent_result.confidence,
                    metadata_json=agent_result.metadata,
                    latency_ms=agent_result.latency_ms,
                    tokens_used=agent_result.tokens_used,
                    model_used=agent_result.model_used
                )
                agent_outputs.append(output)
        
        await rec_repo.commit()
        
        logger.info(f"Recommendation created: {recommendation.id}")
        metrics.record_api_request("POST", "/recommendations", 201)
        
        # Build response
        return RecommendationDetailResponse(
            recommendation=RecommendationResponse.model_validate(recommendation),
            agent_outputs=[AgentOutputResponse.model_validate(o) for o in agent_outputs],
            trade_plan=trade_plan
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create recommendation: {e}", exc_info=True)
        metrics.record_api_request("POST", "/recommendations", 500)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("", response_model=list[RecommendationResponse])
async def list_recommendations(
    symbol: str | None = Query(None, description="Filter by symbol"),
    recommendation: str | None = Query(None, description="Filter by recommendation type"),
    limit: int = Query(20, ge=1, le=100, description="Number of results"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    db: AsyncSession = Depends(get_async_db)
):
    """
    List recommendations with filtering and pagination.
    """
    try:
        rec_repo = RecommendationRepository(db)
        
        # Get recommendations (basic filtering)
        recommendations = await rec_repo.get_latest(limit=limit, symbol=symbol)
        
        # Filter by recommendation type if specified
        if recommendation:
            recommendations = [r for r in recommendations if r.recommendation == recommendation.upper()]
        
        # Apply pagination offset
        recommendations = list(recommendations)[offset:offset + limit]
        
        metrics.record_api_request("GET", "/recommendations", 200)
        
        return [RecommendationResponse.model_validate(r) for r in recommendations]
        
    except Exception as e:
        logger.error(f"Failed to list recommendations: {e}", exc_info=True)
        metrics.record_api_request("GET", "/recommendations", 500)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{recommendation_id}", response_model=RecommendationDetailResponse)
async def get_recommendation(
    recommendation_id: UUID,
    db: AsyncSession = Depends(get_async_db)
):
    """
    Get recommendation details with agent outputs.
    """
    try:
        rec_repo = RecommendationRepository(db)
        agent_repo = AgentOutputRepository(db)
        
        # Get recommendation
        recommendation = await rec_repo.get_by_id(recommendation_id)
        if not recommendation:
            raise HTTPException(status_code=404, detail="Recommendation not found")
        
        # Get agent outputs
        agent_outputs = await agent_repo.get_by_recommendation(recommendation_id)
        
        # Extract trade plan from metadata
        trade_plan = recommendation.metadata_json.get("trade_plan", {})
        
        metrics.record_api_request("GET", f"/recommendations/{recommendation_id}", 200)
        
        return RecommendationDetailResponse(
            recommendation=RecommendationResponse.model_validate(recommendation),
            agent_outputs=[AgentOutputResponse.model_validate(o) for o in agent_outputs],
            trade_plan=trade_plan
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get recommendation: {e}", exc_info=True)
        metrics.record_api_request("GET", f"/recommendations/{recommendation_id}", 500)
        raise HTTPException(status_code=500, detail=str(e))
