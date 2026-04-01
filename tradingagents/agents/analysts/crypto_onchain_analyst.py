# tradingagents/agents/analysts/crypto_onchain_analyst.py
"""
加密货币链上数据与市场微结构分析师
分析订单簿深度、未平仓量、流动性分布等市场微结构数据。
在原框架中对应 fundamentals_analyst 的位置。
"""

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from tradingagents.agents.utils.agent_utils import build_instrument_context, get_language_instruction
from tradingagents.agents.utils.crypto_tools import (
    get_orderbook,
    get_open_interest,
    get_funding_rate,
    get_crypto_ticker,
)


def create_crypto_onchain_analyst(llm):

    def crypto_onchain_analyst_node(state):
        current_date = state["trade_date"]
        symbol = state["company_of_interest"]
        instrument_context = build_instrument_context(symbol)

        tools = [
            get_crypto_ticker,
            get_orderbook,
            get_open_interest,
            get_funding_rate,
        ]

        system_message = (
            f"""You are an expert cryptocurrency market microstructure and on-chain analyst specializing in order flow, liquidity analysis, and derivatives market structure. Your task is to analyze the market microstructure of {symbol} perpetual contracts on Bitget.

**Workflow:**
1. Call `get_crypto_ticker` for the current price context.
2. Call `get_orderbook` with symbol='{symbol}' and depth=20 to analyze market depth and liquidity.
3. Call `get_open_interest` for {symbol} to understand positioning scale and trends.
4. Call `get_funding_rate` for {symbol} for positioning cost analysis.

**Report Structure:**

### 1. Market Liquidity & Order Book Analysis
- Best bid/ask spread (absolute and percentage)
- Total bid vs ask volume in the top 20 levels
- Bid/Ask ratio interpretation (buying vs selling pressure)
- Notable price walls (large limit orders acting as support/resistance)
- Liquidity gaps that could cause slippage or rapid price movement

### 2. Open Interest Deep Dive
- Current OI size in contracts and USDT notional
- OI trend over recent periods (increasing/decreasing)
- Correlation of OI trend with price movement:
  * OI up + Price up → Trend continuation (new longs entering)
  * OI up + Price down → Trend continuation (new shorts entering)
  * OI down + Price up → Short squeeze / short covering
  * OI down + Price down → Long liquidation cascade
- Leverage risk assessment: is the market over-leveraged?

### 3. Funding Rate & Cost-of-Carry Analysis
- Current funding rate and whether it's favorable for long or short
- Cumulative funding cost for holding positions (8h, daily, weekly)
- Whether funding rate arbitrage opportunities exist
- Historical funding rate trend and extreme readings

### 4. Derivatives Market Structure Summary
- Overall market structure health (healthy leverage vs dangerous over-leverage)
- Liquidation cascade risk assessment (estimated liquidation clusters)
- Smart money vs retail positioning signals

### 5. Microstructure-Based Trading Implications
- Optimal entry levels based on order book structure
- Recommended position sizing given current liquidity depth
- Stop-loss levels to avoid known liquidity clusters
- Overall microstructure bias: Bullish / Bearish / Neutral

Append a Markdown table: Metric | Value | Signal | Interpretation."""
            + get_language_instruction()
        )

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are a helpful AI assistant collaborating with other trading agents."
                    " Use the provided tools to gather market microstructure data."
                    " You have access to the following tools: {tool_names}.\n{system_message}"
                    " For your reference, the current date is {current_date}. {instrument_context}",
                ),
                MessagesPlaceholder(variable_name="messages"),
            ]
        )

        prompt = prompt.partial(system_message=system_message)
        prompt = prompt.partial(tool_names=", ".join([t.name for t in tools]))
        prompt = prompt.partial(current_date=current_date)
        prompt = prompt.partial(instrument_context=instrument_context)

        chain = prompt | llm.bind_tools(tools)
        result = chain.invoke(state["messages"])

        report = ""
        if len(result.tool_calls) == 0:
            report = result.content

        return {
            "messages": [result],
            "fundamentals_report": report,  # reuse existing state field
        }

    return crypto_onchain_analyst_node
