"""
Technical Analysis Prompts

Prompt templates for technical analysis agent.
"""


TECHNICAL_ANALYSIS_PROMPT = """You are a technical analysis expert for Indian F&O markets.

SIGNAL DETAILS:
Symbol: {symbol}
Signal Type: {signal_type}
Price: {price}
Support Level: {support}
Resistance Level: {resistance}
Volume: {volume}
Average Volume: {avg_volume}

CONTEXT:
{context}

TASK:
Analyze this technical signal and provide:

1. Pattern Analysis: What technical pattern is forming?
2. Trend Strength: Is the trend strong, weak, or neutral?
3. Volume Confirmation: Does volume support the signal?
4. Level Strength: Are support/resistance levels significant?
5. Risk Assessment: What are the key risks?

Provide your analysis in the following JSON format:
{{
  "pattern": "description of pattern",
  "trend_strength": "strong/moderate/weak",
  "volume_confirmation": "confirmed/partial/weak",
  "level_strength": "strong/moderate/weak",
  "key_risks": ["risk1", "risk2"],
  "reasoning": "brief technical reasoning (2-3 sentences)",
  "confidence": 0-100
}}

Be concise and actionable. Confidence should reflect signal quality and market conditions.
"""


SIGNAL_TYPE_GUIDANCE = {
    "PDH_BREAKOUT": "Bullish breakout above previous day high. Check volume and momentum.",
    "PDL_BREAKDOWN": "Bearish breakdown below previous day low. Verify volume surge.",
    "PDH_REJECTION": "Price rejected at PDH resistance. Potential reversal signal.",
    "PDL_REJECTION": "Price rejected at PDL support. Potential bounce signal.",
    "RANGE_BREAKOUT": "Price breaking out of consolidation range.",
    "TREND_CONTINUATION": "Signal in direction of existing trend.",
}


def get_signal_guidance(signal_type: str) -> str:
    """Get guidance for signal type"""
    return SIGNAL_TYPE_GUIDANCE.get(signal_type, "Analyze price action and volume patterns.")
