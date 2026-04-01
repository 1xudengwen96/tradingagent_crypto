# tradingagents/graph/crypto_trading_graph.py
"""
CryptoTradingAgentsGraph — 加密货币合约交易多智能体系统主类

与原始 TradingAgentsGraph 的区别：
1. 使用双 LLM 配置：Claude Opus（深度分析）+ GPT（快速决策）
2. 数据源：Bitget CCXT 代替 yfinance
3. 决策输出：LONG/LONG-LITE/SHORT/SHORT-LITE/CLOSE + 杠杆 + 止损 + 止盈
4. 自动执行层：通过 BitgetExecutor 将决策转为真实 API 订单
"""

import os
import json
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from langgraph.prebuilt import ToolNode

from tradingagents.llm_clients import create_llm_client
from tradingagents.agents.utils.memory import FinancialSituationMemory
from tradingagents.agents.utils.agent_states import (
    AgentState,
    InvestDebateState,
    RiskDebateState,
)
from tradingagents.dataflows.config import set_config
from tradingagents.default_config import DEFAULT_CONFIG, CRYPTO_CONFIG

# Crypto-specific tool wrappers (LangChain @tool functions)
from tradingagents.agents.utils.crypto_tools import (
    get_crypto_ohlcv,
    get_crypto_indicators,
    get_funding_rate,
    get_orderbook,
    get_open_interest,
    get_crypto_news,
    get_crypto_global_news,
    get_crypto_ticker,
)

from tradingagents.execution.bitget_executor import BitgetExecutor, SignalParser

from .conditional_logic import ConditionalLogic
from .crypto_setup import CryptoGraphSetup
from .propagation import Propagator
from .reflection import Reflector

logger = logging.getLogger(__name__)


class CryptoTradingAgentsGraph:
    """Multi-agent crypto contract trading system.

    Orchestrates the full pipeline:
    Analysts → Researchers → Research Manager → Trader →
    Risk Debaters → Portfolio Manager → (optional) Bitget Order Execution
    """

    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        debug: bool = False,
        auto_execute: bool = False,   # Whether to place real orders via Bitget API
        callbacks: Optional[List] = None,
    ):
        """
        Parameters
        ----------
        config : dict, optional
            Merged config dict. Defaults to CRYPTO_CONFIG merged with DEFAULT_CONFIG.
        debug : bool
            If True, print intermediate agent states.
        auto_execute : bool
            If True, parse the portfolio manager output and place real Bitget orders.
        callbacks : list, optional
            LangChain callback handlers.
        """
        self.debug = debug
        self.auto_execute = auto_execute
        self.callbacks = callbacks or []

        # Merge configs: CRYPTO_CONFIG values take priority
        base = {**DEFAULT_CONFIG}
        base.update(CRYPTO_CONFIG)
        if config:
            base.update(config)
        self.config = base

        # Push config to the vendor routing layer
        set_config(self.config)

        # Create cache directory
        os.makedirs(
            os.path.join(self.config["project_dir"], "dataflows/data_cache"),
            exist_ok=True,
        )

        # ---- LLM setup (dual-provider) -----------------------------------
        # Deep thinking: Claude Opus (research manager, portfolio manager)
        deep_client = create_llm_client(
            provider=self.config.get("deep_think_llm_provider", "anthropic"),
            model=self.config.get("deep_think_llm", "claude-opus-4-6"),
            api_key=self.config.get("anthropic_api_key") or None,
        )
        # Quick thinking: GPT-mini (analysts, trader, debaters)
        quick_client = create_llm_client(
            provider=self.config.get("quick_think_llm_provider", "openai"),
            model=self.config.get("quick_think_llm", "gpt-4o-mini"),
            api_key=self.config.get("openai_api_key") or None,
        )

        self.deep_thinking_llm = deep_client.get_llm()
        self.quick_thinking_llm = quick_client.get_llm()

        # ---- Memory stores -----------------------------------------------
        self.bull_memory = FinancialSituationMemory("crypto_bull_memory", self.config)
        self.bear_memory = FinancialSituationMemory("crypto_bear_memory", self.config)
        self.trader_memory = FinancialSituationMemory("crypto_trader_memory", self.config)
        self.invest_judge_memory = FinancialSituationMemory("crypto_invest_judge_memory", self.config)
        self.portfolio_manager_memory = FinancialSituationMemory("crypto_pm_memory", self.config)

        # ---- Tool nodes --------------------------------------------------
        self.tool_nodes = self._create_tool_nodes()

        # ---- Graph components --------------------------------------------
        self.conditional_logic = ConditionalLogic(
            max_debate_rounds=self.config.get("max_debate_rounds", 1),
            max_risk_discuss_rounds=self.config.get("max_risk_discuss_rounds", 1),
        )
        self.graph_setup = CryptoGraphSetup(
            quick_thinking_llm=self.quick_thinking_llm,
            deep_thinking_llm=self.deep_thinking_llm,
            tool_nodes=self.tool_nodes,
            bull_memory=self.bull_memory,
            bear_memory=self.bear_memory,
            trader_memory=self.trader_memory,
            invest_judge_memory=self.invest_judge_memory,
            portfolio_manager_memory=self.portfolio_manager_memory,
            conditional_logic=self.conditional_logic,
        )

        self.propagator = Propagator(
            max_recur_limit=self.config.get("max_recur_limit", 100)
        )
        self.reflector = Reflector(self.quick_thinking_llm)

        # ---- Execution layer (optional) ----------------------------------
        self.executor: Optional[BitgetExecutor] = None
        if auto_execute:
            self.executor = BitgetExecutor(
                api_key=self.config.get("bitget_api_key", ""),
                secret=self.config.get("bitget_secret", ""),
                passphrase=self.config.get("bitget_passphrase", ""),
                sandbox=self.config.get("sandbox_mode", True),
                margin_mode=self.config.get("margin_mode", "isolated"),
                default_leverage=self.config.get("default_leverage", 5),
            )

        # ---- State tracking ----------------------------------------------
        self.curr_state = None
        self.log_states_dict: Dict[str, Any] = {}

        # Compile graph
        self.graph = self.graph_setup.setup_graph()
        logger.info("CryptoTradingAgentsGraph initialized (auto_execute=%s)", auto_execute)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def propagate(self, symbol: str, trade_date: Optional[str] = None) -> tuple:
        """Run the full multi-agent analysis pipeline for one symbol.

        Parameters
        ----------
        symbol : str
            Trading pair, e.g. "BTC/USDT:USDT"
        trade_date : str, optional
            ISO date string. Defaults to today (UTC).

        Returns
        -------
        (final_state, decision_str)
        """
        if trade_date is None:
            trade_date = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

        init_state = self.propagator.create_initial_state(symbol, trade_date)
        args = self.propagator.get_graph_args()

        if self.debug:
            trace = []
            for chunk in self.graph.stream(init_state, **args):
                if chunk.get("messages"):
                    chunk["messages"][-1].pretty_print()
                trace.append(chunk)
            final_state = trace[-1]
        else:
            final_state = self.graph.invoke(init_state, **args)

        self.curr_state = final_state
        self._log_state(symbol, trade_date, final_state)

        decision_text = final_state.get("final_trade_decision", "")
        logger.info("Analysis complete for %s | decision preview: %.120s", symbol, decision_text)

        return final_state, decision_text

    def execute_decision(
        self,
        decision_text: str,
        symbol: str,
        capital_usdt: Optional[float] = None,
    ):
        """Parse the portfolio manager's decision text and place orders.

        Parameters
        ----------
        decision_text : str
        symbol : str
        capital_usdt : float, optional
            Overrides config value if provided.

        Returns
        -------
        ExecutionResult or None (if auto_execute=False)
        """
        if not self.auto_execute or self.executor is None:
            logger.info("auto_execute=False — skipping order placement")
            return None

        capital = capital_usdt or self.config.get("capital_usdt", 1000.0)
        signal = SignalParser.parse(decision_text)
        result = self.executor.execute(signal, symbol, capital)

        if result.success:
            logger.info(
                "Order(s) placed for %s | direction=%s leverage=%sx | order_ids=%s",
                symbol,
                signal.direction,
                signal.leverage,
                [o.get("id") for o in result.orders],
            )
        else:
            logger.error("Order placement FAILED for %s: %s", symbol, result.error)

        return result

    def run(self, symbol: str) -> tuple:
        """Convenience method: analyse + execute for one symbol.

        Returns
        -------
        (final_state, decision_text, execution_result)
        """
        final_state, decision_text = self.propagate(symbol)
        execution_result = self.execute_decision(decision_text, symbol)
        return final_state, decision_text, execution_result

    def reflect_and_remember(self, pnl: float):
        """Store reflections in agent memories after a trade resolves."""
        self.reflector.reflect_bull_researcher(self.curr_state, pnl, self.bull_memory)
        self.reflector.reflect_bear_researcher(self.curr_state, pnl, self.bear_memory)
        self.reflector.reflect_trader(self.curr_state, pnl, self.trader_memory)
        self.reflector.reflect_invest_judge(self.curr_state, pnl, self.invest_judge_memory)
        self.reflector.reflect_portfolio_manager(self.curr_state, pnl, self.portfolio_manager_memory)

    def fetch_account_balance(self) -> Dict[str, float]:
        """Return USDT balance from Bitget (requires auto_execute=True)."""
        if self.executor is None:
            return {}
        return self.executor.fetch_account_balance()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _create_tool_nodes(self) -> Dict[str, ToolNode]:
        """Wire crypto data tools into LangGraph ToolNodes."""
        return {
            # Market analyst: price data + technical indicators
            "market": ToolNode([
                get_crypto_ohlcv,
                get_crypto_indicators,
                get_crypto_ticker,
                get_funding_rate,
            ]),
            # Sentiment analyst: news + funding rate (crowd positioning)
            "social": ToolNode([
                get_crypto_news,
                get_funding_rate,
            ]),
            # News analyst: global macro + coin-specific news
            "news": ToolNode([
                get_crypto_global_news,
                get_crypto_news,
            ]),
            # Onchain / microstructure analyst: order book, OI, funding
            "fundamentals": ToolNode([
                get_crypto_ticker,
                get_orderbook,
                get_open_interest,
                get_funding_rate,
            ]),
        }

    def _log_state(self, symbol: str, trade_date: str, final_state: Dict[str, Any]):
        """Persist the final state as JSON for audit and debugging."""
        key = f"{symbol}_{trade_date}"
        self.log_states_dict[key] = {
            "symbol": symbol,
            "trade_date": trade_date,
            "market_report": final_state.get("market_report", ""),
            "sentiment_report": final_state.get("sentiment_report", ""),
            "news_report": final_state.get("news_report", ""),
            "onchain_report": final_state.get("fundamentals_report", ""),
            "investment_plan": final_state.get("investment_plan", ""),
            "trader_decision": final_state.get("trader_investment_plan", ""),
            "risk_debate": {
                "history": final_state.get("risk_debate_state", {}).get("history", ""),
                "judge_decision": final_state.get("risk_debate_state", {}).get("judge_decision", ""),
            },
            "final_trade_decision": final_state.get("final_trade_decision", ""),
        }

        safe_symbol = symbol.replace("/", "-").replace(":", "-")
        directory = Path(f"crypto_results/{safe_symbol}/logs/")
        directory.mkdir(parents=True, exist_ok=True)

        log_path = directory / f"state_{trade_date.replace(' ', '_').replace(':', '-')}.json"
        with open(log_path, "w", encoding="utf-8") as f:
            json.dump(self.log_states_dict, f, indent=2, ensure_ascii=False)

        logger.debug("State logged to %s", log_path)
