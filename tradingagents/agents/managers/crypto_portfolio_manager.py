# tradingagents/agents/managers/crypto_portfolio_manager.py
"""
加密货币组合管理者（最终决策者）—— 重构版

重构要点（按 solv.md 阶段二要求）：
1. LLM 只负责输出 Direction（LONG/SHORT/NEUTRAL）和 Conviction Score（1-10）
2. 仓位大小、止损、止盈由 Python 硬编码数学模型计算
3. 内置 BTC 200 日均线硬性拦截器：BTC 跌破 200 日均线时，强制禁止做多
4. ATR 公式：
   - Stop_Loss_Distance = ATR_MULTIPLIER * ATR14
   - Position_Size = (Capital * RISK_PER_TRADE) / Stop_Loss_Distance
   - 单笔最大亏损不超过总资金的 RISK_PER_TRADE（默认 1%）

数学参数（可通过 config 覆盖）：
   - RISK_PER_TRADE: 0.01（单笔最大亏损 1%）
   - ATR_MULTIPLIER: 1.5（止损 = 1.5 × ATR14）
   - TP1_RR: 2.0（止盈1 = 入场价 ± 2.0 × 止损距离）
   - TP2_RR: 3.5（止盈2 = 入场价 ± 3.5 × 止损距离）
   - MAX_POSITION_PCT: 0.30（单笔仓位上限为总资金 30%）
   - LITE_POSITION_SCALE: 0.5（LONG-LITE/SHORT-LITE 时仓位缩半）
"""

import re
import logging
import ccxt
import pandas as pd
from typing import Optional, Tuple, Dict, Any

from tradingagents.agents.utils.agent_utils import build_instrument_context, get_language_instruction
from tradingagents.dataflows.config import get_config

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────
# 风控硬参数（核心数学常数，不交由 LLM 决定）
# ─────────────────────────────────────────────────────────
RISK_PER_TRADE = 0.01       # 每笔最大亏损占总资金比例（1%）
ATR_MULTIPLIER = 1.5        # 止损 = 1.5 × ATR14
TP1_RISK_REWARD = 2.0       # 止盈1 盈亏比（2R）
TP2_RISK_REWARD = 3.5       # 止盈2 盈亏比（3.5R）
MAX_POSITION_PCT = 0.30     # 单笔仓位上限（总资金 30%，防止过度集中）
LITE_POSITION_SCALE = 0.5   # LONG-LITE / SHORT-LITE 仓位缩半系数
BTC_MA200_PERIOD = 200      # BTC 200 日均线周期


# ─────────────────────────────────────────────────────────
# 工具函数：从 Bitget 获取 ATR 和 200 日均线
# ─────────────────────────────────────────────────────────

def _normalize_symbol(symbol: str, exchange: str = "gate") -> str:
    """
    标准化交易对符号格式以适应不同交易所。
    
    Args:
        symbol: 原始符号，如 'BTCUSDT', 'BTC/USDT:USDT', 'BTC/USDT'
        exchange: 目标交易所 ('gate', 'binance', 'bitget')
    
    Returns:
        格式化后的符号
    """
    # 移除所有可能的后缀
    clean = symbol.replace(":USDT", "").replace("/USDT", "").replace("USDT", "").strip()
    
    if exchange == "gate":
        # Gate.io 合约：BTC/USDT:USDT
        return f"{clean}/USDT:USDT"
    elif exchange == "binance":
        # Binance 合约：BTC/USDT (spot format for fapi)
        return f"{clean}/USDT"
    elif exchange == "bitget":
        # Bitget 合约：BTC/USDT:USDT
        return f"{clean}/USDT:USDT"
    else:
        return symbol


# ─────────────────────────────────────────────────────────
# 工具函数：从 Bitget 获取 ATR 和 200 日均线
# ─────────────────────────────────────────────────────────

def _fetch_atr_and_price(
    symbol: str,
    timeframe: str = "1d",
    period: int = 14,
    extra_limit: int = 50,
) -> Tuple[Optional[float], Optional[float]]:
    """
    通过 CCXT 获取指定交易对的 ATR14 和最新已收盘价格。
    优先使用 Bitget，失败时自动降级到 Binance。

    Args:
        symbol:     交易对，如 'BTC/USDT:USDT'
        timeframe:  K 线周期
        period:     ATR 计算窗口（默认 14）
        extra_limit: 额外多拉的 K 线数量（保证 ATR 计算有足够历史）

    Returns:
        (atr14, current_price) 或 (None, None) 若获取失败
    """
    # 尝试 Bitget（主数据源）
    try:
        from tradingagents.dataflows.bitget_vendor import get_bitget_exchange, _filter_closed_daily_candles
        exchange = get_bitget_exchange()

        limit = period + extra_limit + 1  # +1 以备过滤当前未收盘 K 线
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
        if not ohlcv:
            return None, None

        df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
        df["datetime"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
        df = df.sort_values("datetime").reset_index(drop=True)

        # 保存原始收盘价（用于获取最新价格）
        original_close = df["close"].iloc[-1]

        # 日线模式强制过滤未收盘 K 线（ATR 计算需要）
        if timeframe in ("1d", "3d"):
            df = _filter_closed_daily_candles(df)

        if len(df) < period + 1:
            return None, None

        # 计算 ATR（真实波幅均值）
        high = df["high"]
        low = df["low"]
        close = df["close"]
        tr = pd.concat([
            high - low,
            (high - close.shift()).abs(),
            (low - close.shift()).abs(),
        ], axis=1).max(axis=1)
        atr = tr.rolling(period).mean().iloc[-1]
        
        # 使用原始最新收盘价，而不是过滤后的价格
        current_price = original_close

        return float(atr), float(current_price)

    except Exception as e:
        logger.warning("Bitget ATR 获取失败 (%s %s): %s", symbol, timeframe, e)
        logger.info("尝试降级到 Binance 获取 ATR 数据...")

    # 降级到 Binance（备用数据源）
    try:
        import ccxt
        from tradingagents.dataflows.bitget_vendor import _filter_closed_daily_candles
        
        # Binance 测试网不支持 fapiPublic，强制使用实盘 API（只读，不下单）
        exchange = ccxt.binanceusdm({
            'options': {'defaultType': 'future'},
            'enableRateLimit': True,
        })
        logger.info("使用 Binance 实盘 API 获取 ATR（只读模式）")

        # Binance 测试网不支持 fapiPublic 端点，需要使用实盘或调整配置
        limit = period + extra_limit + 1
        ohlcv = exchange.fetch_ohlcv(symbol.replace(":USDT", "/USDT"), timeframe=timeframe, limit=limit)
        if not ohlcv:
            return None, None

        df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
        df["datetime"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
        df = df.sort_values("datetime").reset_index(drop=True)

        # 日线模式强制过滤未收盘 K 线
        if timeframe in ("1d", "3d"):
            df = _filter_closed_daily_candles(df)

        if len(df) < period + 1:
            return None, None

        # 计算 ATR（真实波幅均值）
        high = df["high"]
        low = df["low"]
        close = df["close"]
        tr = pd.concat([
            high - low,
            (high - close.shift()).abs(),
            (low - close.shift()).abs(),
        ], axis=1).max(axis=1)
        atr = tr.rolling(period).mean().iloc[-1]
        current_price = close.iloc[-1]

        logger.info("Binance ATR 获取成功：%s USDT", atr)
        return float(atr), float(current_price)

    except Exception as e:
        logger.error("Binance ATR 获取也失败 (%s %s): %s", symbol, timeframe, e)
        logger.info("尝试降级到 Gate.io 获取 ATR 数据...")

    # 降级到 Gate.io（第三备用数据源）
    try:
        import ccxt
        from tradingagents.dataflows.bitget_vendor import _filter_closed_daily_candles

        exchange = ccxt.gate({
            'options': {'defaultType': 'swap'},
            'enableRateLimit': True,
        })
        logger.info("使用 Gate.io 获取 ATR（只读模式）")

        # Gate.io 需要标准格式：BTC/USDT:USDT
        gate_symbol = _normalize_symbol(symbol, "gate")
        limit = period + extra_limit + 1
        ohlcv = exchange.fetch_ohlcv(gate_symbol, timeframe=timeframe, limit=limit)
        if not ohlcv:
            return None, None

        df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
        df["datetime"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
        df = df.sort_values("datetime").reset_index(drop=True)

        # 保存原始收盘价（用于获取最新价格）
        original_close = df["close"].iloc[-1]

        # 日线模式强制过滤未收盘 K 线（ATR 计算需要）
        if timeframe in ("1d", "3d"):
            df = _filter_closed_daily_candles(df)

        if len(df) < period + 1:
            return None, None

        # 计算 ATR（真实波幅均值）
        high = df["high"]
        low = df["low"]
        close = df["close"]
        tr = pd.concat([
            high - low,
            (high - close.shift()).abs(),
            (low - close.shift()).abs(),
        ], axis=1).max(axis=1)
        atr = tr.rolling(period).mean().iloc[-1]
        
        # 使用原始最新收盘价，而不是过滤后的价格
        current_price = original_close

        logger.info("Gate.io ATR 获取成功：%s USDT", atr)
        return float(atr), float(current_price)

    except Exception as e:
        logger.error("Gate.io ATR 获取也失败 (%s %s): %s", symbol, timeframe, e)
        return None, None


def _fetch_btc_ma200(timeframe: str = "1d") -> Tuple[Optional[float], Optional[float]]:
    """
    获取 BTC 的 200 日均线和当前已收盘价，用于趋势拦截器。
    支持多交易所降级：Bitget → Binance → Gate.io

    Returns:
        (btc_price, btc_ma200) 或 (None, None) 若获取失败
    """
    btc_symbol = "BTC/USDT:USDT"

    # ── 尝试 1: Bitget（主数据源）─────────────────────────────────────
    try:
        from tradingagents.dataflows.bitget_vendor import get_bitget_exchange, _filter_closed_daily_candles
        exchange = get_bitget_exchange()

        ohlcv = exchange.fetch_ohlcv(btc_symbol, timeframe=timeframe, limit=BTC_MA200_PERIOD + 2)
        if not ohlcv:
            return None, None

        df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
        df["datetime"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
        df = df.sort_values("datetime").reset_index(drop=True)

        # 保存原始收盘价（用于获取最新价格）
        original_close = df["close"].iloc[-1]

        if timeframe in ("1d", "3d"):
            df = _filter_closed_daily_candles(df)

        if len(df) < BTC_MA200_PERIOD:
            logger.warning("BTC 数据不足 %d 根日线，跳过 200MA 拦截", BTC_MA200_PERIOD)
            return None, None

        btc_price = original_close
        btc_ma200 = float(df["close"].rolling(BTC_MA200_PERIOD).mean().iloc[-1])
        logger.info("Bitget BTC 200MA 获取成功：价格=%.0f, MA200=%.0f", btc_price, btc_ma200)
        return btc_price, btc_ma200

    except Exception as e:
        logger.warning("Bitget BTC 200MA 获取失败：%s，尝试降级到 Binance", e)

    # ── 尝试 2: Binance（备用数据源）─────────────────────────────────
    try:
        import ccxt
        from tradingagents.dataflows.bitget_vendor import _filter_closed_daily_candles

        exchange = ccxt.binanceusdm({
            'options': {'defaultType': 'future'},
            'enableRateLimit': True,
        })
        logger.info("使用 Binance 实盘 API 获取 BTC 200MA（只读模式）")

        ohlcv = exchange.fetch_ohlcv("BTC/USDT", timeframe=timeframe, limit=BTC_MA200_PERIOD + 2)
        if not ohlcv:
            return None, None

        df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
        df["datetime"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
        df = df.sort_values("datetime").reset_index(drop=True)

        # 保存原始收盘价（用于获取最新价格）
        original_close = df["close"].iloc[-1]

        if timeframe in ("1d", "3d"):
            df = _filter_closed_daily_candles(df)

        if len(df) < BTC_MA200_PERIOD:
            return None, None

        btc_price = original_close
        btc_ma200 = float(df["close"].rolling(BTC_MA200_PERIOD).mean().iloc[-1])
        logger.info("Binance BTC 200MA 获取成功：价格=%.0f, MA200=%.0f", btc_price, btc_ma200)
        return btc_price, btc_ma200

    except Exception as e:
        logger.warning("Binance BTC 200MA 获取失败：%s，尝试降级到 Gate.io", e)

    # ── 尝试 3: Gate.io（第三备用数据源）──────────────────────────────
    try:
        import ccxt
        from tradingagents.dataflows.bitget_vendor import _filter_closed_daily_candles

        exchange = ccxt.gate({
            'options': {'defaultType': 'swap'},
            'enableRateLimit': True,
        })
        logger.info("使用 Gate.io 获取 BTC 200MA（只读模式）")

        # Gate.io 需要标准格式：BTC/USDT:USDT
        gate_symbol = _normalize_symbol(btc_symbol, "gate")
        ohlcv = exchange.fetch_ohlcv(gate_symbol, timeframe=timeframe, limit=BTC_MA200_PERIOD + 2)
        if not ohlcv:
            return None, None

        df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
        df["datetime"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
        df = df.sort_values("datetime").reset_index(drop=True)

        # 保存原始收盘价（用于获取最新价格）
        original_close = df["close"].iloc[-1]

        if timeframe in ("1d", "3d"):
            df = _filter_closed_daily_candles(df)

        if len(df) < BTC_MA200_PERIOD:
            return None, None

        btc_price = original_close
        btc_ma200 = float(df["close"].rolling(BTC_MA200_PERIOD).mean().iloc[-1])
        logger.info("Gate.io BTC 200MA 获取成功：价格=%.0f, MA200=%.0f", btc_price, btc_ma200)
        return btc_price, btc_ma200

    except Exception as e:
        logger.error("Gate.io BTC 200MA 也获取失败：%s", e)
        return None, None

        df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
        df["datetime"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
        df = df.sort_values("datetime").reset_index(drop=True)

        if timeframe in ("1d", "3d"):
            df = _filter_closed_daily_candles(df)

        if len(df) < BTC_MA200_PERIOD:
            logger.warning("BTC 数据不足 %d 根日线，跳过 200MA 拦截", BTC_MA200_PERIOD)
            return None, None

        btc_price = float(df["close"].iloc[-1])
        btc_ma200 = float(df["close"].rolling(BTC_MA200_PERIOD).mean().iloc[-1])
        return btc_price, btc_ma200

    except Exception as e:
        logger.warning("BTC 200MA 获取失败: %s", e)
        return None, None


# ─────────────────────────────────────────────────────────
# 硬编码仓位计算（数学模型，不依赖 LLM）
# ─────────────────────────────────────────────────────────

def compute_position_params(
    direction: str,          # "LONG" | "SHORT" | "LONG-LITE" | "SHORT-LITE" | "CLOSE"
    entry_price: float,
    atr14: float,
    capital_usdt: float,
    conviction_score: int,   # 1-10
    config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    基于 ATR 硬编码计算仓位参数，不允许 LLM 干预数学结果。

    公式：
        stop_loss_dist  = ATR_MULTIPLIER × ATR14
        position_usdt   = (capital × RISK_PER_TRADE) / stop_loss_dist
                          × clamp(conviction_score / 10, 0.5, 1.0)  # 信念分调节
        position_usdt   = min(position_usdt, capital × MAX_POSITION_PCT)

    LITE 信号时仓位额外缩半（LITE_POSITION_SCALE）。

    Args:
        direction:       来自 LLM 的方向决策
        entry_price:     当前已收盘价（市价入场）
        atr14:           14 周期 ATR
        capital_usdt:    账户总资金（USDT）
        conviction_score: LLM 的信念评分 1-10
        config:          可选配置覆盖

    Returns:
        包含所有执行参数的字典（可直接传入 bitget_executor）
    """
    cfg = config or {}
    risk_per_trade = cfg.get("risk_per_trade", RISK_PER_TRADE)
    atr_mult = cfg.get("atr_multiplier", ATR_MULTIPLIER)
    tp1_rr = cfg.get("tp1_risk_reward", TP1_RISK_REWARD)
    tp2_rr = cfg.get("tp2_risk_reward", TP2_RISK_REWARD)
    max_pos_pct = cfg.get("max_position_pct", MAX_POSITION_PCT)

    is_long = direction.startswith("LONG")
    is_lite = direction.endswith("LITE")

    # 止损距离（价格单位）
    stop_loss_dist = atr_mult * atr14

    # 信念分因子：conviction 1-10 映射到 0.5-1.0
    conviction_factor = max(0.5, min(1.0, conviction_score / 10.0))

    # 基础仓位（以最大亏损反推）
    # position_usdt = (capital × risk%) / stop_loss_pct_of_price
    stop_loss_pct = stop_loss_dist / entry_price
    raw_position_usdt = (capital_usdt * risk_per_trade * conviction_factor) / stop_loss_pct

    # LITE 信号额外缩半
    if is_lite:
        raw_position_usdt *= LITE_POSITION_SCALE

    # 上限保护：单笔最多 MAX_POSITION_PCT 的资金
    position_usdt = min(raw_position_usdt, capital_usdt * max_pos_pct)

    # 止损 / 止盈价格（基于 R 倍数）
    if is_long:
        stop_loss_price = entry_price - stop_loss_dist
        tp1_price = entry_price + tp1_rr * stop_loss_dist
        tp2_price = entry_price + tp2_rr * stop_loss_dist
    else:  # SHORT / SHORT-LITE
        stop_loss_price = entry_price + stop_loss_dist
        tp1_price = entry_price - tp1_rr * stop_loss_dist
        tp2_price = entry_price - tp2_rr * stop_loss_dist

    return {
        "direction": direction,
        "entry_price": round(entry_price, 4),
        "entry_type": "MARKET",
        "position_usdt": round(position_usdt, 2),
        "position_pct": round(position_usdt / capital_usdt * 100, 2),
        "stop_loss": round(stop_loss_price, 4),
        "take_profit_1": round(tp1_price, 4),
        "take_profit_2": round(tp2_price, 4),
        "atr14": round(atr14, 4),
        "stop_loss_dist": round(stop_loss_dist, 4),
        "conviction_score": conviction_score,
        "risk_pct": round(risk_per_trade * 100, 2),
        "max_loss_usdt": round(capital_usdt * risk_per_trade, 2),
    }


def format_execution_block(params: Dict[str, Any], rationale: str) -> str:
    """将仓位参数格式化为 Executor 可解析的标准输出字符串（中文版）。"""
    d = params["direction"]
    is_long = d.startswith("LONG")

    lines = [
        f"## 1. 最终决策",
        f"{d}",
        f"",
        f"## 2. 执行参数（Python ATR 模型计算，LLM 不可干预）",
        f"- 方向：{'做多' if is_long else '做空'}",
        f"- 杠杆：1x  [不使用杠杆，风险通过仓位大小控制]",
        f"- 仓位：{params['position_pct']}% 总资金（{params['position_usdt']} USDT）",
        f"- 入场：市价单",
        f"- 止损：{params['stop_loss']}  [= 入场价 {'-' if is_long else '+'} {ATR_MULTIPLIER}×ATR14({params['atr14']})]",
        f"- 止盈 1: {params['take_profit_1']}  [风险收益比 = {TP1_RISK_REWARD}:1]",
        f"- 止盈 2: {params['take_profit_2']}  [风险收益比 = {TP2_RISK_REWARD}:1]",
        f"- 持仓周期：1-3 天（日线波段）",
        f"- 最大亏损：{params['max_loss_usdt']} USDT（占总资金 {params['risk_pct']}%）",
        f"",
        f"## 3. LLM 决策理由",
        rationale,
        f"",
        f"## 4. 风险参数（Python 硬编码计算，LLM 不可覆盖）",
        f"- ATR14: {params['atr14']} USDT",
        f"- 止损距离：{params['stop_loss_dist']} USDT",
        f"- 信心评分：{params['conviction_score']}/10",
        f"- 单笔风险：{params['risk_pct']}%",
    ]
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────
# Agent 节点工厂
# ─────────────────────────────────────────────────────────

def create_crypto_portfolio_manager(llm, memory):
    """
    创建加密货币组合管理者节点。

    LLM 的职责被严格限定为：
    1. 输出方向（LONG / LONG-LITE / SHORT / SHORT-LITE / CLOSE）
    2. 输出信心评分（1-10）
    3. 输出简短的方向理由

    所有仓位计算、止损、止盈由 Python 数学模型硬编码完成。
    """
    def portfolio_manager_node(state) -> dict:
        symbol = state["company_of_interest"]
        instrument_context = build_instrument_context(symbol)
        config = get_config()

        history = state["risk_debate_state"]["history"]
        risk_debate_state = state["risk_debate_state"]
        market_report = state["market_report"]
        news_report = state["news_report"]
        onchain_report = state["fundamentals_report"]
        sentiment_report = state["sentiment_report"]
        trader_plan = state["investment_plan"]

        curr_situation = f"{market_report}\n\n{sentiment_report}\n\n{news_report}\n\n{onchain_report}"
        past_memories = memory.get_memories(curr_situation, n_matches=2)
        past_memory_str = "".join(rec["recommendation"] + "\n\n" for rec in past_memories)

        capital_usdt = config.get("capital_usdt", 1000.0)
        timeframe = config.get("timeframe", "1d")

        # ── Step 1: LLM 只决定方向和信心 ──────────────────────────────
        direction_prompt_template = """你是一家加密货币量化基金的首席投资组合经理。你的职责严格限定为：

1. 选择方向：LONG / LONG-LITE / SHORT / SHORT-LITE / CLOSE
2. 分配信心分数：整数从 1（最弱）到 10（最强）
3. 写 2-3 句理由

你不设置杠杆、仓位大小、止损或止盈价格。
这些由硬编码的 Python 风险引擎计算。

{instrument_context}

**上下文：**
- 研究团队的计划：{trader_plan}
- 风险辩论历史：{history}
- 过往决策经验：{past_memory_str}

**输出格式（严格遵循）：**
DIRECTION: <LONG|LONG-LITE|SHORT|SHORT-LITE|CLOSE>
CONVICTION: <1-10 整数>
RATIONALE: <2-3 句话>

要果断。只输出以上内容，不要输出其他内容。{lang_instruction}"""
        lang_instruction = get_language_instruction()
        direction_prompt = direction_prompt_template.format(
            instrument_context=instrument_context,
            trader_plan=trader_plan,
            history=history,
            past_memory_str=past_memory_str,
            lang_instruction=lang_instruction
        )

        from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
        prompt = ChatPromptTemplate.from_messages([
            ("system", "{system_message}"),
            MessagesPlaceholder(variable_name="messages"),
        ])
        chain = prompt.partial(system_message=direction_prompt) | llm
        llm_response = chain.invoke({"messages": state["messages"]})
        llm_text = llm_response.content

        # ── Step 2: 解析 LLM 输出 ──────────────────────────────────────
        direction, conviction_score, rationale = _parse_llm_direction_output(llm_text)

        # ── Step 3: BTC 200 日均线硬性拦截器 ──────────────────────────
        btc_price, btc_ma200 = _fetch_btc_ma200(timeframe=timeframe)
        intercepted = False
        intercept_note = ""

        if btc_price is not None and btc_ma200 is not None:
            if btc_price < btc_ma200 and direction in ("LONG", "LONG-LITE"):
                # BTC 跌破 200 日均线，强制禁止做多
                old_direction = direction
                direction = "CLOSE"
                intercepted = True
                intercept_note = (
                    f"\n⚠️  [硬性拦截] BTC 200 日均线拦截器触发："
                    f"BTC ${btc_price:.0f} < MA200 ${btc_ma200:.0f}。"
                    f"LLM 方向 '{old_direction}' 被强制覆盖 → CLOSE（仅平仓）。"
                )
                logger.warning(
                    "BTC 200MA 拦截器：BTC %.0f < MA200 %.0f — "
                    "覆盖 %s → CLOSE for %s",
                    btc_price, btc_ma200, old_direction, symbol
                )

        # ── Step 4: 若需开仓，Python 硬编码计算仓位 ────────────────────
        if direction == "CLOSE":
            final_text = _format_close_decision(symbol, rationale, intercept_note)
        else:
            # 获取 ATR14 用于仓位计算
            atr14, entry_price = _fetch_atr_and_price(symbol, timeframe=timeframe)

            if atr14 is None or entry_price is None:
                # ATR 获取失败 → 强制降级为 CLOSE（安全优先）
                logger.error(
                    "ATR 获取失败，无法计算仓位，强制降级为 CLOSE (%s)", symbol
                )
                final_text = (
                    "## 1. 最终决策\nCLOSE\n\n"
                    "## 2. 说明\nATR 数据不可用 — 无法计算仓位大小。"
                    "为保障资金安全，默认选择平仓观望。\n"
                    f"LLM 原意：{direction}（信心 {conviction_score}/10）"
                )
            else:
                params = compute_position_params(
                    direction=direction,
                    entry_price=entry_price,
                    atr14=atr14,
                    capital_usdt=capital_usdt,
                    conviction_score=conviction_score,
                    config=config,
                )
                final_text = format_execution_block(params, rationale)
                if intercept_note:
                    final_text = intercept_note + "\n\n" + final_text

        # ── Step 5: 生成风险经理报告 ───────────────────────────────────
        risk_assessment = ""
        if atr14 is not None and entry_price is not None and direction != "CLOSE":
            params = compute_position_params(
                direction=direction,
                entry_price=entry_price,
                atr14=atr14,
                capital_usdt=capital_usdt,
                conviction_score=conviction_score,
                config=config,
            )
            risk_assessment = f"""## 🛡️ 风险经理评估报告

### 1. 风险参数计算（Python 硬编码，不可被 LLM 干预）
- **ATR14**: {params['atr14']} USDT
- **止损距离**: {params['stop_loss_dist']} USDT（占价格 {params['stop_loss_dist']/entry_price*100:.2f}%）
- **仓位大小**: {params['position_usdt']} USDT（占总资金 {params['position_pct']:.1f}%）
- **最大亏损**: {params['max_loss_usdt']} USDT（占总资金 {params['risk_pct']:.1f}%）
- **杠杆倍数**: 1x（不使用杠杆，风险通过仓位大小控制）

### 2. 风险评估
- **波动率评估**: {'高' if params['atr14']/entry_price > 0.03 else '中' if params['atr14']/entry_price > 0.015 else '低'}（ATR/Price = {params['atr14']/entry_price*100:.2f}%）
- **风险收益比**:
  - TP1 盈亏比 = 2.0:1
  - TP2 盈亏比 = 3.5:1
- **建议风险等级**: {'⚠️ 高风险' if params['atr14']/entry_price > 0.03 else '⚖️ 中等风险' if params['atr14']/entry_price > 0.015 else '✅ 低风险'}

### 3. 风控规则执行
- ✅ 止损必须基于 ATR（1.5×ATR14）
- ✅ 单笔最大亏损不超过 1% 资金
- ✅ 单一方向最大仓位不超过 30%
- ✅ LITE 信号仓位减半

### 4. 风险经理总结
基于当前波动率和仓位计算，该交易的风险可控。止损位设置合理，风险收益比符合量化标准。建议严格执行止损纪律。
"""

        # ── Step 6: 更新状态 ─────────────────────────────────────────
        new_risk_debate_state = {
            "judge_decision": final_text,
            "history": risk_debate_state["history"],
            "aggressive_history": risk_debate_state["aggressive_history"],
            "conservative_history": risk_debate_state["conservative_history"],
            "neutral_history": risk_debate_state["neutral_history"],
            "latest_speaker": "Judge",
            "current_aggressive_response": risk_debate_state["current_aggressive_response"],
            "current_conservative_response": risk_debate_state["current_conservative_response"],
            "current_neutral_response": risk_debate_state["current_neutral_response"],
            "count": risk_debate_state["count"],
        }

        return {
            "risk_debate_state": new_risk_debate_state,
            "final_trade_decision": final_text,
            "risk_assessment": risk_assessment,
        }

    return portfolio_manager_node


# ─────────────────────────────────────────────────────────
# 私有解析函数
# ─────────────────────────────────────────────────────────

def _parse_llm_direction_output(text: str):
    """
    从 LLM 输出中解析：
    - DIRECTION: LONG | LONG-LITE | SHORT | SHORT-LITE | CLOSE
    - CONVICTION: 1-10
    - RATIONALE: 文字说明
    """
    # 方向解析
    direction = "CLOSE"
    dir_patterns = [
        (r'\bLONG-LITE\b', 'LONG-LITE'),
        (r'\bSHORT-LITE\b', 'SHORT-LITE'),
        (r'\bLONG\b', 'LONG'),
        (r'\bSHORT\b', 'SHORT'),
        (r'\bCLOSE\b', 'CLOSE'),
    ]
    m = re.search(r'DIRECTION\s*:\s*(\S+)', text, re.IGNORECASE)
    if m:
        raw = m.group(1).upper().strip()
        for pat, canonical in dir_patterns:
            if re.search(pat, raw):
                direction = canonical
                break
    else:
        # 回退：全文搜索
        for pat, canonical in dir_patterns:
            if re.search(pat, text, re.IGNORECASE):
                direction = canonical
                break

    # 信念分解析
    conviction_score = 5  # 默认中立
    m = re.search(r'CONVICTION\s*:\s*(\d+)', text, re.IGNORECASE)
    if m:
        conviction_score = max(1, min(10, int(m.group(1))))

    # 理由解析
    rationale = "No rationale provided."
    m = re.search(r'RATIONALE\s*:\s*(.+)', text, re.IGNORECASE | re.DOTALL)
    if m:
        rationale = m.group(1).strip()[:500]  # 截断超长文本

    logger.info(
        "LLM direction parsed: %s (conviction=%d/10)",
        direction, conviction_score
    )
    return direction, conviction_score, rationale


def _format_close_decision(symbol: str, rationale: str, note: str = "") -> str:
    """格式化 CLOSE 决策的输出文本。"""
    lines = [
        "## 1. 最终决策",
        "CLOSE（平仓观望）",
        "",
        "## 2. 执行参数",
        "- 方向：FLAT（空仓）",
        "- 操作：关闭该交易对的所有仓位",
        "- 入场：不适用",
        "- 止损：不适用",
        "- 止盈 1：不适用",
        "- 止盈 2：不适用",
        "",
        "## 3. 决策理由",
        rationale,
    ]
    result = "\n".join(lines)
    if note:
        result = note.strip() + "\n\n" + result
    return result
