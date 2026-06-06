"""
Example: Decision Agent Usage

Demonstrates how to use DecisionAgent to synthesize technical and news analysis
into final trading recommendations.
"""

import asyncio
from app.agents.decision_agent import DecisionAgent
from app.core.schemas import AgentRequest, AgentResponse
from app.integrations.groq_client import GroqClient


async def main():
    """Example decision agent workflow"""
    
    # Initialize Groq client and Decision Agent
    groq_client = GroqClient()
    decision_agent = DecisionAgent(llm_client=groq_client)
    
    # Mock technical agent output (bullish)
    technical_output = AgentResponse(
        agent_name="technical_analysis",
        success=True,
        reasoning="Strong bullish breakout above PDH with high volume confirmation. Price holding above resistance turned support.",
        confidence=75,
        metadata={
            "pattern": "breakout",
            "trend_strength": "strong",
            "volume_confirmation": "confirmed",
            "level_strength": "strong",
            "key_risks": ["Overbought RSI"],
            "volume_ratio": 1.8,
            "support": 19450.0,
            "resistance": 19580.0
        },
        latency_ms=150,
        tokens_used=200,
        model_used="llama-3.3-70b-versatile"
    )
    
    # Mock news agent output (positive)
    news_output = AgentResponse(
        agent_name="news_intelligence",
        success=True,
        reasoning="Positive sentiment from strong earnings and FII buying. Sector outlook improved with government policy support.",
        confidence=65,
        metadata={
            "sentiment": "positive",
            "impact": "high",
            "relevance": "relevant",
            "key_signals": ["Strong earnings", "FII buying", "Policy support"],
            "risks": ["Global market uncertainty"]
        },
        latency_ms=200,
        tokens_used=180,
        model_used="deepseek-r1-distill-llama-70b"
    )
    
    # Mock enrichment output (bullish indicators)
    enrichment = {
        "ema_20": 19420.5,
        "ema_50": 19350.2,
        "ema_200": 19100.8,
        "ema_trend": "bullish",
        "rsi": 67.5,
        "rsi_signal": "neutral",
        "macd": 45.2,
        "macd_signal": 38.1,
        "macd_histogram": 7.1,
        "macd_trend": "bullish",
        "vwap": 19480.0,
        "vwap_position": "above",
        "atr": 85.3,
        "volume_ratio": 1.8,
        "volume_signal": "high"
    }
    
    # Create agent request with context
    request = AgentRequest(
        symbol="NIFTY",
        signal_type="PDH_BREAKOUT",
        signal_data={
            "price": 19520.0,
            "support": 19450.0,
            "resistance": 19580.0,
            "volume": 1800000,
            "avg_volume": 1000000
        },
        context={
            "technical_agent": technical_output,
            "news_agent": news_output,
            "enrichment": enrichment
        }
    )
    
    # Execute decision agent
    print("=" * 60)
    print("DECISION AGENT EXAMPLE")
    print("=" * 60)
    print(f"\nSymbol: {request.symbol}")
    print(f"Signal: {request.signal_type}")
    print(f"Price: ₹{request.signal_data['price']}")
    
    print(f"\n{'Technical Analysis':-^60}")
    print(f"Confidence: {technical_output.confidence}%")
    print(f"Reasoning: {technical_output.reasoning}")
    
    print(f"\n{'News Intelligence':-^60}")
    print(f"Confidence: {news_output.confidence}%")
    print(f"Sentiment: {news_output.metadata['sentiment'].upper()}")
    print(f"Reasoning: {news_output.reasoning}")
    
    print(f"\n{'Market Indicators':-^60}")
    print(f"EMA Trend: {enrichment['ema_trend'].upper()}")
    print(f"RSI: {enrichment['rsi']} ({enrichment['rsi_signal']})")
    print(f"MACD: {enrichment['macd_trend'].upper()}")
    print(f"Volume: {enrichment['volume_signal'].upper()} ({enrichment['volume_ratio']}x)")
    
    print(f"\n{'Synthesizing Decision...':-^60}")
    
    # Get decision
    result = await decision_agent.analyze(request)
    
    print(f"\n{'FINAL RECOMMENDATION':-^60}")
    print(f"Action: {result['recommendation']}")
    print(f"Confidence: {result['confidence']}%")
    print(f"Risk Level: {result['metadata']['risk_level'].upper()}")
    print(f"\nReasoning:")
    print(f"  {result['reasoning']}")
    
    if result['metadata'].get('key_factors'):
        print(f"\nKey Factors:")
        for factor in result['metadata']['key_factors']:
            print(f"  • {factor}")
    
    if result['metadata'].get('conflicts'):
        print(f"\nConflicts: {result['metadata']['conflicts']}")
    
    if result.get('model_used'):
        print(f"\nModel: {result['model_used']}")
        print(f"Tokens: {result['tokens_used']}")
    
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
