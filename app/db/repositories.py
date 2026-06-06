"""
Repository Layer

Database access layer for TradeMind models.
"""

from uuid import UUID
from typing import Sequence
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Recommendation, AgentOutput, MarketNews, EvaluationResult
from app.core.schemas import RecommendationCreate
from app.core.logging import get_logger

logger = get_logger(__name__)


class RecommendationRepository:
    """Repository for Recommendation operations"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, data: RecommendationCreate) -> Recommendation:
        """Create new recommendation"""
        rec = Recommendation(**data.model_dump())
        self.session.add(rec)
        await self.session.flush()
        logger.info(f"Created recommendation: {rec.id} for {rec.symbol}")
        return rec
    
    async def get_by_id(self, rec_id: UUID) -> Recommendation | None:
        """Get recommendation by ID"""
        result = await self.session.execute(
            select(Recommendation).where(Recommendation.id == rec_id)
        )
        return result.scalar_one_or_none()
    
    async def get_latest(self, limit: int = 20, symbol: str | None = None) -> Sequence[Recommendation]:
        """Get latest recommendations"""
        query = select(Recommendation).order_by(desc(Recommendation.created_at))
        
        if symbol:
            query = query.where(Recommendation.symbol == symbol.upper())
        
        query = query.limit(limit)
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def commit(self):
        """Commit transaction"""
        await self.session.commit()
    
    async def rollback(self):
        """Rollback transaction"""
        await self.session.rollback()


class AgentOutputRepository:
    """Repository for AgentOutput operations"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(
        self,
        recommendation_id: UUID,
        agent_name: str,
        reasoning: str,
        confidence: int,
        metadata_json: dict,
        latency_ms: int,
        tokens_used: int | None = None,
        model_used: str | None = None
    ) -> AgentOutput:
        """Create agent output"""
        output = AgentOutput(
            recommendation_id=recommendation_id,
            agent_name=agent_name,
            reasoning=reasoning,
            confidence=confidence,
            metadata_json=metadata_json,
            latency_ms=latency_ms,
            tokens_used=tokens_used,
            model_used=model_used
        )
        self.session.add(output)
        await self.session.flush()
        logger.debug(f"Created agent output: {agent_name} for rec {recommendation_id}")
        return output
    
    async def get_by_recommendation(self, recommendation_id: UUID) -> Sequence[AgentOutput]:
        """Get all agent outputs for a recommendation"""
        result = await self.session.execute(
            select(AgentOutput).where(AgentOutput.recommendation_id == recommendation_id)
        )
        return result.scalars().all()


class MarketNewsRepository:
    """Repository for MarketNews operations"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create_batch(self, news_items: list[dict]) -> list[MarketNews]:
        """Create multiple news items"""
        news_objects = [MarketNews(**item) for item in news_items]
        self.session.add_all(news_objects)
        await self.session.flush()
        logger.info(f"Created {len(news_objects)} news items")
        return news_objects
    
    async def get_recent_for_symbol(self, symbol: str, hours: int = 24) -> Sequence[MarketNews]:
        """Get recent news for symbol"""
        from datetime import datetime, timedelta
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        
        result = await self.session.execute(
            select(MarketNews)
            .where(MarketNews.symbol == symbol.upper())
            .where(MarketNews.published_at >= cutoff)
            .order_by(desc(MarketNews.published_at))
        )
        return result.scalars().all()


class EvaluationRepository:
    """Repository for EvaluationResult operations"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(
        self,
        recommendation_id: UUID,
        outcome: str,
        pnl_percent: float | None = None,
        max_favorable_move: float | None = None,
        max_adverse_move: float | None = None
    ) -> EvaluationResult:
        """Create evaluation result"""
        evaluation = EvaluationResult(
            recommendation_id=recommendation_id,
            outcome=outcome,
            pnl_percent=pnl_percent,
            max_favorable_move=max_favorable_move,
            max_adverse_move=max_adverse_move
        )
        self.session.add(evaluation)
        await self.session.flush()
        logger.info(f"Created evaluation for rec {recommendation_id}: {outcome}")
        return evaluation
    
    async def get_by_recommendation(self, recommendation_id: UUID) -> EvaluationResult | None:
        """Get evaluation for recommendation"""
        result = await self.session.execute(
            select(EvaluationResult).where(EvaluationResult.recommendation_id == recommendation_id)
        )
        return result.scalar_one_or_none()
