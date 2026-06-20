"""
Decision Agent

Synthesizes technical and news analysis into final trading recommendation.
"""

import json
from typing import Any

from app.agents.base import BaseAgent
from app.agents.prompts.decision_prompt import DECISION_PROMPT
from app.core.schemas import AgentRequest, AgentResponse
from app.integrations.groq_client import GroqClient
from app.core.logging import get_logger

logger = get_logger(__name__)


class DecisionAgent(BaseAgent):
    """
    Decision Agent
    
    Synthesizes technical analysis, news intelligence, and quantitative indicators
    into final BUY/SELL/HOLD/SKIP recommendation with confidence scoring.
    """
    
    def __init__(self, llm_client: GroqClient):
        super().__init__(name="decision_maker", llm_client=llm_client)
    
    async def analyze(self, request: AgentRequest) -> dict[str, Any]:
        """
        Generate final trading recommendation.
        
        Expects context to contain:
        - technical_agent: AgentResponse from TechnicalAgent
        - news_agent: AgentResponse from NewsAgent
        - enrichment: dict from SignalEnrichment
        
        Returns:
            {
                "recommendation": str,  # BUY/SELL/HOLD/SKIP
                "reasoning": str,
                "confidence": int,
                "metadata": dict,
                "tokens_used": int,
                "model_used": str
            }
        """
        
        # Extract agent outputs from context
        tech_output = request.context.get("technical_agent")
        news_output = request.context.get("news_agent")
        enrichment = request.context.get("enrichment", {})
        
        # Validate inputs
        if not tech_output:
            return self._error_response("Technical analysis missing from context")
        
        # Extract technical data
        tech_confidence = tech_output.confidence if isinstance(tech_output, AgentResponse) else tech_output.get("confidence", 50)
        tech_metadata = tech_output.metadata if isinstance(tech_output, AgentResponse) else tech_output.get("metadata", {})
        tech_reasoning = tech_output.reasoning if isinstance(tech_output, AgentResponse) else tech_output.get("reasoning", "")
        
        # Extract news data
        if news_output and (isinstance(news_output, AgentResponse) and news_output.success or isinstance(news_output, dict)):
            news_confidence = news_output.confidence if isinstance(news_output, AgentResponse) else news_output.get("confidence", 40)
            news_metadata = news_output.metadata if isinstance(news_output, AgentResponse) else news_output.get("metadata", {})
            news_reasoning = news_output.reasoning if isinstance(news_output, AgentResponse) else news_output.get("reasoning", "No news")
        else:
            news_confidence = 40
            news_metadata = {"sentiment": "neutral", "impact": "low", "relevance": "irrelevant"}
            news_reasoning = "No news available"
        
        # Build prompt context
        prompt_context = self._build_prompt_context(
            symbol=request.symbol,
            signal_type=request.signal_type,
            price=request.signal_data.get("price", 0),
            tech_confidence=tech_confidence,
            tech_metadata=tech_metadata,
            tech_reasoning=tech_reasoning,
            news_confidence=news_confidence,
            news_metadata=news_metadata,
            news_reasoning=news_reasoning,
            enrichment=enrichment
        )
        
        # Use Llama 3.3
        try:
            return await self._analyze_with_llama(prompt_context)
        except Exception as e:
            self.logger.error(f"LLM analysis failed: {e}, using deterministic fallback")
            return self._deterministic_decision(
                tech_confidence=tech_confidence,
                tech_metadata=tech_metadata,
                news_confidence=news_confidence,
                news_metadata=news_metadata,
                signal_type=request.signal_type
            )
    
    def _build_prompt_context(
        self,
        symbol: str,
        signal_type: str,
        price: float,
        tech_confidence: int,
        tech_metadata: dict,
        tech_reasoning: str,
        news_confidence: int,
        news_metadata: dict,
        news_reasoning: str,
        enrichment: dict
    ) -> dict:
        """Build unified context for LLM prompt"""
        return {
            "symbol": symbol,
            "signal_type": signal_type,
            "price": price,
            "tech_confidence": tech_confidence,
            "tech_trend": tech_metadata.get("trend_strength", "moderate"),
            "tech_reasoning": tech_reasoning,
            "news_confidence": news_confidence,
            "news_sentiment": news_metadata.get("sentiment", "neutral"),
            "news_impact": news_metadata.get("impact", "low"),
            "news_relevance": news_metadata.get("relevance", "irrelevant"),
            "news_reasoning": news_reasoning,
            "rsi": enrichment.get("rsi", 50),
            "rsi_signal": enrichment.get("rsi_signal", "neutral"),
            "macd_trend": enrichment.get("macd_trend", "neutral"),
            "volume_signal": enrichment.get("volume_signal", "normal"),
        }
    
    async def _analyze_with_llama(self, context: dict) -> dict[str, Any]:
        """Analyze with Llama 3.3 model"""
        prompt = DECISION_PROMPT.format(**context)
        
        llm_response = await self.llm.generate(
            prompt=prompt,
            model="llama-3.3-70b-versatile",
            temperature=0.3,
            max_tokens=600,
            timeout=15
        )
        
        decision = self._parse_llm_response(llm_response["content"])
        return self._build_result(decision, llm_response)
    
    def _parse_llm_response(self, content: str) -> dict:
        """Parse LLM JSON response"""
        try:
            start = content.find("{")
            end = content.rfind("}") + 1
            
            if start >= 0 and end > start:
                json_str = content[start:end]
                return json.loads(json_str)
            else:
                self.logger.warning("No JSON found in LLM response")
                return {}
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse LLM JSON: {e}")
            return {}
    
    def _build_result(self, decision: dict, llm_response: dict) -> dict[str, Any]:
        """Build standardized result from LLM decision"""
        recommendation = decision.get("recommendation", "SKIP").upper()
        confidence = decision.get("confidence", 40)
        
        # Validate recommendation
        if recommendation not in ["BUY", "SELL", "HOLD", "SKIP"]:
            self.logger.warning(f"Invalid recommendation {recommendation}, defaulting to SKIP")
            recommendation = "SKIP"
            confidence = max(30, confidence - 20)
        
        # Clamp confidence
        if confidence < 0 or confidence > 100:
            confidence = max(0, min(100, confidence))
        
        reasoning = decision.get("reasoning", "Trading decision completed")
        
        metadata = {
            "recommendation": recommendation,
            "risk_level": decision.get("risk_level", "medium"),
            "key_factors": decision.get("key_factors", []),
            "conflicts": decision.get("conflicts", ""),
        }
        
        return {
            "recommendation": recommendation,
            "reasoning": reasoning,
            "confidence": confidence,
            "metadata": metadata,
            "tokens_used": llm_response.get("tokens_total", 0),
            "model_used": llm_response.get("model")
        }
    
    def _deterministic_decision(
        self,
        tech_confidence: int,
        tech_metadata: dict,
        news_confidence: int,
        news_metadata: dict,
        signal_type: str
    ) -> dict[str, Any]:
        """
        Deterministic fallback decision logic.
        
        Weighted scoring:
        - Technical: 60%
        - News: 40%
        """
        self.logger.info("Using deterministic decision logic")
        
        # Calculate weighted confidence
        weighted_confidence = int((tech_confidence * 0.6) + (news_confidence * 0.4))
        
        # Get sentiment signals
        news_sentiment = news_metadata.get("sentiment", "neutral")
        news_impact = news_metadata.get("impact", "low")
        trend_strength = tech_metadata.get("trend_strength", "moderate")
        
        # Determine recommendation
        is_bullish_signal = signal_type in ["PDH_BREAKOUT", "PDL_REJECTION", "TREND_CONTINUATION"]
        is_bearish_signal = signal_type in ["PDL_BREAKDOWN", "PDH_REJECTION"]
        
        recommendation = "SKIP"
        risk_level = "medium"
        conflicts = ""
        
        # BUY logic
        if is_bullish_signal and tech_confidence >= 60:
            if news_sentiment in ["positive", "neutral"] or news_impact == "low":
                if weighted_confidence >= 55:
                    recommendation = "BUY"
                    risk_level = "low" if news_sentiment == "positive" else "medium"
                else:
                    recommendation = "HOLD"
            else:
                conflicts = "Bullish technical but negative news"
                recommendation = "SKIP"
        
        # SELL logic
        elif is_bearish_signal and tech_confidence >= 60:
            if news_sentiment in ["negative", "neutral"] or news_impact == "low":
                if weighted_confidence >= 55:
                    recommendation = "SELL"
                    risk_level = "low" if news_sentiment == "negative" else "medium"
                else:
                    recommendation = "HOLD"
            else:
                conflicts = "Bearish technical but positive news"
                recommendation = "SKIP"
        
        # Low confidence = SKIP
        else:
            recommendation = "SKIP"
            conflicts = "Insufficient confidence or unclear signal"
            risk_level = "high"
        
        # Adjust confidence for recommendation
        if recommendation == "SKIP":
            final_confidence = min(weighted_confidence, 45)
        else:
            final_confidence = weighted_confidence
        
        reasoning = (
            f"{recommendation} recommendation for {signal_type}. "
            f"Technical confidence: {tech_confidence}%, News sentiment: {news_sentiment}. "
            f"Weighted confidence: {final_confidence}%."
        )
        
        metadata = {
            "recommendation": recommendation,
            "risk_level": risk_level,
            "key_factors": [
                f"Technical: {trend_strength}",
                f"News: {news_sentiment}",
                f"Confidence: {final_confidence}%"
            ],
            "conflicts": conflicts,
            "fallback": True
        }
        
        return {
            "recommendation": recommendation,
            "reasoning": reasoning,
            "confidence": final_confidence,
            "metadata": metadata,
            "tokens_used": None,
            "model_used": None
        }
    
    def _error_response(self, error_msg: str) -> dict[str, Any]:
        """Return error response"""
        self.logger.error(f"Decision agent error: {error_msg}")
        return {
            "recommendation": "SKIP",
            "reasoning": f"Error: {error_msg}",
            "confidence": 0,
            "metadata": {"error": error_msg},
            "tokens_used": None,
            "model_used": None
        }
