"""
News Agent Usage Example

Demonstrates how to use the News Intelligence Agent.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.agents.news_agent import NewsAgent
from app.core.schemas import AgentRequest
from app.integrations.groq_client import GroqClient
from app.core.logging import setup_logging, get_logger

setup_logging()
logger = get_logger(__name__)


async def main():
    """Example usage of News Agent"""
    
    # Initialize agent
    logger.info("Initializing News Intelligence Agent...")
    llm_client = GroqClient()
    agent = NewsAgent(llm_client=llm_client)
    
    # Example 1: Positive News
    logger.info("\n--- Example 1: Positive News ---")
    request = AgentRequest(
        symbol="RELIANCE",
        signal_type="PDH_BREAKOUT",
        context={
            "news": [
                {
                    "headline": "Reliance Industries posts record quarterly profit",
                    "source": "Economic Times"
                },
                {
                    "headline": "Strong growth in digital services segment",
                    "source": "Moneycontrol"
                },
                {
                    "headline": "Reliance expands retail footprint",
                    "source": "Yahoo Finance"
                }
            ]
        }
    )
    
    response = await agent.execute(request)
    
    logger.info(f"Success: {response.success}")
    logger.info(f"Confidence: {response.confidence}%")
    logger.info(f"Sentiment: {response.metadata.get('sentiment')}")
    logger.info(f"Impact: {response.metadata.get('impact')}")
    logger.info(f"Reasoning: {response.reasoning}")
    logger.info(f"Latency: {response.latency_ms}ms")
    
    # Example 2: Negative News
    logger.info("\n--- Example 2: Negative News ---")
    request = AgentRequest(
        symbol="INFY",
        signal_type="PDL_BREAKDOWN",
        context={
            "news": [
                {
                    "headline": "Infosys faces attrition challenges",
                    "source": "Economic Times"
                },
                {
                    "headline": "Client project delays impact revenue",
                    "source": "Moneycontrol"
                }
            ]
        }
    )
    
    response = await agent.execute(request)
    
    logger.info(f"Sentiment: {response.metadata.get('sentiment')}")
    logger.info(f"Risks: {response.metadata.get('risks', [])}")
    logger.info(f"Confidence: {response.confidence}%")
    
    # Example 3: No News
    logger.info("\n--- Example 3: No News Available ---")
    request = AgentRequest(
        symbol="TCS",
        signal_type="RANGE_BREAKOUT",
        context={"news": []}
    )
    
    response = await agent.execute(request)
    
    logger.info(f"Sentiment: {response.metadata.get('sentiment')}")
    logger.info(f"Confidence: {response.confidence}%")
    logger.info(f"Reasoning: {response.reasoning}")
    
    logger.info("\n✓ News Agent examples completed")


if __name__ == "__main__":
    asyncio.run(main())
