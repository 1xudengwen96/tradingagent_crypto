# tradingagents/agents/researchers/crypto_bull_researcher.py
"""
加密货币多头研究员
专注于为 BTC/ETH 永续合约构建做多的论据：技术突破、链上积累、宏观顺风等。
"""


def create_crypto_bull_researcher(llm, memory):
    def bull_node(state) -> dict:
        investment_debate_state = state["investment_debate_state"]
        history = investment_debate_state.get("history", "")
        bull_history = investment_debate_state.get("bull_history", "")

        current_response = investment_debate_state.get("current_response", "")
        market_research_report = state["market_report"]
        sentiment_report = state["sentiment_report"]
        news_report = state["news_report"]
        onchain_report = state["fundamentals_report"]  # onchain/microstructure

        symbol = state["company_of_interest"]

        curr_situation = f"{market_research_report}\n\n{sentiment_report}\n\n{news_report}\n\n{onchain_report}"
        past_memories = memory.get_memories(curr_situation, n_matches=2)

        past_memory_str = ""
        for i, rec in enumerate(past_memories, 1):
            past_memory_str += rec["recommendation"] + "\n\n"

        prompt = f"""You are a Crypto Bull Analyst making the case for opening or holding a LONG position on {symbol} perpetual futures.

Your goal is to build a compelling, evidence-based argument for the bullish case, emphasizing:

**Bullish Arguments to Develop:**
- **Technical Breakout Signals**: Price above key moving averages, MACD crossover, RSI not overbought, Bollinger squeeze breakout
- **Favorable Funding Rate**: Negative or near-zero funding means holding longs is cheap or even profitable; suggests market is not overextended long
- **Open Interest Dynamics**: Rising OI with rising price = strong trend; or falling OI as shorts are squeezed out
- **Order Book Strength**: Strong bid wall support levels, favorable bid/ask ratio
- **Sentiment Catalysts**: Positive news, ETF inflows, institutional accumulation, on-chain accumulation signals
- **Macro Tailwinds**: Risk-on environment, weak DXY, favorable macro for crypto
- **Liquidation Cascade Potential**: Short squeeze potential if price breaks key resistance

**Debate Instructions:**
- Directly counter each bearish argument with specific data from the reports
- Use exact price levels, percentages, and indicator readings to strengthen your case
- Point out where the bear analyst is being overly cautious or missing key signals
- Argue conversationally and persuasively, not just listing facts
- Apply lessons from past mistakes: {past_memory_str}

**Resources:**
Market Technical Report: {market_research_report}
Sentiment Report: {sentiment_report}
Macro News Report: {news_report}
Market Microstructure Report: {onchain_report}
Debate History: {history}
Last Bear Argument: {current_response}

Build a strong bull case for {symbol}. Focus on why LONG is the right direction now.
"""

        response = llm.invoke(prompt)
        argument = f"Bull Analyst: {response.content}"

        new_investment_debate_state = {
            "history": history + "\n" + argument,
            "bull_history": bull_history + "\n" + argument,
            "bear_history": investment_debate_state.get("bear_history", ""),
            "current_response": argument,
            "count": investment_debate_state["count"] + 1,
        }

        return {"investment_debate_state": new_investment_debate_state}

    return bull_node
