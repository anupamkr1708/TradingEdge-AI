"""
News Intelligence Prompts

Prompt templates for news sentiment analysis agent.
"""


NEWS_ANALYSIS_PROMPT = """You are a financial news analyst for Indian equity markets.

SYMBOL: {symbol}

NEWS HEADLINES:
{headlines}

TASK:
Analyze the sentiment and impact of these news items on {symbol}.

Provide your analysis in the following JSON format:
{{
  "sentiment": "positive/neutral/negative",
  "impact": "high/medium/low",
  "relevance": "relevant/partially_relevant/irrelevant",
  "key_signals": ["signal1", "signal2"],
  "risks": ["risk1", "risk2"],
  "reasoning": "brief explanation (2-3 sentences)",
  "confidence": 0-100
}}

Consider:
- Earnings reports and guidance
- Management commentary
- Regulatory news
- Sector trends
- Market sentiment

Be objective and concise. Confidence reflects certainty of sentiment and impact assessment.
"""


NEWS_ANALYSIS_PROMPT_DEEPSEEK = """You are a financial news analyst. Analyze sentiment for {symbol}.

NEWS:
{headlines}

Respond with JSON:
{{
  "sentiment": "positive/neutral/negative",
  "impact": "high/medium/low",
  "relevance": "relevant/partially_relevant/irrelevant",
  "key_signals": ["list"],
  "risks": ["list"],
  "reasoning": "brief analysis",
  "confidence": 0-100
}}

Focus on financial impact. Be concise.
"""


def format_headlines(news_items: list[dict]) -> str:
    """Format news headlines for prompt"""
    if not news_items:
        return "No recent news available."
    
    formatted = []
    for i, item in enumerate(news_items[:5], 1):  # Max 5 headlines
        headline = item.get("headline", "")
        source = item.get("source", "Unknown")
        formatted.append(f"{i}. [{source}] {headline}")
    
    return "\n".join(formatted)
