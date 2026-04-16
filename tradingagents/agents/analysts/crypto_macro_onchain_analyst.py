# tradingagents/agents/analysts/crypto_macro_onchain_analyst.py
"""
加密货币宏观与链上分析师（重构版）

重构要点：
1. 合并原有的 News Analyst、Sentiment Analyst、Onchain Analyst 职能
2. 只关注对 4H/1D 有实质影响的大事件（ETF、美联储决议、大户爆仓）
3. 结构化输出：必须包含 evidence 字段
4. 数据驱动：所有情绪分析必须基于真实新闻和链上数据
"""

import logging
from typing import Dict, Any
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from tradingagents.agents.utils.agent_utils import build_instrument_context, get_language_instruction
from tradingagents.agents.utils.crypto_tools import (
    get_crypto_ticker,
    get_orderbook,
    get_open_interest,
    get_funding_rate,
    get_crypto_global_news,
)

logger = logging.getLogger(__name__)


def create_crypto_macro_onchain_analyst(llm):
    """
    创建宏观与链上分析师节点
    
    职责：
    - 监控大额资金流向（交易所钱包、巨鲸转账）
    - 评估宏观事件影响（ETF、美联储决议、监管政策）
    - 分析市场情绪（恐慌/贪婪、新闻情绪）
    - 订单簿深度和流动性分析
    
    Args:
        llm: LLM 客户端
    
    Returns:
        crypto_macro_onchain_analyst_node 函数
    """
    
    def crypto_macro_onchain_analyst_node(state) -> Dict[str, Any]:
        current_date = state["trade_date"]
        symbol = state["company_of_interest"]
        timeframe = state.get("timeframe", "4h")
        instrument_context = build_instrument_context(symbol)
        
        # 工具集：宏观和链上数据
        tools = [
            get_crypto_ticker,
            get_orderbook,
            get_open_interest,
            get_funding_rate,
            get_crypto_global_news,
        ]
        
        system_message = f"""You are a cryptocurrency macro and on-chain analyst specializing in market structure, capital flows, and sentiment analysis for 4H/Daily trading.

**Core Principles:**
1. **Macro-First**: Focus on events that materially impact 4H/Daily trends (ETF approvals, Fed decisions, regulatory changes, major exchange flows).
2. **Data-Driven**: All sentiment claims must cite specific data (e.g., "Exchange inflow +15,000 BTC in 24h").
3. **Signal Filtering**: Ignore noise. Only report events with measurable market impact.
4. **Structured Output**: Your response MUST follow the JSON format below.

**Workflow (execute in order):**
1. Call `get_crypto_ticker` for price context.
2. Call `get_orderbook` with depth=20 to analyze liquidity and bid/ask pressure.
3. Call `get_open_interest` for positioning scale and trends.
4. Call `get_funding_rate` for cost-of-carry and sentiment bias.
5. Call `get_crypto_global_news` (limit=15) for macro events and market sentiment.

**Structured Output Format (MUST follow):**
```json
{{
  "evidence": {{
    "ticker": {{
      "price": <float>,
      "change_24h_pct": <float>,
      "volume_24h_usdt": <float>
    }},
    "orderbook": {{
      "bid_ask_spread_pct": <float or null>,
      "bid_ask_ratio": <float or null>,
      "top_bid_volume": <float or null>,
      "top_ask_volume": <float or null>
    }},
    "open_interest": {{
      "oi_usdt": <float or null>,
      "oi_change_pct": <float or null>,
      "oi_trend": "RISING|FALLING|STABLE"
    }},
    "funding_rate": {{
      "current_rate_pct": <float or null>,
      "annualized_pct": <float or null>,
      "bias": "LONGS_PAY|SHORTS_PAY|NEUTRAL"
    }},
    "news_sentiment": {{
      "total_articles": <int>,
      "bullish_count": <int>,
      "bearish_count": <int>,
      "neutral_count": <int>,
      "key_events": ["<event 1>", "<event 2>", ...]
    }}
  }},
  "objective_signals": {{
    "liquidity_signal": "HIGH|NORMAL|LOW",
    "positioning_signal": "CROWDED_LONGS|CROWDED_SHORTS|BALANCED",
    "sentiment_signal": "BULLISH|BEARISH|NEUTRAL",
    "macro_headwinds": ["<headwind 1>", ...],
    "macro_tailwinds": ["<tailwind 1>", ...]
  }},
  "analysis": {{
    "liquidity_analysis": "<2-3 sentences on orderbook depth and slippage risk>",
    "positioning_analysis": "<2-3 sentences on OI and funding rate implications>",
    "sentiment_analysis": "<2-3 sentences on news sentiment and social mood>",
    "macro_events": "<summary of material events impacting 4H/Daily trend>",
    "key_observations": ["<observation 1>", "<observation 2>", ...]
  }},
  "conclusion": {{
    "bias": "BULLISH|BEARISH|NEUTRAL",
    "confidence": <1-10 integer>,
    "risk_level": "HIGH|MODERATE|LOW",
    "reasoning": "<concise summary>"
  }}
}}

**Important Rules:**
- If any data field is unavailable, set it to `null` and mention in analysis.
- Do NOT output any text outside the JSON structure.
- All numerical values must be from tool responses, NOT estimated.
- Filter news: Only include events with measurable market impact (ETF, regulation, exchange hacks, major partnerships).

{instrument_context}
Current date: {current_date}
""" + get_language_instruction()
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_message),
            MessagesPlaceholder(variable_name="messages"),
        ])
        
        chain = prompt | llm.bind_tools(tools)
        result = chain.invoke(state["messages"])
        
        report_content = result.content if len(result.tool_calls) == 0 else ""
        
        return {
            "messages": [result],
            "macro_onchain_report": report_content,
        }
    
    return crypto_macro_onchain_analyst_node
