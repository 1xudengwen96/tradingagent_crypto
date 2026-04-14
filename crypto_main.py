#!/usr/bin/env python3
# crypto_main.py
"""
加密货币合约交易机器人主入口
使用 APScheduler 定时驱动多智能体分析流水线，自动对 BTC 和 ETH 永续合约做出交易决策。

用法:
    python crypto_main.py                 # 定时运行（每4小时）
    python crypto_main.py --once          # 立即运行一次后退出
    python crypto_main.py --symbol ETHUSDT  # 只分析 ETH
    python crypto_main.py --no-execute    # 只分析，不实际下单
"""

import argparse
import json
import logging
import sys
import os
from datetime import datetime, timezone
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# ---- Logging setup -------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("crypto_trading.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger("crypto_main")

# ---- Suppress noisy third-party loggers ----------------------------------
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("ccxt").setLevel(logging.WARNING)
logging.getLogger("langchain").setLevel(logging.WARNING)


def _send_feishu_card(webhook_url: str, header_title: str, header_template: str, content: str, fields: list = None) -> None:
    """Internal helper: send a Feishu interactive card.

    Args:
        webhook_url: Full webhook URL string
        header_title: Card header title text
        header_template: Card color template (blue/green/red/orange/purple)
        content: Markdown content body
        fields: Optional list of field dicts for the footer
    """
    if not webhook_url:
        return

    elements = [
        {
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": content[:2000],  # Feishu has message size limits
            },
        }
    ]

    if fields:
        elements.append({"tag": "hr"})
        elements.append({
            "tag": "div",
            "fields": fields,
        })

    payload = {
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {"tag": "plain_text", "content": header_title},
                "template": header_template,
            },
            "elements": elements,
        },
    }

    try:
        import requests
        resp = requests.post(webhook_url, json=payload, timeout=10)
        if resp.status_code == 200:
            logger.info("Feishu card sent: %s", header_title)
        else:
            logger.warning("Feishu webhook returned HTTP %d for %s", resp.status_code, header_title)
    except Exception:
        logger.exception("Failed to send Feishu card: %s", header_title)


def _get_webhook(env_var: str) -> str:
    """Get webhook URL from environment variable."""
    return os.getenv(env_var, "")


def send_feishu_multi_notifications(symbol: str, final_state: dict, execution_result, now_str: str) -> None:
    """Send AI analysis results to multiple Feishu bots, each representing a different role.

    Roles:
    - 📊 Market Analyst (FEISHU_WEBHOOK_ANALYST)
    - 😊 Sentiment Analyst (FEISHU_WEBHOOK_SENTIMENT) - optional
    - 📰 News Analyst (FEISHU_WEBHOOK_NEWS) - optional
    - 💎 Fundamentals/Onchain Analyst (FEISHU_WEBHOOK_FUNDAMENTALS) - optional
    - ⚖️ Research Manager (FEISHU_WEBHOOK_MANAGER)
    - 🛡️ Risk Manager (FEISHU_WEBHOOK_RISK)
    - 🎯 Final Decision / Trader (FEISHU_WEBHOOK_TRADER)
    - 📋 Summary Card (FEISHU_WEBHOOK_URL) - fallback/general
    """

    # ─── 1. 📈 Market Analyst Report ──────────────────────────────────────
    if final_state.get("market_report"):
        webhook = _get_webhook("FEISHU_WEBHOOK_ANALYST") or _get_webhook("FEISHU_WEBHOOK_URL")
        if webhook:
            content = final_state["market_report"][:3000]
            fields = [
                {"is_short": True, "text": {"tag": "lark_md", "content": f"**角色**\n📈 市场分析师"}},
                {"is_short": True, "text": {"tag": "lark_md", "content": f"**交易对**\n{symbol}"}},
                {"is_short": True, "text": {"tag": "lark_md", "content": f"**时间**\n{now_str}"}},
            ]
            _send_feishu_card(webhook, f"📈 {symbol} 市场分析报告", "blue", content, fields)

    # ─── 2. 😊 Sentiment Analyst Report ──────────────────────────────────
    if final_state.get("sentiment_report"):
        webhook = _get_webhook("FEISHU_WEBHOOK_SENTIMENT") or _get_webhook("FEISHU_WEBHOOK_URL")
        if webhook:
            content = final_state["sentiment_report"][:3000]
            fields = [
                {"is_short": True, "text": {"tag": "lark_md", "content": f"**角色**\n😊 情绪分析师"}},
                {"is_short": True, "text": {"tag": "lark_md", "content": f"**交易对**\n{symbol}"}},
                {"is_short": True, "text": {"tag": "lark_md", "content": f"**时间**\n{now_str}"}},
            ]
            _send_feishu_card(webhook, f"😊 {symbol} 情绪分析报告", "blue", content, fields)

    # ─── 3. 📰 News Analyst Report ───────────────────────────────────────
    if final_state.get("news_report"):
        webhook = _get_webhook("FEISHU_WEBHOOK_NEWS") or _get_webhook("FEISHU_WEBHOOK_URL")
        if webhook:
            content = final_state["news_report"][:3000]
            fields = [
                {"is_short": True, "text": {"tag": "lark_md", "content": f"**角色**\n📰 新闻分析师"}},
                {"is_short": True, "text": {"tag": "lark_md", "content": f"**交易对**\n{symbol}"}},
                {"is_short": True, "text": {"tag": "lark_md", "content": f"**时间**\n{now_str}"}},
            ]
            _send_feishu_card(webhook, f"📰 {symbol} 新闻分析报告", "blue", content, fields)

    # ─── 4. 💎 Fundamentals/Onchain Analyst Report ───────────────────────
    if final_state.get("fundamentals_report") or final_state.get("onchain_report"):
        webhook = _get_webhook("FEISHU_WEBHOOK_FUNDAMENTALS") or _get_webhook("FEISHU_WEBHOOK_URL")
        if webhook:
            report = final_state.get("fundamentals_report") or final_state.get("onchain_report", "")
            content = report[:3000]
            role_icon = "💎" if final_state.get("fundamentals_report") else "🔗"
            role_name = "基本面分析师" if final_state.get("fundamentals_report") else "链上数据分析师"
            fields = [
                {"is_short": True, "text": {"tag": "lark_md", "content": f"**角色**\n{role_icon} {role_name}"}},
                {"is_short": True, "text": {"tag": "lark_md", "content": f"**交易对**\n{symbol}"}},
                {"is_short": True, "text": {"tag": "lark_md", "content": f"**时间**\n{now_str}"}},
            ]
            _send_feishu_card(webhook, f"{role_icon} {symbol} {role_name}报告", "blue", content, fields)

    # ─── 5. ⚖️ Research Manager (Bull/Bear Debate Summary) ──────────────
    debate_state = final_state.get("investment_debate_state", {})
    if debate_state.get("judge_decision"):
        webhook = _get_webhook("FEISHU_WEBHOOK_MANAGER") or _get_webhook("FEISHU_WEBHOOK_URL")
        if webhook:
            content = debate_state["judge_decision"][:3000]

            # Add bull/bear context if available
            bull_hist = debate_state.get("bull_history", [])
            bear_hist = debate_state.get("bear_history", [])
            if bull_hist or bear_hist:
                context_parts = []
                if bull_hist:
                    last_bull = bull_hist[-1] if isinstance(bull_hist, list) else bull_hist
                    context_parts.append(f"**🐂 多头观点**\n{last_bull[:500]}")
                if bear_hist:
                    last_bear = bear_hist[-1] if isinstance(bear_hist, list) else bear_hist
                    context_parts.append(f"**🐻 空头观点**\n{last_bear[:500]}")
                if context_parts:
                    content = "\n\n".join(context_parts) + f"\n\n---\n\n**⚖️ 研究经理裁决**\n\n{content}"

            fields = [
                {"is_short": True, "text": {"tag": "lark_md", "content": f"**角色**\n⚖️ 研究经理"}},
                {"is_short": True, "text": {"tag": "lark_md", "content": f"**交易对**\n{symbol}"}},
                {"is_short": True, "text": {"tag": "lark_md", "content": f"**时间**\n{now_str}"}},
            ]
            _send_feishu_card(webhook, f"⚖️ {symbol} 研究经理裁决", "orange", content, fields)

    # ─── 6. 💼 Trader Recommendation ─────────────────────────────────────
    if final_state.get("trader_investment_plan"):
        # Trader is grouped with risk manager or sent separately if trader webhook exists
        webhook = _get_webhook("FEISHU_WEBHOOK_TRADER")
        if webhook:
            content = final_state["trader_investment_plan"][:3000]
            fields = [
                {"is_short": True, "text": {"tag": "lark_md", "content": f"**角色**\n💼 交易员"}},
                {"is_short": True, "text": {"tag": "lark_md", "content": f"**交易对**\n{symbol}"}},
                {"is_short": True, "text": {"tag": "lark_md", "content": f"**时间**\n{now_str}"}},
            ]
            _send_feishu_card(webhook, f"💼 {symbol} 交易员建议", "blue", content, fields)

    # ─── 7. 🛡️ Risk Manager Decision ────────────────────────────────────
    if final_state.get("risk_debate_state", {}).get("judge_decision"):
        webhook = _get_webhook("FEISHU_WEBHOOK_RISK") or _get_webhook("FEISHU_WEBHOOK_URL")
        if webhook:
            content = final_state["risk_debate_state"]["judge_decision"][:3000]
            fields = [
                {"is_short": True, "text": {"tag": "lark_md", "content": f"**角色**\n🛡️ 风险经理"}},
                {"is_short": True, "text": {"tag": "lark_md", "content": f"**交易对**\n{symbol}"}},
                {"is_short": True, "text": {"tag": "lark_md", "content": f"**时间**\n{now_str}"}},
            ]
            _send_feishu_card(webhook, f"🛡️ {symbol} 风险评估", "orange", content, fields)

    # ─── 8. 🎯 Final Decision ────────────────────────────────────────────
    if final_state.get("final_trade_decision"):
        webhook = _get_webhook("FEISHU_WEBHOOK_TRADER") or _get_webhook("FEISHU_WEBHOOK_URL")
        if webhook:
            content = final_state["final_trade_decision"][:3000]

            # Parse execution status
            status_emoji = "⏸️ 仅分析"
            status_text = "未执行交易"
            if execution_result is not None:
                if execution_result.success:
                    order_ids = [o.get("id", "?") for o in execution_result.orders]
                    status_emoji = "✅ 已下单"
                    status_text = f"订单: {', '.join(order_ids)}"
                else:
                    status_emoji = "❌ 下单失败"
                    status_text = execution_result.error or "未知错误"

            fields = [
                {"is_short": True, "text": {"tag": "lark_md", "content": f"**角色**\n🎯 最终决策"}},
                {"is_short": True, "text": {"tag": "lark_md", "content": f"**执行状态**\n{status_emoji} {status_text}"}},
                {"is_short": True, "text": {"tag": "lark_md", "content": f"**时间**\n{now_str}"}},
            ]
            _send_feishu_card(webhook, f"🎯 {symbol} 最终决策", "green" if execution_result is None or execution_result.success else "red", content, fields)


def send_feishu_notification(symbol: str, decision_text: str, execution_result, final_state: dict = None) -> None:
    """Send AI analysis result to Feishu webhook(s).

    This is the main entry point. It delegates to send_feishu_multi_notifications
    for role-based multi-bot messaging. If no role-specific webhooks are configured,
    it falls back to sending a single summary card to FEISHU_WEBHOOK_URL.
    """
    webhook_url = os.getenv("FEISHU_WEBHOOK_URL", "")
    now_str = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')

    # Try multi-bot notifications first
    if final_state:
        send_feishu_multi_notifications(symbol, final_state, execution_result, now_str)

    # Fallback: if no role-specific webhooks found, send a single summary card
    if not webhook_url:
        return

    # Check if any role-specific webhook was configured
    role_webhooks = [
        "FEISHU_WEBHOOK_ANALYST", "FEISHU_WEBHOOK_SENTIMENT", "FEISHU_WEBHOOK_NEWS",
        "FEISHU_WEBHOOK_FUNDAMENTALS", "FEISHU_WEBHOOK_MANAGER", "FEISHU_WEBHOOK_RISK",
        "FEISHU_WEBHOOK_TRADER",
    ]
    has_role_webhook = any(os.getenv(w, "") for w in role_webhooks)

    if has_role_webhook:
        # Multi-bot mode: role-specific bots already sent above
        return

    # Single-bot mode: send a consolidated summary card
    # Parse execution status
    status_emoji = "⏸️ 仅分析"
    status_text = "未执行交易"
    if execution_result is not None:
        if execution_result.success:
            order_ids = [o.get("id", "?") for o in execution_result.orders]
            status_emoji = "✅ 已下单"
            status_text = f"订单: {', '.join(order_ids)}"
        else:
            status_emoji = "❌ 下单失败"
            status_text = execution_result.error or "未知错误"

    # Build detailed markdown content from final_state if available
    detailed_content = ""
    if final_state:
        reports = []

        # Market Analyst Report
        if final_state.get("market_report"):
            reports.append(f"**📈 市场分析师**\n{final_state['market_report'][:800]}")

        # Sentiment Report
        if final_state.get("sentiment_report"):
            reports.append(f"**😊 情绪分析师**\n{final_state['sentiment_report'][:800]}")

        # News Report
        if final_state.get("news_report"):
            reports.append(f"**📰 新闻分析师**\n{final_state['news_report'][:800]}")

        # Fundamentals/Onchain Report
        if final_state.get("fundamentals_report"):
            reports.append(f"**💎 基本面分析师**\n{final_state['fundamentals_report'][:800]}")
        elif final_state.get("onchain_report"):
            reports.append(f"**🔗 链上数据分析师**\n{final_state['onchain_report'][:800]}")

        # Bull Researcher
        if final_state.get("investment_debate_state", {}).get("bull_history"):
            bull_hist = final_state["investment_debate_state"]["bull_history"]
            if bull_hist:
                reports.append(f"**🐂 多头研究员**\n{bull_hist[-1][:800] if isinstance(bull_hist, list) else bull_hist[:800]}")

        # Bear Researcher
        if final_state.get("investment_debate_state", {}).get("bear_history"):
            bear_hist = final_state["investment_debate_state"]["bear_history"]
            if bear_hist:
                reports.append(f"**🐻 空头研究员**\n{bear_hist[-1][:800] if isinstance(bear_hist, list) else bear_hist[:800]}")

        # Investment Judge (Research Manager)
        if final_state.get("investment_debate_state", {}).get("judge_decision"):
            reports.append(f"**⚖️ 研究经理**\n{final_state['investment_debate_state']['judge_decision'][:800]}")

        # Trader Recommendation
        if final_state.get("trader_investment_plan"):
            reports.append(f"**💼 交易员**\n{final_state['trader_investment_plan'][:800]}")

        # Risk Debate Judge
        if final_state.get("risk_debate_state", {}).get("judge_decision"):
            reports.append(f"**🛡️ 风险经理**\n{final_state['risk_debate_state']['judge_decision'][:800]}")

        # Final Decision
        if final_state.get("final_trade_decision"):
            reports.append(f"**🎯 最终决策**\n{final_state['final_trade_decision'][:800]}")

        # Combine reports
        if reports:
            detailed_content = "\n\n---\n\n".join(reports)
        else:
            detailed_content = decision_text[:1500]
    else:
        detailed_content = decision_text[:1500]

    # Build card payload
    payload = {
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {"tag": "plain_text", "content": f"📊 {symbol} 分析报告"},
                "template": "blue",
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": detailed_content[:2000],  # Feishu has message size limits
                    },
                },
                {"tag": "hr"},
                {
                    "tag": "div",
                    "fields": [
                        {
                            "is_short": True,
                            "text": {"tag": "lark_md", "content": f"**执行状态**\n{status_emoji} {status_text}"},
                        },
                        {
                            "is_short": True,
                            "text": {
                                "tag": "lark_md",
                                "content": f"**时间**\n{now_str}",
                            },
                        },
                    ],
                },
            ],
        },
    }

    try:
        import requests
        resp = requests.post(webhook_url, json=payload, timeout=10)
        if resp.status_code == 200:
            logger.info("Feishu notification sent for %s", symbol)
        else:
            logger.warning("Feishu webhook returned HTTP %d for %s", resp.status_code, symbol)
    except Exception:
        logger.exception("Failed to send Feishu notification for %s", symbol)


def send_feishu_error_notification(symbol: str, error_text: str) -> None:
    """Send error notification to Feishu webhook."""
    webhook_url = os.getenv("FEISHU_WEBHOOK_URL", "")
    if not webhook_url:
        return

    payload = {
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {"tag": "plain_text", "content": f"❌ {symbol} 分析错误"},
                "template": "red",
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "tag": "plain_text",
                        "content": error_text[:1500],
                    },
                },
                {"tag": "hr"},
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"**时间**\n{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}\n\n**建议**: 检查API Key配置和LLM服务状态",
                    },
                },
            ],
        },
    }

    try:
        import requests
        resp = requests.post(webhook_url, json=payload, timeout=10)
        if resp.status_code == 200:
            logger.info("Feishu error notification sent for %s", symbol)
        else:
            logger.warning("Feishu webhook returned HTTP %d for %s", resp.status_code, symbol)
    except Exception:
        logger.exception("Failed to send Feishu error notification for %s", symbol)


# ─── Trade history persistence ────────────────────────────────────────────

_TRADE_HISTORY_FILE = os.path.join(os.path.expanduser("~"), ".tradingbot", "trade_history.json")


def record_trade_history(action: str, symbol: str, details: dict) -> None:
    """Append a trade record to the persistent history file."""
    try:
        history_file = _TRADE_HISTORY_FILE
        history = []
        if os.path.exists(history_file):
            try:
                with open(history_file, "r", encoding="utf-8") as f:
                    history = json.load(f)
            except (json.JSONDecodeError, IOError):
                history = []

        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": action,
            "symbol": symbol,
            "details": details,
        }
        history.append(entry)
        if len(history) > 500:
            history = history[-500:]

        os.makedirs(os.path.dirname(history_file), exist_ok=True)
        with open(history_file, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2, ensure_ascii=False)
    except Exception:
        logger.exception("Failed to record trade history for %s", symbol)


def run_analysis(graph, symbols: list, auto_execute: bool, timeframe: str = "4h"):
    """Run one full analysis cycle for all configured symbols."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    logger.info("=" * 60)
    logger.info("Analysis cycle started at %s | timeframe=%s", now, timeframe)
    logger.info("Symbols: %s | auto_execute=%s", symbols, auto_execute)
    logger.info("=" * 60)

    for symbol in symbols:
        logger.info("▶ Analysing %s (timeframe=%s) ...", symbol, timeframe)
        logger.info("📡 Step 1: Fetching OHLCV K-line data from Bitget exchange...")
        logger.info("📡 Step 2: Computing technical indicators (SMA, EMA, MACD, RSI, Bollinger)...")
        logger.info("📡 Step 3: Fetching funding rate, orderbook, and open interest...")
        logger.info("🤖 Step 4: Running Market Analyst agent...")
        logger.info("🤖 Step 5: Running Sentiment, News, and On-chain analysts...")
        logger.info("🤖 Step 6: Running Bull & Bear researchers debate...")
        logger.info("🤖 Step 7: Running Research Manager to synthesize...")
        logger.info("🤖 Step 8: Running Trader agent for recommendation...")
        logger.info("🤖 Step 9: Running Risk Management debate...")
        logger.info("🤖 Step 10: Running Portfolio Manager for final decision...")
        
        try:
            final_state, decision_text, execution_result = graph.run(symbol, timeframe=timeframe)

            # Print decision summary to console
            print(f"\n{'='*60}")
            print(f"  SYMBOL : {symbol}")
            print(f"  TIME   : {now}")
            print(f"{'='*60}")
            print(decision_text)

            if execution_result is not None:
                if execution_result.success:
                    print(f"\n✅ Orders placed: {[o.get('id') for o in execution_result.orders]}")
                else:
                    print(f"\n❌ Order placement FAILED: {execution_result.error}")
            print()

            # Send Feishu notification with detailed reports
            send_feishu_notification(symbol, decision_text, execution_result, final_state)

            # Record to persistent trade history
            if execution_result is not None:
                if execution_result.success:
                    for order in execution_result.orders:
                        action = f"OPEN_{execution_result.signal.direction}" if execution_result.signal.direction in ("LONG", "LONG-LITE", "SHORT", "SHORT-LITE") else "CLOSE"
                        record_trade_history(action, symbol, {
                            "order_id": order.get("id"),
                            "type": order.get("type"),
                            "side": order.get("side"),
                            "amount": order.get("amount"),
                            "price": order.get("price"),
                            "signal_direction": execution_result.signal.direction,
                            "leverage": execution_result.signal.leverage,
                        })
                else:
                    record_trade_history(execution_result.signal.direction if execution_result.signal else "UNKNOWN", symbol, {
                        "status": "FAILED",
                        "error": execution_result.error,
                    })
            else:
                record_trade_history("ANALYSIS", symbol, {"decision": decision_text[:200]})

        except Exception as e:
            logger.exception("Unhandled error analysing %s", symbol)
            # Send error notification to Feishu
            error_msg = f"❌ 分析失败\n\n交易对: {symbol}\n时间: {now}\n错误: {str(e)[:500]}"
            send_feishu_error_notification(symbol, error_msg)


def build_graph(auto_execute: bool, symbols: list, timeframe: str = "4h"):
    """Instantiate CryptoTradingAgentsGraph with the current environment."""
    from tradingagents.graph.crypto_trading_graph import CryptoTradingAgentsGraph
    from tradingagents.default_config import CRYPTO_CONFIG

    # Allow runtime overrides via environment variables
    config_override = {
        "crypto_symbols": symbols,
        "sandbox_mode": os.getenv("BITGET_SANDBOX", "true").lower() != "false",
        "account_type": os.getenv("BITGET_ACCOUNT_TYPE", "classic"),
        "capital_usdt": float(os.getenv("CAPITAL_USDT", CRYPTO_CONFIG["capital_usdt"])),
        "timeframe": os.getenv("TIMEFRAME", timeframe),
    }

    return CryptoTradingAgentsGraph(
        config=config_override,
        debug=os.getenv("DEBUG", "false").lower() == "true",
        auto_execute=auto_execute,
    )


def main():
    parser = argparse.ArgumentParser(description="Crypto perpetual futures trading bot")
    parser.add_argument(
        "--once", action="store_true",
        help="Run analysis once immediately then exit (no scheduler)"
    )
    parser.add_argument(
        "--symbol", type=str, default=None,
        help="Analyse a single symbol only, e.g. BTC/USDT:USDT"
    )
    parser.add_argument(
        "--no-execute", action="store_true",
        help="Analysis only — do not place real orders"
    )
    parser.add_argument(
        "--interval-hours", type=float, default=4.0,
        help="How often to run analysis (hours). Default: 4"
    )
    args = parser.parse_args()

    from tradingagents.default_config import CRYPTO_CONFIG

    symbols = [args.symbol] if args.symbol else CRYPTO_CONFIG["crypto_symbols"]
    auto_execute = not args.no_execute
    timeframe = os.getenv("TIMEFRAME", CRYPTO_CONFIG.get("timeframe", "4h"))

    logger.info("Initialising CryptoTradingAgentsGraph (timeframe=%s) …", timeframe)
    graph = build_graph(auto_execute=auto_execute, symbols=symbols, timeframe=timeframe)
    logger.info("Graph ready.")

    if auto_execute:
        balance = graph.fetch_account_balance()
        logger.info(
            "Bitget account balance (USDT): total=%.2f free=%.2f",
            balance.get("total", 0), balance.get("free", 0),
        )

    # Run initial analysis immediately so users can verify AI is working
    logger.info("Running initial analysis cycle...")
    run_analysis(graph, symbols, auto_execute, timeframe=timeframe)
    logger.info("Initial analysis complete.\n")

    if args.once:
        # Single run — already completed above
        return

    # ---- Scheduled mode --------------------------------------------------
    try:
        from apscheduler.schedulers.blocking import BlockingScheduler
        from apscheduler.triggers.interval import IntervalTrigger
    except ImportError:
        logger.error(
            "APScheduler not installed. Install it with: pip install apscheduler\n"
            "Or run once with --once flag."
        )
        sys.exit(1)

    scheduler = BlockingScheduler(timezone="UTC")
    interval_hours = args.interval_hours

    scheduler.add_job(
        func=run_analysis,
        trigger=IntervalTrigger(hours=interval_hours),
        args=[graph, symbols, auto_execute, timeframe],
        id="crypto_analysis",
        name=f"Crypto analysis every {interval_hours}h (timeframe={timeframe})",
        replace_existing=True,
    )

    logger.info(
        "Scheduler started — analysis every %.1f hours for %s",
        interval_hours, symbols,
    )
    logger.info("Press Ctrl+C to stop.\n")

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped by user.")


if __name__ == "__main__":
    main()
