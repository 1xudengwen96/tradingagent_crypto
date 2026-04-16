# tradingagents/graph/crypto_setup.py
"""
加密货币版图结构装配器 —— 日线铁三角精简版 (v2.0 Refactored)

重构方案（按 problem.md 和 problem1.md 要求）：
- 移除：Sentiment Analyst、News Analyst、Bull/Bear Researchers、所有 Debators
- 保留并精简：Technical Analyst（技术面）、Macro Onchain Analyst（宏观 + 链上）、
              Research Manager（汇总）、Portfolio Manager（仓位决策）

最终图流程（三节点精简版）：
    START
      │
      ▼
    Technical Analyst ←→ tools_technical  (技术面：OHLCV/指标/成交量异常)
      │
      ▼ Msg Clear Technical
    Macro Onchain Analyst ←→ tools_macro  (宏观：资金费率/OI/订单簿/新闻)
      │
      ▼ Msg Clear Macro
    Research Manager（深度 LLM）→ research_report
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

# 精简后的分析师模块
from tradingagents.agents.analysts.crypto_technical_analyst import create_crypto_technical_analyst
from tradingagents.agents.analysts.crypto_macro_onchain_analyst import create_crypto_macro_onchain_analyst

# 研究经理和投资组合经理
from tradingagents.agents.managers.crypto_research_manager import create_crypto_research_manager
from tradingagents.agents.managers.crypto_portfolio_manager import create_crypto_portfolio_manager

from .conditional_logic import ConditionalLogic


class CryptoGraphSetup:
    """
    构建并编译日线铁三角精简版 LangGraph StateGraph。

    精简架构（v2.0）：
    1. Technical Analyst    → 技术面分析（价格行为、均线、RSI、ATR、成交量异常）
    2. Macro Onchain Analyst → 宏观 + 市场微观结构（资金费率、OI、订单簿、宏观新闻）
    3. Research Manager     → 汇总两份报告，识别一致性和分歧
    4. Portfolio Manager    → LLM 定方向，Python 硬算仓位（ATR 模型）
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
        编译并返回日线铁三角精简版 StateGraph。

        精简后只保留 4 个核心节点：
        - Technical Analyst      （技术面分析）
        - Macro Onchain Analyst  （宏观 + 链上分析）
        - Research Manager       （汇总研究，输出 research_report）
        - Portfolio Manager      （最终仓位决策，Python ATR 模型）
        """
        # ---- 创建节点 --------------------------------------------------------
        # 技术面分析师（使用快速思考模型）
        technical_analyst_node = create_crypto_technical_analyst(
            self.quick_thinking_llm,
            enable_vision=False,  # 默认不启用视觉分析（可通过配置开启）
        )
        
        # 宏观链上分析师（使用快速思考模型）
        macro_onchain_analyst_node = create_crypto_macro_onchain_analyst(
            self.quick_thinking_llm,
        )
        
        # 研究经理（使用深度思考模型 Qwen-Max）
        rm_node = create_crypto_research_manager(
            self.deep_thinking_llm,
            self.invest_judge_memory,
        )
        
        # 投资组合经理（使用深度思考模型 Qwen-Max）
        pm_node = create_crypto_portfolio_manager(
            self.deep_thinking_llm,
            self.portfolio_manager_memory,
        )

        # ---- 构建图 ----------------------------------------------------------
        workflow = StateGraph(AgentState)

        # 节点注册
        workflow.add_node("Technical Analyst", technical_analyst_node)
        workflow.add_node("Msg Clear Technical", create_msg_delete())
        workflow.add_node("tools_technical", self.tool_nodes["technical"])

        workflow.add_node("Macro Onchain Analyst", macro_onchain_analyst_node)
        workflow.add_node("Msg Clear Macro", create_msg_delete())
        workflow.add_node("tools_macro", self.tool_nodes["macro"])

        workflow.add_node("Research Manager", rm_node)
        workflow.add_node("Portfolio Manager", pm_node)

        # ---- 边：Technical Analyst（含工具循环）---------------------------------
        workflow.add_edge(START, "Technical Analyst")
        workflow.add_conditional_edges(
            "Technical Analyst",
            self.conditional_logic.should_continue_technical,
            ["tools_technical", "Msg Clear Technical"],
        )
        workflow.add_edge("tools_technical", "Technical Analyst")
        workflow.add_edge("Msg Clear Technical", "Macro Onchain Analyst")

        # ---- 边：Macro Onchain Analyst（含工具循环）---------------------------------
        workflow.add_conditional_edges(
            "Macro Onchain Analyst",
            self.conditional_logic.should_continue_macro,
            ["tools_macro", "Msg Clear Macro"],
        )
        workflow.add_edge("tools_macro", "Macro Onchain Analyst")

        # ---- 边：Research Manager → Portfolio Manager → END ------------------
        workflow.add_edge("Msg Clear Macro", "Research Manager")
        workflow.add_edge("Research Manager", "Portfolio Manager")
        workflow.add_edge("Portfolio Manager", END)

        return workflow.compile()
