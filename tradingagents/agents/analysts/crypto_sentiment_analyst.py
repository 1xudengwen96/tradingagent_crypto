# tradingagents/agents/analysts/crypto_sentiment_analyst.py
"""
加密货币情绪分析师
分析社区新闻、市场情绪、链上情绪信号，为交易决策提供情绪面依据。
"""

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from tradingagents.agents.utils.agent_utils import build_instrument_context, get_language_instruction
from tradingagents.agents.utils.crypto_tools import get_crypto_news, get_funding_rate


def create_crypto_sentiment_analyst(llm):

    def crypto_sentiment_analyst_node(state):
        current_date = state["trade_date"]
        symbol = state["company_of_interest"]  # e.g. "BTC/USDT:USDT"
        # Extract coin code from symbol: "BTC/USDT:USDT" → "BTC"
        coin = symbol.split("/")[0] if "/" in symbol else symbol
        instrument_context = build_instrument_context(symbol)

        tools = [
            get_crypto_news,
            get_funding_rate,
        ]

        system_message = (
            f"""You are an expert cryptocurrency sentiment analyst specializing in community sentiment, social media analysis, and market psychology for crypto markets. Your task is to produce a comprehensive sentiment and community analysis report for {coin}.

**Workflow:**
1. Call `get_crypto_news` with coin='{coin}' and limit=30 to get the latest community news and sentiment.
2. Call `get_funding_rate` for the full symbol (e.g. '{symbol}') to understand crowd positioning sentiment.

**Report Structure:**

### 1. News Sentiment Overview
- Classify the overall news sentiment: Strongly Bullish / Bullish / Neutral / Bearish / Strongly Bearish
- Count: number of bullish vs bearish articles in the sample
- Most impactful news events (top 5 that could move price)

### 2. Key Narrative Themes
- What is the dominant narrative in the community right now? (e.g., ETF flows, network upgrade, regulatory news, whale movements, hacking events, macro correlation)
- Are there any FUD (Fear, Uncertainty, Doubt) events or FOMO signals?
- Notable institutional or whale activity mentioned

### 3. Social Sentiment Signals
- Community confidence level in current price direction
- Signs of retail capitulation or euphoria
- Contrarian indicators (extreme sentiment often signals reversals)

### 4. Funding Rate as Sentiment Proxy
- Interpret the current funding rate through a sentiment lens:
  - High positive funding → crowd is too long / overleveraged (bearish contrarian signal)
  - High negative funding → crowd is too short / fear dominant (bullish contrarian signal)
  - Near-zero funding → balanced positioning, no strong sentiment bias
- How does this align or conflict with the news sentiment?

### 5. Sentiment-Based Trading Implications
- Overall sentiment score: 1-10 (1=extreme fear, 10=extreme greed)
- Key risk events that could rapidly shift sentiment
- Sentiment-based directional bias and confidence

Include a Markdown summary table: Sentiment Dimension | Reading | Implication."""
            + get_language_instruction()
        )

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are a helpful AI assistant collaborating with other trading agents."
                    " Use the provided tools to gather data and complete your sentiment analysis."
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
            "sentiment_report": report,
        }

    return crypto_sentiment_analyst_node
