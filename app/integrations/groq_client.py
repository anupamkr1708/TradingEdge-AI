"""
Groq LLM Client

Client for Groq API with Llama 3.3 support.
"""

import hashlib
import json
import time
from typing import Literal
from groq import Groq, RateLimitError, APIError

from app.core.config import settings
from app.core.logging import get_logger
from app.integrations.redis_client import get_redis_sync
from app.monitoring.metrics import metrics

logger = get_logger(__name__)


ModelType = Literal["llama-3.3-70b-versatile", "llama-3.1-8b-instant"]


class GroqClient:
    """Client for Groq API with caching and retry logic"""
    
    # Model pricing per 1M tokens (input/output in USD)
    PRICING = {
        "llama-3.3-70b-versatile": {"input": 0.59, "output": 0.79},
        "llama-3.1-8b-instant": {"input": 0.05, "output": 0.08},
    }
    
    # Primary and fallback models
    PRIMARY_MODEL = "llama-3.3-70b-versatile"
    FALLBACK_MODEL = "llama-3.1-8b-instant"
    
    def __init__(self):
        if not hasattr(settings, 'GROQ_API_KEY'):
            raise ValueError("GROQ_API_KEY not found in settings")
        
        self.client = Groq(api_key=settings.GROQ_API_KEY)
        self.redis = get_redis_sync()
    
    async def generate(
        self,
        prompt: str,
        model: ModelType = "llama-3.3-70b-versatile",
        temperature: float = 0.3,
        max_tokens: int = 500,
        timeout: int = 30,
        use_cache: bool = True
    ) -> dict:
        """
        Generate LLM response with caching and retry.
        
        Returns:
            {
                "content": str,
                "tokens_input": int,
                "tokens_output": int,
                "tokens_total": int,
                "model": str,
                "cached": bool,
                "cost_usd": float
            }
        """
        start_time = time.time()
        
        # Check cache
        if use_cache:
            cached = self._get_cached(prompt, model, temperature)
            if cached:
                logger.info(f"LLM cache hit for model={model}")
                latency_ms = int((time.time() - start_time) * 1000)
                metrics.record_cache_operation("llm", "hit")
                return {**cached, "cached": True, "latency_ms": latency_ms}
        
        # Call API with retry
        try:
            response = await self._call_with_retry(
                prompt=prompt,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=timeout
            )
            
            latency_ms = int((time.time() - start_time) * 1000)
            
            # Calculate cost
            cost_usd = self._calculate_cost(
                model=model,
                tokens_input=response["tokens_input"],
                tokens_output=response["tokens_output"]
            )
            
            result = {
                "content": response["content"],
                "tokens_input": response["tokens_input"],
                "tokens_output": response["tokens_output"],
                "tokens_total": response["tokens_total"],
                "model": model,
                "cached": False,
                "cost_usd": cost_usd,
                "latency_ms": latency_ms
            }
            
            # Cache response
            if use_cache:
                self._set_cached(prompt, model, temperature, result)
                metrics.record_cache_operation("llm", "miss")
            
            # Record metrics
            logger.info(
                f"LLM response: model={model}, tokens={response['tokens_total']}, "
                f"cost=${cost_usd:.4f}, latency={latency_ms}ms"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            raise
    
    async def _call_with_retry(
        self,
        prompt: str,
        model: str,
        temperature: float,
        max_tokens: int,
        timeout: int,
        max_retries: int = 2
    ) -> dict:
        """Call Groq API with exponential backoff retry"""
        
        # Run sync Groq client in executor to avoid blocking event loop
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, 
            self._call_with_retry_sync,
            prompt,
            model,
            temperature,
            max_tokens,
            timeout,
            max_retries
        )
    
    def _call_with_retry_sync(
        self,
        prompt: str,
        model: str,
        temperature: float,
        max_tokens: int,
        timeout: int,
        max_retries: int = 2
    ) -> dict:
        """Synchronous Groq API call with retry and fallback logic"""
        
        models_to_try = [model]
        # Add fallback model if primary model fails with rate limit
        if model == self.PRIMARY_MODEL and self.FALLBACK_MODEL not in models_to_try:
            models_to_try.append(self.FALLBACK_MODEL)
        
        for model_attempt in models_to_try:
            for attempt in range(max_retries + 1):
                try:
                    response = self.client.chat.completions.create(
                        model=model_attempt,
                        messages=[{"role": "user", "content": prompt}],
                        temperature=temperature,
                        max_tokens=max_tokens,
                        timeout=timeout
                    )
                    
                    if model_attempt != model:
                        logger.info(f"Used fallback model: {model_attempt}")
                    
                    return {
                        "content": response.choices[0].message.content,
                        "tokens_input": response.usage.prompt_tokens,
                        "tokens_output": response.usage.completion_tokens,
                        "tokens_total": response.usage.total_tokens
                    }
                    
                except RateLimitError as e:
                    if attempt < max_retries:
                        wait_time = 2 ** attempt
                        logger.warning(f"Rate limit on {model_attempt}, retry {attempt+1}/{max_retries} in {wait_time}s")
                        time.sleep(wait_time)
                    elif model_attempt != models_to_try[-1]:
                        logger.warning(f"Rate limit exhausted on {model_attempt}, trying fallback")
                        break
                    else:
                        logger.error("Rate limit exceeded on all models")
                        raise
                
                except APIError as e:
                    if e.status_code >= 500 and attempt < max_retries:
                        wait_time = 1
                        logger.warning(f"API error {e.status_code} on {model_attempt}, retrying...")
                        time.sleep(wait_time)
                    else:
                        raise
    
    def _calculate_cost(self, model: str, tokens_input: int, tokens_output: int) -> float:
        """Calculate cost in USD"""
        pricing = self.PRICING.get(model, {"input": 0, "output": 0})
        cost = (tokens_input * pricing["input"] + tokens_output * pricing["output"]) / 1_000_000
        return round(cost, 6)
    
    def _get_cache_key(self, prompt: str, model: str, temperature: float) -> str:
        """Generate cache key"""
        key_data = f"{prompt}|{model}|{temperature}"
        return f"llm:{hashlib.md5(key_data.encode()).hexdigest()}"
    
    def _get_cached(self, prompt: str, model: str, temperature: float) -> dict | None:
        """Get cached response"""
        if not self.redis:
            return None
        
        try:
            key = self._get_cache_key(prompt, model, temperature)
            cached = self.redis.get(key)
            if cached:
                return json.loads(cached)
        except Exception as e:
            logger.warning(f"Cache get failed: {e}")
        
        return None
    
    def _set_cached(self, prompt: str, model: str, temperature: float, response: dict):
        """Cache response for 30 minutes"""
        if not self.redis:
            return
        
        try:
            key = self._get_cache_key(prompt, model, temperature)
            self.redis.setex(key, 1800, json.dumps(response))  # 30 min TTL
        except Exception as e:
            logger.warning(f"Cache set failed: {e}")


# Global instance
groq_client = GroqClient()
