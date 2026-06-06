"""
Agent Orchestrator

Central execution engine coordinating all agents and services.
"""

import time
from typing import Any

from app.agents import TechnicalAgent, NewsAgent, DecisionAgent
from app.services.signal_enrichment import SignalEnrichment
from app.services.trade_planner import TradePlanner
from app.core.schemas import AgentRequest, AgentResponse
from app.integrations.groq_client import GroqClient
from app.core.logging import get_logger
from app.monitoring.metrics import metrics

logger = get_logger(__name__)


class Orchestrator:
    """
    Agent Orchestrator
    
    Executes the full trading intelligence pipeline:
    1. Signal Enrichment (quantitative indicators)
    2. Technical Agent (technical analysis)
    3. News Agent (sentiment analysis)
    4. Decision Agent (final recommendation)
    5. Trade Planner (execution parameters)
    """
    
    def __init__(self, groq_client: GroqClient):
        self.groq_client = groq_client
        self.enrichment_service = SignalEnrichment()
        self.technical_agent = TechnicalAgent(llm_client=groq_client)
        self.news_agent = NewsAgent(llm_client=groq_client)
        self.decision_agent = DecisionAgent(llm_client=groq_client)
        self.trade_planner = TradePlanner()
        self.logger = logger
    
    async def process_signal(
        self,
        symbol: str,
        signal_type: str,
        signal_data: dict[str, Any],
        candles: list[dict] | None = None,
        news_items: list[dict] | None = None
    ) -> dict[str, Any]:
        """
        Process trading signal through full pipeline.
        
        Args:
            symbol: Trading symbol (e.g., NIFTY, BANKNIFTY)
            signal_type: Signal type (PDH_BREAKOUT, PDL_BREAKDOWN, etc.)
            signal_data: Signal metadata (price, support, resistance, volume, etc.)
            candles: Historical OHLCV data for enrichment (optional)
            news_items: Recent news headlines (optional)
        
        Returns:
            {
                "symbol": str,
                "signal_type": str,
                "enrichment": dict,
                "technical_analysis": AgentResponse,
                "news_analysis": AgentResponse,
                "decision": AgentResponse,
                "trade_plan": dict,
                "final_recommendation": str,
                "confidence": int,
                "total_latency_ms": int,
                "success": bool
            }
        """
        start_time = time.time()
        
        self.logger.info(f"Processing signal: {symbol} - {signal_type}")
        
        try:
            # Step 1: Signal Enrichment
            enrichment = await self._run_enrichment(candles)
            
            # Step 2: Technical Agent
            technical_result = await self._run_technical_agent(
                symbol=symbol,
                signal_type=signal_type,
                signal_data=signal_data,
                enrichment=enrichment
            )
            
            # Step 3: News Agent (non-blocking failure)
            news_result = await self._run_news_agent(
                symbol=symbol,
                signal_type=signal_type,
                signal_data=signal_data,
                news_items=news_items
            )
            
            # Step 4: Decision Agent
            decision_result = await self._run_decision_agent(
                symbol=symbol,
                signal_type=signal_type,
                signal_data=signal_data,
                technical_result=technical_result,
                news_result=news_result,
                enrichment=enrichment
            )
            
            # Step 5: Trade Planner
            trade_plan = self._run_trade_planner(
                decision_result=decision_result,
                signal_type=signal_type,
                signal_data=signal_data,
                enrichment=enrichment
            )
            
            # Calculate total latency
            total_latency_ms = int((time.time() - start_time) * 1000)
            
            # Build unified response
            result = {
                "symbol": symbol,
                "signal_type": signal_type,
                "enrichment": enrichment,
                "technical_analysis": technical_result,
                "news_analysis": news_result,
                "decision": decision_result,
                "trade_plan": trade_plan,
                "final_recommendation": decision_result.metadata.get("recommendation", "SKIP"),
                "confidence": decision_result.confidence,
                "total_latency_ms": total_latency_ms,
                "success": True
            }
            
            self.logger.info(
                f"Signal processed: {symbol} - {result['final_recommendation']} "
                f"(confidence={result['confidence']}%, latency={total_latency_ms}ms)"
            )
            
            # Record metrics
            metrics.record_cache_operation("orchestrator", "success")
            
            return result
            
        except Exception as e:
            total_latency_ms = int((time.time() - start_time) * 1000)
            
            self.logger.error(f"Orchestrator failed: {e}", exc_info=True)
            
            # Record metrics
            metrics.record_cache_operation("orchestrator", "failure")
            
            return {
                "symbol": symbol,
                "signal_type": signal_type,
                "enrichment": {},
                "technical_analysis": None,
                "news_analysis": None,
                "decision": None,
                "trade_plan": None,
                "final_recommendation": "SKIP",
                "confidence": 0,
                "total_latency_ms": total_latency_ms,
                "success": False,
                "error": str(e)
            }
    
    async def _run_enrichment(self, candles: list[dict] | None) -> dict[str, Any]:
        """Run signal enrichment with fallback"""
        if not candles or len(candles) < 20:
            self.logger.warning("Insufficient candles for enrichment, using defaults")
            return {
                "ema_trend": "neutral",
                "rsi": 50,
                "rsi_signal": "neutral",
                "macd_trend": "neutral",
                "volume_signal": "normal",
                "atr": 0,
                "volume_ratio": 1.0
            }
        
        try:
            return self.enrichment_service.enrich(candles)
        except Exception as e:
            self.logger.error(f"Enrichment failed: {e}")
            return {
                "ema_trend": "neutral",
                "rsi": 50,
                "rsi_signal": "neutral",
                "macd_trend": "neutral",
                "volume_signal": "normal",
                "atr": 0,
                "volume_ratio": 1.0
            }
    
    async def _run_technical_agent(
        self,
        symbol: str,
        signal_type: str,
        signal_data: dict,
        enrichment: dict
    ) -> AgentResponse:
        """Run technical agent"""
        request = AgentRequest(
            symbol=symbol,
            signal_type=signal_type,
            signal_data=signal_data,
            context={"enrichment": enrichment}
        )
        
        return await self.technical_agent.execute(request)
    
    async def _run_news_agent(
        self,
        symbol: str,
        signal_type: str,
        signal_data: dict,
        news_items: list[dict] | None
    ) -> AgentResponse:
        """Run news agent with graceful failure"""
        try:
            context = {"news": news_items} if news_items else {}
            
            request = AgentRequest(
                symbol=symbol,
                signal_type=signal_type,
                signal_data=signal_data,
                context=context
            )
            
            return await self.news_agent.execute(request)
            
        except Exception as e:
            self.logger.warning(f"News agent failed: {e}, continuing with neutral sentiment")
            
            # Return neutral news response
            return AgentResponse(
                agent_name="news_intelligence",
                success=False,
                reasoning="News analysis unavailable",
                confidence=40,
                metadata={
                    "sentiment": "neutral",
                    "impact": "low",
                    "relevance": "irrelevant"
                },
                latency_ms=0,
                error=str(e)
            )
    
    async def _run_decision_agent(
        self,
        symbol: str,
        signal_type: str,
        signal_data: dict,
        technical_result: AgentResponse,
        news_result: AgentResponse,
        enrichment: dict
    ) -> AgentResponse:
        """Run decision agent"""
        request = AgentRequest(
            symbol=symbol,
            signal_type=signal_type,
            signal_data=signal_data,
            context={
                "technical_agent": technical_result,
                "news_agent": news_result,
                "enrichment": enrichment
            }
        )
        
        return await self.decision_agent.execute(request)
    
    def _run_trade_planner(
        self,
        decision_result: AgentResponse,
        signal_type: str,
        signal_data: dict,
        enrichment: dict
    ) -> dict[str, Any]:
        """Run trade planner with graceful failure"""
        try:
            recommendation = decision_result.metadata.get("recommendation", "SKIP")
            confidence = decision_result.confidence
            risk_level = decision_result.metadata.get("risk_level", "medium")
            current_price = signal_data.get("price", 0)
            
            return self.trade_planner.plan_trade(
                recommendation=recommendation,
                confidence=confidence,
                risk_level=risk_level,
                current_price=current_price,
                signal_type=signal_type,
                enrichment=enrichment
            )
            
        except Exception as e:
            self.logger.error(f"Trade planner failed: {e}")
            return {
                "entry_price": 0.0,
                "stop_loss": 0.0,
                "target_1": 0.0,
                "target_2": 0.0,
                "risk_reward_ratio": 0.0,
                "position_size_pct": 0.0,
                "trade_valid": False,
                "error": str(e)
            }
