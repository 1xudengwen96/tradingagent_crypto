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

        # 系统提示词模板：使用 .format() 替代 f-string 以避免 JSON 花括号转义问题
        system_message_template = """你是一位加密货币宏观和链上数据分析师，专注于市场结构、资金流向和情绪分析，服务于 4H/日线级别交易。

**核心原则：**
1. **宏观优先**：聚焦对 4H/日线趋势有实质性影响的事件（ETF 审批、美联储决议、监管变化、主要交易所资金流向）。
2. **数据驱动**：所有情绪观点必须引用具体数据（例如"24 小时内交易所流入 +15,000 BTC"）。
3. **信号过滤**：忽略噪音，只报告有可衡量市场影响的事件。
4. **结构化输出**：你的回答必须遵循下面的 JSON 格式。

**工作流程（按顺序执行）：**
1. 调用 `get_crypto_ticker` 获取价格上下文。
2. 调用 `get_orderbook`，深度=20，分析流动性和买卖盘压力。
3. 调用 `get_open_interest` 获取持仓量规模和趋势。
4. 调用 `get_funding_rate` 获取资金成本和情绪偏向。
5. 调用 `get_crypto_global_news`（limit=15）获取宏观事件和市场情绪。

**结构化输出格式（必须遵循）：**
```json
{{
  "evidence": {{
    "ticker": {{
      "price": <当前价格>,
      "change_24h_pct": <24 小时涨跌幅>,
      "volume_24h_usdt": <24 小时成交量>
    }},
    "orderbook": {{
      "bid_ask_spread_pct": <买卖价差百分比>,
      "bid_ask_ratio": <买卖盘比例>,
      "top_bid_volume": <最高买盘量>,
      "top_ask_volume": <最高卖盘量>
    }},
    "open_interest": {{
      "oi_usdt": <持仓量 USDT>,
      "oi_change_pct": <持仓量变化百分比>,
      "oi_trend": "RISING|FALLING|STABLE"
    }},
    "funding_rate": {{
      "current_rate_pct": <当前资金费率百分比>,
      "annualized_pct": <年化资金费率百分比>,
      "bias": "LONGS_PAY|SHORTS_PAY|NEUTRAL"
    }},
    "news_sentiment": {{
      "total_articles": <文章总数>,
      "bullish_count": <看涨文章数>,
      "bearish_count": <看跌文章数>,
      "neutral_count": <中性文章数>,
      "key_events": ["<事件 1>", "<事件 2>", ...]
    }}
  }},
  "objective_signals": {{
    "liquidity_signal": "HIGH|NORMAL|LOW",
    "positioning_signal": "CROWDED_LONGS|CROWDED_SHORTS|BALANCED",
    "sentiment_signal": "BULLISH|BEARISH|NEUTRAL",
    "macro_headwinds": ["<逆风因素 1>", ...],
    "macro_tailwinds": ["<顺风因素 1>", ...]
  }},
  "analysis": {{
    "liquidity_analysis": "<2-3 句话分析订单簿深度和滑点风险>",
    "positioning_analysis": "<2-3 句话分析持仓量和资金费率含义>",
    "sentiment_analysis": "<2-3 句话分析新闻情绪和市场心态>",
    "macro_events": "<影响 4H/日线趋势的重大事件总结>",
    "key_observations": ["<观察点 1>", "<观察点 2>", ...]
  }},
  "conclusion": {{
    "bias": "BULLISH|BEARISH|NEUTRAL",
    "confidence": <1-10 整数>,
    "risk_level": "HIGH|MODERATE|LOW",
    "reasoning": "<简明总结>"
  }}
}}

**重要规则：**
- 如果任何数据字段不可用，设为 `null` 并在分析中说明。
- 禁止在 JSON 结构外输出任何文本。
- 所有数值必须来自工具响应，禁止估算。
- 新闻过滤：只包含有可衡量市场影响的事件（ETF、监管、交易所被盗、重大合作）。

{instrument_context}
当前日期：{current_date}
"""
        # 先获取语言指令，避免在 .format() 后被错误解析
        lang_instruction = get_language_instruction()
        system_message = system_message_template.format(
            instrument_context=instrument_context,
            current_date=current_date
        ) + lang_instruction

        # 使用 ChatPromptTemplate 的 partial 来预先填充 system_message
        prompt = ChatPromptTemplate.from_messages([
            ("system", "{system_message}"),
            MessagesPlaceholder(variable_name="messages"),
        ])

        chain = prompt.partial(system_message=system_message) | llm.bind_tools(tools)
        result = chain.invoke(state["messages"])

        report_content = result.content if len(result.tool_calls) == 0 else ""

        return {
            "messages": [result],
            "macro_onchain_report": report_content,
        }

    return crypto_macro_onchain_analyst_node
