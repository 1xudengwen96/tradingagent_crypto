# tradingagents/graph/crypto_setup.py
"""
加密货币版图结构装配器 —— 日线铁三角版

重构方案（按 solv.md 阶段四）：
- 移除：Sentiment Analyst、News Analyst、
         Bull/Bear Researchers（辩论噪音）、
         Aggressive/Conservative/Neutral Debators（三方辩论）
- 保留：Market Analyst（技术面）、Onchain Analyst（宏观/市场结构）、
         Research Manager（汇总）、Portfolio Manager（仓位）

最终图流程：
    START
      │
      ▼
    Market Analyst ←→ tools_market  (技术面：OHLCV/指标/ATR)
      │
      ▼ Msg Clear Market
    Onchain Analyst ←→ tools_fundamentals  (宏观：资金费率/OI/Ticker)
      │
      ▼ Msg Clear Fundamentals
    Research Manager（深度LLM）→ investment_plan
      │
      ▼
    Portfolio Manager（LLM 定向 + Python 仓位）→ final_trade_decision
      │
      ▼
    END

保留原有的 Debate / Risk discuss 条件路由代码以便将来重新启用，
但当前轮数固定为 0（跳过辩论）。
"""

from typing import Dict
from langgraph.graph import END, StateGraph, START
from langgraph.prebuilt import ToolNode

from tradingagents.agents.utils.agent_states import AgentState
from tradingagents.agents.utils.agent_utils import create_msg_delete

from tradingagents.agents.analysts.crypto_market_analyst import create_crypto_market_analyst
from tradingagents.agents.analysts.crypto_onchain_analyst import create_crypto_onchain_analyst

from tradingagents.agents.managers.crypto_research_manager import create_crypto_research_manager
from tradingagents.agents.managers.crypto_portfolio_manager import create_crypto_portfolio_manager

from .conditional_logic import ConditionalLogic


class CryptoGraphSetup:
    """
    构建并编译日线铁三角 LangGraph StateGraph。

    铁三角架构（日线专用）：
    1. Technical_Analyst  → Market Analyst（价格行为、均线、RSI、ATR）
    2. Macro_Analyst      → Onchain Analyst（资金费率、OI、恐慌贪婪指数）
    3. Portfolio_Manager  → LLM 定方向，Python 硬算仓位
    """

    def __init__(
        self,
        quick_thinking_llm,
        deep_thinking_llm,
        tool_nodes: Dict[str, ToolNode],
        bull_memory,
        bear_memory,
        trader_memory,
        invest_judge_memory,
        portfolio_manager_memory,
        conditional_logic: ConditionalLogic,
    ):
        self.quick_thinking_llm = quick_thinking_llm
        self.deep_thinking_llm = deep_thinking_llm
        self.tool_nodes = tool_nodes
        self.bull_memory = bull_memory
        self.bear_memory = bear_memory
        self.trader_memory = trader_memory
        self.invest_judge_memory = invest_judge_memory
        self.portfolio_manager_memory = portfolio_manager_memory
        self.conditional_logic = conditional_logic

    def setup_graph(self):
        """
        编译并返回日线铁三角 StateGraph。

        精简后只保留 4 个节点：
        - Market Analyst     （技术面分析）
        - Onchain Analyst    （宏观 + 市场微观结构）
        - Research Manager   （汇总研究，输出 investment_plan）
        - Portfolio Manager  （最终仓位决策，Python ATR 模型）
        """
        # ---- 创建节点 --------------------------------------------------------
        market_analyst_node = create_crypto_market_analyst(self.quick_thinking_llm)
        onchain_analyst_node = create_crypto_onchain_analyst(self.quick_thinking_llm)
        rm_node = create_crypto_research_manager(self.deep_thinking_llm, self.invest_judge_memory)
        pm_node = create_crypto_portfolio_manager(self.deep_thinking_llm, self.portfolio_manager_memory)

        # ---- 构建图 ----------------------------------------------------------
        workflow = StateGraph(AgentState)

        # 节点注册
        workflow.add_node("Market Analyst", market_analyst_node)
        workflow.add_node("Msg Clear Market", create_msg_delete())
        workflow.add_node("tools_market", self.tool_nodes["market"])

        workflow.add_node("Onchain Analyst", onchain_analyst_node)
        workflow.add_node("Msg Clear Fundamentals", create_msg_delete())
        workflow.add_node("tools_fundamentals", self.tool_nodes["fundamentals"])

        workflow.add_node("Research Manager", rm_node)
        workflow.add_node("Portfolio Manager", pm_node)

        # ---- 边：Market Analyst（含工具循环）---------------------------------
        workflow.add_edge(START, "Market Analyst")
        workflow.add_conditional_edges(
            "Market Analyst",
            self.conditional_logic.should_continue_market,
            ["tools_market", "Msg Clear Market"],
        )
        workflow.add_edge("tools_market", "Market Analyst")
        workflow.add_edge("Msg Clear Market", "Onchain Analyst")

        # ---- 边：Onchain Analyst（含工具循环）---------------------------------
        workflow.add_conditional_edges(
            "Onchain Analyst",
            self.conditional_logic.should_continue_fundamentals,
            ["tools_fundamentals", "Msg Clear Fundamentals"],
        )
        workflow.add_edge("tools_fundamentals", "Onchain Analyst")

        # ---- 边：Research Manager → Portfolio Manager → END ------------------
        workflow.add_edge("Msg Clear Fundamentals", "Research Manager")
        workflow.add_edge("Research Manager", "Portfolio Manager")
        workflow.add_edge("Portfolio Manager", END)

        return workflow.compile()
