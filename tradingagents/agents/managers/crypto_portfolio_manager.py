# tradingagents/agents/managers/crypto_portfolio_manager.py
"""
加密货币组合管理者（最终决策者）
综合风险辩论，产出最终的合约交易决策：LONG/SHORT/CLOSE + 杠杆 + 止损 + 止盈。
"""

from tradingagents.agents.utils.agent_utils import build_instrument_context, get_language_instruction


def create_crypto_portfolio_manager(llm, memory):
    def portfolio_manager_node(state) -> dict:
        symbol = state["company_of_interest"]
        instrument_context = build_instrument_context(symbol)

        history = state["risk_debate_state"]["history"]
        risk_debate_state = state["risk_debate_state"]
        market_report = state["market_report"]
        news_report = state["news_report"]
        onchain_report = state["fundamentals_report"]
        sentiment_report = state["sentiment_report"]
        trader_plan = state["investment_plan"]

        curr_situation = f"{market_report}\n\n{sentiment_report}\n\n{news_report}\n\n{onchain_report}"
        past_memories = memory.get_memories(curr_situation, n_matches=2)

        past_memory_str = ""
        for i, rec in enumerate(past_memories, 1):
            past_memory_str += rec["recommendation"] + "\n\n"

        prompt = f"""You are the Chief Portfolio Manager for a crypto quantitative trading fund. Your role is to synthesize the risk analysts' debate and deliver the FINAL, EXECUTABLE trading decision for {symbol} perpetual futures on Bitget.

{instrument_context}

---

**DECISION SCALE** (choose exactly one):
- **LONG**: Open or add to a long (buy) position — strong bullish conviction
- **LONG-LITE**: Open a smaller long position — moderate bullish bias with caution
- **SHORT**: Open or add to a short (sell) position — strong bearish conviction
- **SHORT-LITE**: Open a smaller short position — moderate bearish bias with caution
- **CLOSE**: Close all existing positions, go flat — no clear edge or conflicting signals

---

**Context:**
- Research Team's Plan: {trader_plan}
- Lessons From Past Decisions: {past_memory_str}

---

**Required Output Structure:**

## 1. Final Decision
State exactly one of: LONG / LONG-LITE / SHORT / SHORT-LITE / CLOSE

## 2. Execution Parameters
- **Direction**: LONG or SHORT (or FLAT for CLOSE)
- **Leverage**: [X]x (justify based on current ATR and conviction)
- **Position Size**: [X]% of capital
- **Entry**: [price level or MARKET]
- **Stop-Loss**: [price] — the level where the thesis is definitively wrong
- **Take-Profit 1**: [price] — first partial exit (50% of position)
- **Take-Profit 2**: [price] — second exit (remaining position)
- **Time Horizon**: [e.g., 4-12 hours / 1-3 days]
- **Estimated Liquidation Price** (at chosen leverage): [price]

## 3. Executive Rationale
2-3 sentences explaining the most decisive factors from the risk debate.

## 4. Key Risk Factors
2-3 specific risks that could invalidate this trade and the stop-loss level protecting against them.

---

**Risk Analysts Debate:**
{history}

---

Be decisive. Ground every parameter in specific evidence. The execution engine will use your output directly to place orders.{get_language_instruction()}"""

        response = llm.invoke(prompt)

        new_risk_debate_state = {
            "judge_decision": response.content,
            "history": risk_debate_state["history"],
            "aggressive_history": risk_debate_state["aggressive_history"],
            "conservative_history": risk_debate_state["conservative_history"],
            "neutral_history": risk_debate_state["neutral_history"],
            "latest_speaker": "Judge",
            "current_aggressive_response": risk_debate_state["current_aggressive_response"],
            "current_conservative_response": risk_debate_state["current_conservative_response"],
            "current_neutral_response": risk_debate_state["current_neutral_response"],
            "count": risk_debate_state["count"],
        }

        return {
            "risk_debate_state": new_risk_debate_state,
            "final_trade_decision": response.content,
        }

    return portfolio_manager_node
