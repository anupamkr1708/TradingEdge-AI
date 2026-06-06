"""
Technical Analysis Agent

Analyzes technical signals from NSE FNO backend.
"""

import json
from typing import Any

from app.agents.base import BaseAgent
from app.agents.prompts.technical_prompt import TECHNICAL_ANALYSIS_PROMPT, get_signal_guidance
from app.core.schemas import AgentRequest
from app.integrations.groq_client import GroqClient
from app.core.logging import get_logger

logger = get_logger(__name__)


class TechnicalAgent(BaseAgent):
    """
    Technical Analysis Agent
    
    Evaluates price action, volume, support/resistance levels
    and generates technical reasoning with confidence scores.
    """
    
    def __init__(self, llm_client: GroqClient):
        super().__init__(name="technical_analysis", llm_client=llm_client)
    
    async def analyze(self, request: AgentRequest) -> dict[str, Any]:
        """
        Perform technical analysis on signal.
        
        Returns:
            {
                "reasoning": str,
                "confidence": int,
                "metadata": dict,
                "tokens_used": int,
                "model_used": str
            }
        """
        
        # Extract signal data
        signal_data = request.signal_data
        price = signal_data.get("price", 0)
        support = signal_data.get("support", price * 0.98)
        resistance = signal_data.get("resistance", price * 1.02)
        volume = signal_data.get("volume", 0)
        avg_volume = signal_data.get("avg_volume", volume)
        
        # Build context
        signal_guidance = get_signal_guidance(request.signal_type)
        volume_ratio = round(volume / avg_volume, 2) if avg_volume > 0 else 1.0
        
        context = f"{signal_guidance}\nVolume Ratio: {volume_ratio}x average"
        
        # Build prompt
        prompt = TECHNICAL_ANALYSIS_PROMPT.format(
            symbol=request.symbol,
            signal_type=request.signal_type,
            price=price,
            support=support,
            resistance=resistance,
            volume=volume,
            avg_volume=avg_volume,
            context=context
        )
        
        # Call LLM
        try:
            llm_response = await self.llm.generate(
                prompt=prompt,
                model="llama-3.3-70b-versatile",
                temperature=0.3,
                max_tokens=500,
                timeout=15
            )
            
            # Parse JSON response
            analysis = self._parse_llm_response(llm_response["content"])
            
            # Build result
            confidence = analysis.get("confidence", 50)
            reasoning = analysis.get("reasoning", "Technical analysis completed")
            
            # Add fallback validation
            if confidence < 0 or confidence > 100:
                self.logger.warning(f"Invalid confidence {confidence}, clamping to range")
                confidence = max(0, min(100, confidence))
            
            metadata = {
                "pattern": analysis.get("pattern", "unknown"),
                "trend_strength": analysis.get("trend_strength", "moderate"),
                "volume_confirmation": analysis.get("volume_confirmation", "partial"),
                "level_strength": analysis.get("level_strength", "moderate"),
                "key_risks": analysis.get("key_risks", []),
                "volume_ratio": volume_ratio,
                "support": support,
                "resistance": resistance
            }
            
            return {
                "reasoning": reasoning,
                "confidence": confidence,
                "metadata": metadata,
                "tokens_used": llm_response.get("tokens_total", 0),
                "model_used": llm_response.get("model", "llama-3.3-70b-versatile")
            }
            
        except Exception as e:
            self.logger.error(f"LLM call failed: {e}")
            # Fallback to deterministic analysis
            return self._deterministic_analysis(request, volume_ratio, support, resistance)
    
    def _parse_llm_response(self, content: str) -> dict:
        """Parse LLM JSON response"""
        try:
            # Try to extract JSON from response
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
    
    def _deterministic_analysis(
        self,
        request: AgentRequest,
        volume_ratio: float,
        support: float,
        resistance: float
    ) -> dict[str, Any]:
        """
        Fallback deterministic analysis when LLM fails.
        
        Simple rule-based confidence scoring.
        """
        signal_type = request.signal_type
        
        # Base confidence by signal type
        base_confidence = {
            "PDH_BREAKOUT": 65,
            "PDL_BREAKDOWN": 65,
            "PDH_REJECTION": 55,
            "PDL_REJECTION": 55,
            "RANGE_BREAKOUT": 60,
            "TREND_CONTINUATION": 70
        }.get(signal_type, 50)
        
        # Volume adjustment
        if volume_ratio > 1.5:
            base_confidence += 10
        elif volume_ratio < 0.7:
            base_confidence -= 10
        
        # Clamp confidence
        confidence = max(30, min(85, base_confidence))
        
        reasoning = (
            f"Technical signal {signal_type} for {request.symbol}. "
            f"Volume ratio: {volume_ratio}x. "
            f"Price levels: S={support:.2f}, R={resistance:.2f}."
        )
        
        metadata = {
            "pattern": signal_type.lower().replace("_", " "),
            "trend_strength": "strong" if volume_ratio > 1.5 else "moderate",
            "volume_confirmation": "confirmed" if volume_ratio > 1.3 else "partial",
            "level_strength": "moderate",
            "key_risks": ["Low volume"] if volume_ratio < 0.7 else [],
            "volume_ratio": volume_ratio,
            "support": support,
            "resistance": resistance,
            "fallback": True
        }
        
        self.logger.info(f"Using deterministic analysis: confidence={confidence}")
        
        return {
            "reasoning": reasoning,
            "confidence": confidence,
            "metadata": metadata,
            "tokens_used": None,
            "model_used": None
        }
