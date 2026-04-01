# tradingagents/agents/analysts/crypto_market_analyst.py
"""
加密货币市场技术分析师
负责分析 BTC/ETH 永续合约的价格走势、技术指标、资金费率、持仓量等。
"""

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from tradingagents.agents.utils.agent_utils import build_instrument_context, get_language_instruction
from tradingagents.agents.utils.crypto_tools import (
    get_crypto_ohlcv,
    get_crypto_indicators,
    get_funding_rate,
    get_open_interest,
    get_crypto_ticker,
)


def create_crypto_market_analyst(llm):

    def crypto_market_analyst_node(state):
        current_date = state["trade_date"]
        symbol = state["company_of_interest"]  # e.g. "BTC/USDT:USDT"
        instrument_context = build_instrument_context(symbol)

        tools = [
            get_crypto_ticker,
            get_crypto_ohlcv,
            get_crypto_indicators,
            get_funding_rate,
            get_open_interest,
        ]

        system_message = (
            """You are an expert cryptocurrency perpetual futures market analyst specializing in technical analysis and market microstructure. Your task is to produce a comprehensive technical analysis report for the given crypto perpetual contract.

**Workflow (execute in this order):**
1. Call `get_crypto_ticker` to get the latest price snapshot (24h change, high/low, volume).
2. Call `get_crypto_ohlcv` with timeframe='4h' and limit=200 to get medium-term price history.
3. Call `get_crypto_indicators` with the same timeframe to compute all technical indicators.
4. Call `get_funding_rate` to assess market positioning cost and sentiment bias.
5. Call `get_open_interest` to understand the magnitude and trend of leveraged positions.

**Report Structure:**

### 1. Price Action Overview
- Current price, 24h change, recent trend direction
- Key price levels: recent highs, lows, support/resistance zones

### 2. Technical Indicators Analysis
- **Trend**: SMA-20/50 relationship, EMA-10/20 direction, golden/death cross status
- **Momentum**: MACD signal (histogram expanding/contracting, crossovers), RSI level and divergence
- **Volatility**: Bollinger Band width, ATR as % of price, recent breakout/squeeze patterns
- **Volume-weighted**: VWMA vs price, volume confirmation of trends

### 3. Funding Rate & Market Positioning
- Current funding rate: positive (longs heavy) vs negative (shorts heavy)
- Annualized funding cost for long/short positions
- Historical funding trend and what it implies about market crowding

### 4. Open Interest Analysis
- OI trend (rising/falling) in context of price direction
- Interpretation: new money entering vs liquidations/position closing
- Leverage risk assessment

### 5. Trading Bias & Key Levels
- Overall directional bias: Bullish / Bearish / Neutral with confidence level
- Key support levels (for long entries or stop-loss)
- Key resistance levels (for short entries or take-profit)
- Potential invalidation levels

Append a concise Markdown summary table at the end covering: Indicator, Value, Signal.
Be specific with price levels and percentages. This report feeds directly into the investment debate."""
            + get_language_instruction()
        )

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are a helpful AI assistant collaborating with other trading agents."
                    " Use the provided tools to progress towards completing your analysis."
                    " If you are unable to fully answer, that's OK; another assistant with different tools"
                    " will help where you left off. Execute what you can to make progress."
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
            "market_report": report,
        }

    return crypto_market_analyst_node
