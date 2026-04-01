# tradingagents/agents/trader/crypto_trader.py
"""
加密货币交易员
综合研究主管的投资计划，输出具体的合约交易指令：
LONG/SHORT/CLOSE @ 杠杆倍数 / 止损价 / 止盈价
"""

import functools
from tradingagents.agents.utils.agent_utils import build_instrument_context


def create_crypto_trader(llm, memory):
    def trader_node(state, name):
        symbol = state["company_of_interest"]
        instrument_context = build_instrument_context(symbol)
        investment_plan = state["investment_plan"]
        market_research_report = state["market_report"]
        sentiment_report = state["sentiment_report"]
        news_report = state["news_report"]
        onchain_report = state["fundamentals_report"]

        curr_situation = f"{market_research_report}\n\n{sentiment_report}\n\n{news_report}\n\n{onchain_report}"
        past_memories = memory.get_memories(curr_situation, n_matches=2)

        past_memory_str = ""
        if past_memories:
            for i, rec in enumerate(past_memories, 1):
                past_memory_str += rec["recommendation"] + "\n\n"
        else:
            past_memory_str = "No past memories found."

        context = {
            "role": "user",
            "content": (
                f"Based on comprehensive analysis by the research team, here is the investment plan for {symbol} perpetual futures. "
                f"{instrument_context}\n\n"
                f"Research Team's Investment Plan:\n{investment_plan}\n\n"
                "Your task is to translate this plan into a precise, executable trading order. "
                "Apply your past trading lessons to refine the execution."
            ),
        }

        messages = [
            {
                "role": "system",
                "content": f"""You are an expert crypto perpetual futures trader executing trades on Bitget. Your job is to take the research team's investment plan and produce a precise, executable trading decision.

**Output Requirements:**
You MUST end your response with the exact following format (fill in the values):

FINAL TRANSACTION PROPOSAL: **[LONG/SHORT/CLOSE]**
- Leverage: [X]x
- Entry Price: [price or MARKET]
- Stop-Loss: [price]
- Take-Profit 1: [price]
- Take-Profit 2: [price] (optional)
- Position Size: [percentage of capital, e.g., 20%]
- Time Horizon: [e.g., 4-12 hours]

**Decision Rules:**
- LONG: Open/add a long (buy) position — expecting price to rise
- SHORT: Open/add a short (sell) position — expecting price to fall
- CLOSE: Close all existing positions — exit the market (flat)
- Leverage should be proportional to conviction and volatility (higher ATR → lower leverage)
- Stop-loss must be at a technically meaningful level (not arbitrary %)
- Always specify a stop-loss — never trade without one

**Past Trading Lessons:**
{past_memory_str}""",
            },
            context,
        ]

        result = llm.invoke(messages)

        return {
            "messages": [result],
            "trader_investment_plan": result.content,
            "sender": name,
        }

    return functools.partial(trader_node, name="Crypto Trader")
