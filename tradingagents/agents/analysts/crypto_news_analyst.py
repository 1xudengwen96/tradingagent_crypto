# tradingagents/agents/analysts/crypto_news_analyst.py
"""
加密货币宏观新闻分析师
分析宏观市场动态、监管政策、链上数据趋势等影响加密市场的宏观因素。
"""

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from tradingagents.agents.utils.agent_utils import build_instrument_context, get_language_instruction
from tradingagents.agents.utils.crypto_tools import get_crypto_news, get_crypto_global_news


def create_crypto_news_analyst(llm):

    def crypto_news_analyst_node(state):
        current_date = state["trade_date"]
        symbol = state["company_of_interest"]
        coin = symbol.split("/")[0] if "/" in symbol else symbol
        instrument_context = build_instrument_context(symbol)

        tools = [
            get_crypto_global_news,
            get_crypto_news,
        ]

        system_message = (
            f"""You are an expert cryptocurrency macro and news analyst. Your task is to analyze the global crypto market environment and how macro events affect {coin} perpetual contract trading.

**Workflow:**
1. Call `get_crypto_global_news` with limit=25 to get broad market macro news.
2. Call `get_crypto_news` with coin='{coin}' and limit=20 for coin-specific news.

**Report Structure:**

### 1. Global Macro Crypto Environment
- Federal Reserve / interest rate developments affecting risk assets
- Bitcoin ETF flows and institutional adoption news
- Regulatory developments (SEC, CFTC, global regulations)
- Stablecoin and DeFi ecosystem news
- Major exchange news (listings, delistings, hacks, outages)

### 2. {coin}-Specific News
- Protocol upgrades, hard forks, or technical developments
- Partnership announcements, ecosystem growth
- Whale wallet movements or large on-chain transactions
- Mining/staking metrics (for BTC: hash rate; for ETH: staking yield, burn rate)
- Derivatives-specific news: options expiry, institutional positioning

### 3. Macro Correlation Analysis
- How is {coin} correlating with traditional markets (S&P 500, gold, DXY) right now?
- Risk-on vs risk-off environment assessment
- Any decoupling signals or unusual correlation breakdowns

### 4. Event Calendar & Upcoming Catalysts
- Known upcoming events: protocol upgrades, token unlocks, regulatory deadlines, options expiry
- Potential surprise events that could create volatility

### 5. Macro-Based Trading Implications
- Is the macro environment favorable for leveraged long or short positions?
- Key macro risk levels to watch
- Overall macro sentiment: Bullish / Neutral / Bearish

End with a Markdown table: Event Category | Description | Estimated Impact (High/Medium/Low) | Direction Bias."""
            + get_language_instruction()
        )

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are a helpful AI assistant collaborating with other trading agents."
                    " Use the provided tools to gather macro and news data."
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
            "news_report": report,
        }

    return crypto_news_analyst_node
