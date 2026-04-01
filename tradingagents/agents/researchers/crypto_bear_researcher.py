# tradingagents/agents/researchers/crypto_bear_researcher.py
"""
加密货币空头研究员
专注于为 BTC/ETH 永续合约构建做空的论据：技术破位、流动性枯竭、宏观逆风等。
"""


def create_crypto_bear_researcher(llm, memory):
    def bear_node(state) -> dict:
        investment_debate_state = state["investment_debate_state"]
        history = investment_debate_state.get("history", "")
        bear_history = investment_debate_state.get("bear_history", "")

        current_response = investment_debate_state.get("current_response", "")
        market_research_report = state["market_report"]
        sentiment_report = state["sentiment_report"]
        news_report = state["news_report"]
        onchain_report = state["fundamentals_report"]

        symbol = state["company_of_interest"]

        curr_situation = f"{market_research_report}\n\n{sentiment_report}\n\n{news_report}\n\n{onchain_report}"
        past_memories = memory.get_memories(curr_situation, n_matches=2)

        past_memory_str = ""
        for i, rec in enumerate(past_memories, 1):
            past_memory_str += rec["recommendation"] + "\n\n"

        prompt = f"""You are a Crypto Bear Analyst making the case for opening or holding a SHORT position on {symbol} perpetual futures.

Your goal is to build a compelling, evidence-based argument for the bearish case, emphasizing:

**Bearish Arguments to Develop:**
- **Technical Breakdown Signals**: Price below key moving averages, MACD bearish crossover, RSI overbought divergence, Bollinger Band rejection at upper band
- **Dangerous Funding Rate**: High positive funding means longs are paying heavily—overleveraged longs are vulnerable to cascade liquidation
- **Open Interest Warning Signs**: OI rising while price struggles = trapped longs; declining OI with declining price = accelerating selloff
- **Order Book Weakness**: Large ask walls as resistance, poor bid depth below current price
- **Sentiment Exhaustion**: FOMO-driven highs, extreme greed readings, whale distribution signals
- **Macro Headwinds**: Risk-off environment, strong DXY, regulatory pressure, Fed tightening
- **Liquidation Cascade Risk**: Crowded long side means a drop could trigger cascading long liquidations

**Debate Instructions:**
- Directly counter each bullish argument with specific data from the reports
- Use exact price levels, percentages, and indicator readings
- Point out where the bull analyst is being overly optimistic or ignoring downside risks
- Argue conversationally and persuasively
- Apply lessons from past mistakes: {past_memory_str}

**Resources:**
Market Technical Report: {market_research_report}
Sentiment Report: {sentiment_report}
Macro News Report: {news_report}
Market Microstructure Report: {onchain_report}
Debate History: {history}
Last Bull Argument: {current_response}

Build a strong bear case for {symbol}. Focus on why SHORT or CLOSE LONG is the right move now.
"""

        response = llm.invoke(prompt)
        argument = f"Bear Analyst: {response.content}"

        new_investment_debate_state = {
            "history": history + "\n" + argument,
            "bear_history": bear_history + "\n" + argument,
            "bull_history": investment_debate_state.get("bull_history", ""),
            "current_response": argument,
            "count": investment_debate_state["count"] + 1,
        }

        return {"investment_debate_state": new_investment_debate_state}

    return bear_node
