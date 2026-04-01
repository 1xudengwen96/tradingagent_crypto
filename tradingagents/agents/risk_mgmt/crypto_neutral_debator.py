# tradingagents/agents/risk_mgmt/crypto_neutral_debator.py
"""
加密货币中立风险分析师
在激进和保守之间寻求平衡，倡导适中杠杆和动态仓位管理。
"""


def create_crypto_neutral_debator(llm):
    def neutral_node(state) -> dict:
        risk_debate_state = state["risk_debate_state"]
        history = risk_debate_state.get("history", "")
        neutral_history = risk_debate_state.get("neutral_history", "")

        current_aggressive_response = risk_debate_state.get("current_aggressive_response", "")
        current_conservative_response = risk_debate_state.get("current_conservative_response", "")

        market_report = state["market_report"]
        sentiment_report = state["sentiment_report"]
        news_report = state["news_report"]
        onchain_report = state["fundamentals_report"]

        trader_decision = state["trader_investment_plan"]
        symbol = state["company_of_interest"]

        prompt = f"""You are the Neutral Risk Analyst on a crypto trading desk specializing in {symbol} perpetual futures. Your role is to provide a balanced, data-driven perspective that balances return potential with capital preservation.

**The Trader's Proposed Decision:**
{trader_decision}

**Your Balanced Stance:**
- **Calibrated Leverage**: Recommend leverage proportional to the ATR (volatility). Rule of thumb: leverage = 1 / (ATR% × 2). For a 2% ATR, suggest max 10x leverage. For a 5% ATR, max 4-5x.
- **Scaled Position Entry**: Suggest entering in 2-3 tranches rather than all at once. This reduces risk if entry timing is slightly off.
- **Dynamic Stop-Loss**: Use ATR-based stop-losses (1.5-2× ATR from entry) rather than arbitrary percentages.
- **Take-Profit Laddering**: Partial profit-taking at TP1 (50% of position), letting remaining run to TP2/TP3.
- **Funding Rate Management**: If funding is strongly positive (longs paying shorts), consider reducing position size or waiting for funding to normalize before entering long.
- **Counter the Aggressive View**: Challenge positions that don't properly account for crypto's extreme volatility regime. High leverage is acceptable only when ATR is low and the setup is textbook perfect.
- **Counter the Conservative View**: Overly conservative sizing means risk-adjusted returns are too low for a crypto trading operation. Some leverage is necessary for meaningful returns.

**Balanced Recommendation Framework:**
- Leverage: 5x-10x (depending on current volatility)
- Position size: 15-25% of capital
- Entry: Scale in gradually
- Stop-loss: ATR-based, 1.5-2× ATR from entry
- Take-profit: Laddered exits

**Data to Reference:**
Market Technical Analysis: {market_report}
Sentiment Analysis: {sentiment_report}
Macro News: {news_report}
Market Microstructure: {onchain_report}
Debate History: {history}
Last Aggressive Argument: {current_aggressive_response}
Last Conservative Argument: {current_conservative_response}

Make the case for why a balanced, data-calibrated approach maximizes risk-adjusted returns. Challenge both extremes with specific numbers. Output conversationally without special formatting."""

        response = llm.invoke(prompt)
        argument = f"Neutral Analyst: {response.content}"

        new_risk_debate_state = {
            "history": history + "\n" + argument,
            "aggressive_history": risk_debate_state.get("aggressive_history", ""),
            "conservative_history": risk_debate_state.get("conservative_history", ""),
            "neutral_history": neutral_history + "\n" + argument,
            "latest_speaker": "Neutral",
            "current_aggressive_response": risk_debate_state.get("current_aggressive_response", ""),
            "current_conservative_response": risk_debate_state.get("current_conservative_response", ""),
            "current_neutral_response": argument,
            "count": risk_debate_state["count"] + 1,
        }

        return {"risk_debate_state": new_risk_debate_state}

    return neutral_node
