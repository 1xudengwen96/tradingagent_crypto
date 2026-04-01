# tradingagents/agents/risk_mgmt/crypto_aggressive_debator.py
"""
加密货币激进风险分析师
倡导更高杠杆、更大仓位的激进策略，强调潜在收益。
"""


def create_crypto_aggressive_debator(llm):
    def aggressive_node(state) -> dict:
        risk_debate_state = state["risk_debate_state"]
        history = risk_debate_state.get("history", "")
        aggressive_history = risk_debate_state.get("aggressive_history", "")

        current_conservative_response = risk_debate_state.get("current_conservative_response", "")
        current_neutral_response = risk_debate_state.get("current_neutral_response", "")

        market_report = state["market_report"]
        sentiment_report = state["sentiment_report"]
        news_report = state["news_report"]
        onchain_report = state["fundamentals_report"]

        trader_decision = state["trader_investment_plan"]
        symbol = state["company_of_interest"]

        prompt = f"""You are the Aggressive Risk Analyst on a crypto trading desk specializing in {symbol} perpetual futures. Your role is to advocate for a bold, high-conviction approach that maximizes returns from the current setup.

**The Trader's Proposed Decision:**
{trader_decision}

**Your Aggressive Stance:**
- **Leverage**: Argue for higher leverage (e.g., 10x-20x) if the setup is strong. Technical setups with clear invalidation points justify higher leverage since risk is defined.
- **Position Size**: Advocate for meaningful position sizes (20-40% of capital) when conviction is high.
- **Risk/Reward**: Emphasize that the risk/reward ratio justifies the position — if the stop is tight and the target is large, the math works.
- **Crypto-Specific Upside**: In crypto, 10-30% moves happen in hours. Missing a strong setup costs more than a controlled loss.
- **Funding Rate Advantage**: If funding favors the position direction, the carry is free money — this amplifies the case for higher size.
- **Counter the Conservative View**: Point out where excessive caution means leaving money on the table. Challenge overly tight stop-losses or undersized positions.
- **Counter the Neutral View**: Show why a "balanced" approach is suboptimal when the signal is clear.

**Data to Reference:**
Market Technical Analysis: {market_report}
Sentiment Analysis: {sentiment_report}
Macro News: {news_report}
Market Microstructure: {onchain_report}
Debate History: {history}
Last Conservative Argument: {current_conservative_response}
Last Neutral Argument: {current_neutral_response}

Make your case for why the aggressive approach—higher leverage, larger position—is justified here. Be specific with numbers. Output conversationally without special formatting."""

        response = llm.invoke(prompt)
        argument = f"Aggressive Analyst: {response.content}"

        new_risk_debate_state = {
            "history": history + "\n" + argument,
            "aggressive_history": aggressive_history + "\n" + argument,
            "conservative_history": risk_debate_state.get("conservative_history", ""),
            "neutral_history": risk_debate_state.get("neutral_history", ""),
            "latest_speaker": "Aggressive",
            "current_aggressive_response": argument,
            "current_conservative_response": risk_debate_state.get("current_conservative_response", ""),
            "current_neutral_response": risk_debate_state.get("current_neutral_response", ""),
            "count": risk_debate_state["count"] + 1,
        }

        return {"risk_debate_state": new_risk_debate_state}

    return aggressive_node
