"""
Base Agent Framework

Abstract base class for all AI agents.
"""

import time
from abc import ABC, abstractmethod
from typing import Any

from app.core.schemas import AgentRequest, AgentResponse
from app.core.logging import get_logger
from app.integrations.groq_client import GroqClient
from app.monitoring.metrics import metrics

logger = get_logger(__name__)


class BaseAgent(ABC):
    """
    Abstract base class for all agents.
    
    Provides:
    - Logging hooks
    - Metrics hooks
    - Error handling
    - Execution timing
    """
    
    def __init__(self, name: str, llm_client: GroqClient):
        self.name = name
        self.llm = llm_client
        self.logger = get_logger(f"agent.{name}")
    
    @abstractmethod
    async def analyze(self, request: AgentRequest) -> dict[str, Any]:
        """
        Core agent logic - must be implemented by subclasses.
        
        Args:
            request: Agent request with signal data and context
        
        Returns:
            dict with analysis results (reasoning, confidence, metadata)
        """
        pass
    
    async def execute(self, request: AgentRequest) -> AgentResponse:
        """
        Execute agent with timing, logging, and error handling.
        
        This method wraps the agent's analyze() method with:
        - Execution timing
        - Structured logging
        - Error handling
        - Metrics collection
        """
        start_time = time.time()
        
        self.logger.info(
            f"Starting analysis for {request.symbol} ({request.signal_type})"
        )
        
        try:
            # Run agent analysis
            result = await self.analyze(request)
            
            # Calculate latency
            latency_ms = int((time.time() - start_time) * 1000)
            
            # Extract standard fields
            reasoning = result.get("reasoning", "")
            confidence = result.get("confidence", 50)
            metadata = result.get("metadata", {})
            tokens_used = result.get("tokens_used")
            model_used = result.get("model_used")
            
            self.logger.info(
                f"Analysis complete: confidence={confidence}%, latency={latency_ms}ms"
            )
            
            # Record metrics
            metrics.record_agent_execution(
                agent_name=self.name,
                success=True,
                latency_seconds=latency_ms / 1000.0,
                confidence=confidence
            )
            
            return AgentResponse(
                agent_name=self.name,
                success=True,
                reasoning=reasoning,
                confidence=confidence,
                metadata=metadata,
                latency_ms=latency_ms,
                tokens_used=tokens_used,
                llm_model=model_used,
                error=None
            )
            
        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)
            error_msg = str(e)
            
            self.logger.error(
                f"Analysis failed: {error_msg}",
                exc_info=True
            )
            
            # Record metrics
            metrics.record_agent_execution(
                agent_name=self.name,
                success=False,
                latency_seconds=latency_ms / 1000.0,
                confidence=0
            )
            
            return AgentResponse(
                agent_name=self.name,
                success=False,
                reasoning="",
                confidence=0,
                metadata={},
                latency_ms=latency_ms,
                tokens_used=None,
                llm_model=None,
                error=error_msg
            )
    
    def _build_prompt(self, template: str, **kwargs) -> str:
        """
        Build prompt from template with variable substitution.
        
        Args:
            template: Prompt template string
            **kwargs: Variables to substitute
        
        Returns:
            Formatted prompt string
        """
        try:
            return template.format(**kwargs)
        except KeyError as e:
            self.logger.error(f"Prompt template missing variable: {e}")
            raise
