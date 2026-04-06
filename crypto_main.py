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


def send_feishu_notification(symbol: str, decision_text: str, execution_result) -> None:
    """Send AI analysis result to Feishu webhook as an interactive card."""
    webhook_url = os.getenv("FEISHU_WEBHOOK_URL", "")
    if not webhook_url:
        return

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
                        "tag": "plain_text",
                        "content": decision_text[:1500],  # Feishu has message size limits
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
                                "content": f"**时间**\n{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
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


def run_analysis(graph, symbols: list, auto_execute: bool):
    """Run one full analysis cycle for all configured symbols."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    logger.info("=" * 60)
    logger.info("Analysis cycle started at %s", now)
    logger.info("Symbols: %s | auto_execute=%s", symbols, auto_execute)
    logger.info("=" * 60)

    for symbol in symbols:
        logger.info("▶ Analysing %s ...", symbol)
        try:
            final_state, decision_text, execution_result = graph.run(symbol)

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

            # Send Feishu notification
            send_feishu_notification(symbol, decision_text, execution_result)

        except Exception:
            logger.exception("Unhandled error analysing %s", symbol)


def build_graph(auto_execute: bool, symbols: list):
    """Instantiate CryptoTradingAgentsGraph with the current environment."""
    from tradingagents.graph.crypto_trading_graph import CryptoTradingAgentsGraph
    from tradingagents.default_config import CRYPTO_CONFIG

    # Allow runtime overrides via environment variables
    config_override = {
        "crypto_symbols": symbols,
        "sandbox_mode": os.getenv("BITGET_SANDBOX", "true").lower() != "false",
        "capital_usdt": float(os.getenv("CAPITAL_USDT", CRYPTO_CONFIG["capital_usdt"])),
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

    logger.info("Initialising CryptoTradingAgentsGraph …")
    graph = build_graph(auto_execute=auto_execute, symbols=symbols)
    logger.info("Graph ready.")

    if auto_execute:
        balance = graph.fetch_account_balance()
        logger.info(
            "Bitget account balance (USDT): total=%.2f free=%.2f",
            balance.get("total", 0), balance.get("free", 0),
        )

    if args.once:
        # Single run
        run_analysis(graph, symbols, auto_execute)
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
        args=[graph, symbols, auto_execute],
        id="crypto_analysis",
        name=f"Crypto analysis every {interval_hours}h",
        replace_existing=True,
        # Run immediately on startup, then on schedule
        next_run_time=datetime.now(timezone.utc),
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
