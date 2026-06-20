"""
News Intelligence Agent

Analyzes market news and sentiment for trading symbols.
"""

import json
from typing import Any

from app.agents.base import BaseAgent
from app.agents.prompts.news_prompt import NEWS_ANALYSIS_PROMPT, format_headlines
from app.core.schemas import AgentRequest
from app.integrations.groq_client import GroqClient
from app.core.logging import get_logger

logger = get_logger(__name__)


class NewsAgent(BaseAgent):
    """
    News Intelligence Agent
    
    Analyzes news sentiment, impact, and relevance for trading symbols.
    Provides risk signals based on news analysis.
    """
    
    def __init__(self, llm_client: GroqClient):
        super().__init__(name="news_intelligence", llm_client=llm_client)
    
    async def analyze(self, request: AgentRequest) -> dict[str, Any]:
        """
        Perform news sentiment analysis.
        
        Returns:
            {
                "reasoning": str,
                "confidence": int,
                "metadata": dict,
                "tokens_used": int,
                "model_used": str
            }
        """
        
        # Extract news from context or signal_data
        news_items = request.context.get("news", [])
        if not news_items:
            news_items = request.signal_data.get("news", [])
        
        # If no news available, return neutral assessment
        if not news_items:
            return self._no_news_analysis(request.symbol)
        
        # Format headlines
        headlines = format_headlines(news_items)
        
        # Use Llama 3.3
        try:
            return await self._analyze_with_llama(request.symbol, headlines)
        except Exception as e:
            self.logger.error(f"LLM analysis failed: {e}, using deterministic fallback")
            return self._deterministic_analysis(request.symbol, news_items)
    
    async def _analyze_with_llama(self, symbol: str, headlines: str) -> dict[str, Any]:
        """Analyze with Llama 3.3 model"""
        prompt = NEWS_ANALYSIS_PROMPT.format(
            symbol=symbol,
            headlines=headlines
        )
        
        llm_response = await self.llm.generate(
            prompt=prompt,
            model="llama-3.3-70b-versatile",
            temperature=0.3,
            max_tokens=400,
            timeout=15
        )
        
        analysis = self._parse_llm_response(llm_response["content"])
        return self._build_result(analysis, llm_response)
    
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
    
    def _build_result(self, analysis: dict, llm_response: dict) -> dict[str, Any]:
        """Build standardized result from analysis"""
        confidence = analysis.get("confidence", 50)
        
        # Clamp confidence
        if confidence < 0 or confidence > 100:
            self.logger.warning(f"Invalid confidence {confidence}, clamping")
            confidence = max(0, min(100, confidence))
        
        reasoning = analysis.get("reasoning", "News analysis completed")
        
        metadata = {
            "sentiment": analysis.get("sentiment", "neutral"),
            "impact": analysis.get("impact", "medium"),
            "relevance": analysis.get("relevance", "partially_relevant"),
            "key_signals": analysis.get("key_signals", []),
            "risks": analysis.get("risks", [])
        }
        
        return {
            "reasoning": reasoning,
            "confidence": confidence,
            "metadata": metadata,
            "tokens_used": llm_response.get("tokens_total", 0),
            "model_used": llm_response.get("model")
        }
    
    def _no_news_analysis(self, symbol: str) -> dict[str, Any]:
        """Handle case when no news is available"""
        self.logger.info(f"No news available for {symbol}")
        
        return {
            "reasoning": f"No recent news available for {symbol}. Neutral sentiment assumed.",
            "confidence": 40,
            "metadata": {
                "sentiment": "neutral",
                "impact": "low",
                "relevance": "irrelevant",
                "key_signals": [],
                "risks": ["No news data available"]
            },
            "tokens_used": None,
            "model_used": None
        }
    
    def _deterministic_analysis(self, symbol: str, news_items: list[dict]) -> dict[str, Any]:
        """
        Deterministic fallback when LLM fails.
        
        Simple keyword-based sentiment detection.
        """
        self.logger.info("Using deterministic news analysis")
        
        positive_keywords = ["profit", "growth", "upgrade", "beat", "strong", "gain", "positive"]
        negative_keywords = ["loss", "decline", "downgrade", "miss", "weak", "fall", "negative"]
        
        positive_count = 0
        negative_count = 0
        
        for item in news_items[:5]:
            headline = item.get("headline", "").lower()
            positive_count += sum(1 for kw in positive_keywords if kw in headline)
            negative_count += sum(1 for kw in negative_keywords if kw in headline)
        
        # Determine sentiment
        if positive_count > negative_count + 1:
            sentiment = "positive"
            confidence = 55
        elif negative_count > positive_count + 1:
            sentiment = "negative"
            confidence = 55
        else:
            sentiment = "neutral"
            confidence = 45
        
        reasoning = (
            f"News analysis for {symbol} based on {len(news_items)} headlines. "
            f"Sentiment: {sentiment}. Keyword analysis detected "
            f"{positive_count} positive and {negative_count} negative signals."
        )
        
        metadata = {
            "sentiment": sentiment,
            "impact": "medium",
            "relevance": "partially_relevant",
            "key_signals": [],
            "risks": [],
            "fallback": True
        }
        
        return {
            "reasoning": reasoning,
            "confidence": confidence,
            "metadata": metadata,
            "tokens_used": None,
            "model_used": None
        }
