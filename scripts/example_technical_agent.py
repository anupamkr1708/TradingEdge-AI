"""
Technical Agent Usage Example

Demonstrates how to use the Technical Analysis Agent.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.agents.technical_agent import TechnicalAgent
from app.core.schemas import AgentRequest
from app.integrations.groq_client import GroqClient
from app.core.logging import setup_logging, get_logger

setup_logging()
logger = get_logger(__name__)


async def main():
    """Example usage of Technical Agent"""
    
    # Initialize agent
    logger.info("Initializing Technical Agent...")
    llm_client = GroqClient()
    agent = TechnicalAgent(llm_client=llm_client)
    
    # Example 1: PDH Breakout
    logger.info("\n--- Example 1: PDH Breakout ---")
    request = AgentRequest(
        symbol="RELIANCE",
        signal_type="PDH_BREAKOUT",
        signal_data={
            "price": 2550.50,
            "support": 2520.00,
            "resistance": 2580.00,
            "volume": 1500000,
            "avg_volume": 1000000
        }
    )
    
    response = await agent.execute(request)
    
    logger.info(f"Success: {response.success}")
    logger.info(f"Confidence: {response.confidence}%")
    logger.info(f"Reasoning: {response.reasoning}")
    logger.info(f"Latency: {response.latency_ms}ms")
    logger.info(f"Metadata: {response.metadata}")
    
    # Example 2: PDL Breakdown (Low Volume)
    logger.info("\n--- Example 2: PDL Breakdown (Low Volume) ---")
    request = AgentRequest(
        symbol="INFY",
        signal_type="PDL_BREAKDOWN",
        signal_data={
            "price": 1420.75,
            "support": 1415.00,
            "resistance": 1450.00,
            "volume": 600000,
            "avg_volume": 1000000
        }
    )
    
    response = await agent.execute(request)
    
    logger.info(f"Success: {response.success}")
    logger.info(f"Confidence: {response.confidence}%")
    logger.info(f"Reasoning: {response.reasoning}")
    logger.info(f"Key Risks: {response.metadata.get('key_risks', [])}")
    
    logger.info("\n✓ Technical Agent examples completed")


if __name__ == "__main__":
    asyncio.run(main())
