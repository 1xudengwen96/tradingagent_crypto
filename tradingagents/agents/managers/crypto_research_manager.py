# tradingagents/agents/managers/crypto_research_manager.py
"""
加密货币研究主管
综合多空辩论，产出 LONG / SHORT / CLOSE 方向决策及交易计划。
"""

from tradingagents.agents.utils.agent_utils import build_instrument_context


def create_crypto_research_manager(llm, memory):
    def research_manager_node(state) -> dict:
        symbol = state["company_of_interest"]
        instrument_context = build_instrument_context(symbol)
        history = state["investment_debate_state"].get("history", "")
        market_research_report = state["market_report"]
        sentiment_report = state["sentiment_report"]
        news_report = state["news_report"]
        onchain_report = state["fundamentals_report"]

        investment_debate_state = state["investment_debate_state"]

        curr_situation = f"{market_research_report}\n\n{sentiment_report}\n\n{news_report}\n\n{onchain_report}"
        past_memories = memory.get_memories(curr_situation, n_matches=2)

        past_memory_str = ""
        for i, rec in enumerate(past_memories, 1):
            past_memory_str += rec["recommendation"] + "\n\n"

        prompt = f"""You are the Head of Research for a crypto quantitative trading desk. Your role is to evaluate the bull vs bear debate and produce a decisive, actionable trading plan for {symbol} perpetual futures.

{instrument_context}

**Your Decision Framework:**
- Evaluate the quality of evidence on both sides (not just argument volume)
- Prioritize: technical signals > microstructure > sentiment > macro (for short-term contract trading)
- Make a decisive directional call: LONG, SHORT, or CLOSE/STAY FLAT
- AVOID neutral/hold if the evidence clearly favors one direction — be decisive

**Required Output:**

1. **Direction Decision**: LONG / SHORT / CLOSE (flat)
2. **Conviction Level**: High / Medium / Low
3. **Rationale**: The 3 strongest pieces of evidence supporting your decision
4. **Invalidation Conditions**: What market conditions would make this call wrong?
5. **Detailed Trading Plan** (feed directly to the Trader agent):
   - Direction: LONG or SHORT
   - Suggested leverage range: e.g., 5x-10x (based on volatility/ATR)
   - Entry zone: specific price level or range
   - Stop-loss level: specific price (beyond which the thesis is invalidated)
   - Take-profit targets: TP1, TP2, TP3
   - Time horizon: e.g., "4-12 hours" or "1-3 days"
   - Position sizing recommendation: e.g., 20% of capital given current volatility

**Past Mistakes to Learn From:**
{past_memory_str}

**Debate History:**
{history}

Present your analysis conversationally but include the structured trading plan clearly. Be decisive."""

        response = llm.invoke(prompt)

        new_investment_debate_state = {
            "judge_decision": response.content,
            "history": investment_debate_state.get("history", ""),
            "bear_history": investment_debate_state.get("bear_history", ""),
            "bull_history": investment_debate_state.get("bull_history", ""),
            "current_response": response.content,
            "count": investment_debate_state["count"],
        }

        return {
            "investment_debate_state": new_investment_debate_state,
            "investment_plan": response.content,
        }

    return research_manager_node
