# tradingagents/graph/crypto_setup.py
"""
加密货币版图结构装配器
使用加密货币专用智能体替换股票版智能体，构建合约交易分析流水线。
"""

from typing import Dict
from langgraph.graph import END, StateGraph, START
from langgraph.prebuilt import ToolNode

from tradingagents.agents.utils.agent_states import AgentState
from tradingagents.agents.utils.agent_utils import create_msg_delete

from tradingagents.agents.analysts.crypto_market_analyst import create_crypto_market_analyst
from tradingagents.agents.analysts.crypto_sentiment_analyst import create_crypto_sentiment_analyst
from tradingagents.agents.analysts.crypto_news_analyst import create_crypto_news_analyst
from tradingagents.agents.analysts.crypto_onchain_analyst import create_crypto_onchain_analyst

from tradingagents.agents.researchers.crypto_bull_researcher import create_crypto_bull_researcher
from tradingagents.agents.researchers.crypto_bear_researcher import create_crypto_bear_researcher

from tradingagents.agents.managers.crypto_research_manager import create_crypto_research_manager
from tradingagents.agents.managers.crypto_portfolio_manager import create_crypto_portfolio_manager

from tradingagents.agents.trader.crypto_trader import create_crypto_trader

from tradingagents.agents.risk_mgmt.crypto_aggressive_debator import create_crypto_aggressive_debator
from tradingagents.agents.risk_mgmt.crypto_conservative_debator import create_crypto_conservative_debator
from tradingagents.agents.risk_mgmt.crypto_neutral_debator import create_crypto_neutral_debator

from .conditional_logic import ConditionalLogic


class CryptoGraphSetup:
    """Builds and compiles the LangGraph StateGraph for crypto contract trading."""

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
        """Compile and return the crypto trading StateGraph.

        Analyst pipeline (always all four for crypto):
            Market → Sentiment → News → Onchain → Bull↔Bear → ResearchManager
            → Trader → Aggressive↔Conservative↔Neutral → PortfolioManager → END
        """
        # ---- Analyst nodes -----------------------------------------------
        analyst_map = {
            "market":    (create_crypto_market_analyst(self.quick_thinking_llm),
                          "should_continue_market"),
            "social":    (create_crypto_sentiment_analyst(self.quick_thinking_llm),
                          "should_continue_social"),
            "news":      (create_crypto_news_analyst(self.quick_thinking_llm),
                          "should_continue_news"),
            "fundamentals": (create_crypto_onchain_analyst(self.quick_thinking_llm),
                             "should_continue_fundamentals"),
        }
        analyst_order = ["market", "social", "news", "fundamentals"]

        # ---- Other nodes -------------------------------------------------
        bull_node   = create_crypto_bull_researcher(self.quick_thinking_llm, self.bull_memory)
        bear_node   = create_crypto_bear_researcher(self.quick_thinking_llm, self.bear_memory)
        rm_node     = create_crypto_research_manager(self.deep_thinking_llm, self.invest_judge_memory)
        trader_node = create_crypto_trader(self.quick_thinking_llm, self.trader_memory)

        aggressive_node   = create_crypto_aggressive_debator(self.quick_thinking_llm)
        conservative_node = create_crypto_conservative_debator(self.quick_thinking_llm)
        neutral_node      = create_crypto_neutral_debator(self.quick_thinking_llm)
        pm_node           = create_crypto_portfolio_manager(self.deep_thinking_llm, self.portfolio_manager_memory)

        # ---- Build graph -------------------------------------------------
        workflow = StateGraph(AgentState)

        # Add analyst nodes
        for key, (node, _) in analyst_map.items():
            label = key.capitalize()
            workflow.add_node(f"{label} Analyst", node)
            workflow.add_node(f"Msg Clear {label}", create_msg_delete())
            workflow.add_node(f"tools_{key}", self.tool_nodes[key])

        # Add remaining nodes
        workflow.add_node("Bull Researcher",    bull_node)
        workflow.add_node("Bear Researcher",    bear_node)
        workflow.add_node("Research Manager",   rm_node)
        workflow.add_node("Trader",             trader_node)
        workflow.add_node("Aggressive Analyst", aggressive_node)
        workflow.add_node("Conservative Analyst", conservative_node)
        workflow.add_node("Neutral Analyst",    neutral_node)
        workflow.add_node("Portfolio Manager",  pm_node)

        # ---- Analyst edges (sequential chain) ----------------------------
        first_label = analyst_order[0].capitalize()
        workflow.add_edge(START, f"{first_label} Analyst")

        for i, key in enumerate(analyst_order):
            label = key.capitalize()
            _, cond_method = analyst_map[key]

            workflow.add_conditional_edges(
                f"{label} Analyst",
                getattr(self.conditional_logic, cond_method),
                [f"tools_{key}", f"Msg Clear {label}"],
            )
            workflow.add_edge(f"tools_{key}", f"{label} Analyst")

            if i < len(analyst_order) - 1:
                next_label = analyst_order[i + 1].capitalize()
                workflow.add_edge(f"Msg Clear {label}", f"{next_label} Analyst")
            else:
                workflow.add_edge(f"Msg Clear {label}", "Bull Researcher")

        # ---- Research debate edges ----------------------------------------
        workflow.add_conditional_edges(
            "Bull Researcher",
            self.conditional_logic.should_continue_debate,
            {"Bear Researcher": "Bear Researcher", "Research Manager": "Research Manager"},
        )
        workflow.add_conditional_edges(
            "Bear Researcher",
            self.conditional_logic.should_continue_debate,
            {"Bull Researcher": "Bull Researcher", "Research Manager": "Research Manager"},
        )
        workflow.add_edge("Research Manager", "Trader")

        # ---- Risk debate edges --------------------------------------------
        workflow.add_edge("Trader", "Aggressive Analyst")
        workflow.add_conditional_edges(
            "Aggressive Analyst",
            self.conditional_logic.should_continue_risk_analysis,
            {"Conservative Analyst": "Conservative Analyst", "Portfolio Manager": "Portfolio Manager"},
        )
        workflow.add_conditional_edges(
            "Conservative Analyst",
            self.conditional_logic.should_continue_risk_analysis,
            {"Neutral Analyst": "Neutral Analyst", "Portfolio Manager": "Portfolio Manager"},
        )
        workflow.add_conditional_edges(
            "Neutral Analyst",
            self.conditional_logic.should_continue_risk_analysis,
            {"Aggressive Analyst": "Aggressive Analyst", "Portfolio Manager": "Portfolio Manager"},
        )
        workflow.add_edge("Portfolio Manager", END)

        return workflow.compile()
