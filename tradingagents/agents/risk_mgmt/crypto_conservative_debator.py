# tradingagents/agents/risk_mgmt/crypto_conservative_debator.py
"""
加密货币保守风险分析师
强调资金安全、防止爆仓，倡导低杠杆、小仓位的保守策略。
"""


def create_crypto_conservative_debator(llm):
    def conservative_node(state) -> dict:
        risk_debate_state = state["risk_debate_state"]
        history = risk_debate_state.get("history", "")
        conservative_history = risk_debate_state.get("conservative_history", "")

        current_aggressive_response = risk_debate_state.get("current_aggressive_response", "")
        current_neutral_response = risk_debate_state.get("current_neutral_response", "")

        market_report = state["market_report"]
        sentiment_report = state["sentiment_report"]
        news_report = state["news_report"]
        onchain_report = state["fundamentals_report"]

        trader_decision = state["trader_investment_plan"]
        symbol = state["company_of_interest"]

        prompt = f"""You are the Conservative Risk Analyst on a crypto trading desk specializing in {symbol} perpetual futures. Your role is to protect capital, avoid liquidation, and ensure sustainable trading.

**The Trader's Proposed Decision:**
{trader_decision}

**Your Conservative Stance:**
- **Liquidation Risk**: In crypto, high leverage means liquidation can happen in minutes. A 5% adverse move at 20x leverage wipes the position. The math of ruin is unforgiving.
- **Funding Rate Risk**: Positive funding can eat into profits over time. High positive funding means the market is crowded long — a dangerous situation.
- **Volatility Risk**: Crypto markets can move 10-20% in hours due to whale manipulation, news events, or liquidation cascades. Low leverage (3x-5x) gives time to react.
- **Open Interest Risk**: High OI with crowded positioning means cascade liquidations are possible. One large liquidation triggers others.
- **Overnight/Weekend Risk**: Crypto trades 24/7. Gaps on weekends and overnight sessions can instantly hit stop-losses.
- **Position Sizing**: Recommend max 10-15% of capital per trade. Concentration in one position is reckless.
- **Counter the Aggressive View**: Challenge unrealistic leverage expectations. Past performance of high leverage doesn't account for the inevitable blow-up.
- **Counter the Neutral View**: Even "moderate" leverage can be too high given crypto's inherent volatility.

**Data to Reference:**
Market Technical Analysis: {market_report}
Sentiment Analysis: {sentiment_report}
Macro News: {news_report}
Market Microstructure: {onchain_report}
Debate History: {history}
Last Aggressive Argument: {current_aggressive_response}
Last Neutral Argument: {current_neutral_response}

Make your case for why a conservative approach — lower leverage (3x-5x), tighter position sizing, wider stop-losses — is the only sustainable strategy. Output conversationally without special formatting."""

        response = llm.invoke(prompt)
        argument = f"Conservative Analyst: {response.content}"

        new_risk_debate_state = {
            "history": history + "\n" + argument,
            "aggressive_history": risk_debate_state.get("aggressive_history", ""),
            "conservative_history": conservative_history + "\n" + argument,
            "neutral_history": risk_debate_state.get("neutral_history", ""),
            "latest_speaker": "Conservative",
            "current_aggressive_response": risk_debate_state.get("current_aggressive_response", ""),
            "current_conservative_response": argument,
            "current_neutral_response": risk_debate_state.get("current_neutral_response", ""),
            "count": risk_debate_state["count"] + 1,
        }

        return {"risk_debate_state": new_risk_debate_state}

    return conservative_node
