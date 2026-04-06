#!/usr/bin/env python3
"""
Crypto Trading Bot Web UI Server

FastAPI backend that serves:
- REST API for config management, bot lifecycle, account info
- SSE log streaming
- Static frontend (single-page app)

Usage:
    python server.py                  # Start on localhost:8000
    python server.py --host 0.0.0.0   # Listen on all interfaces
    python server.py --port 9000      # Custom port
"""

import argparse
import asyncio
import json
import logging
import os
import signal
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import ccxt
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_DIR = Path(__file__).parent.resolve()
CONFIG_DIR = Path.home() / ".tradingbot"
CONFIG_FILE = CONFIG_DIR / "config.json"
LOG_FILE = PROJECT_DIR / "crypto_trading.log"
HISTORY_FILE = CONFIG_DIR / "trade_history.json"

# Ensure config directory exists
CONFIG_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger("server")
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("uvicorn").setLevel(logging.INFO)

# ---------------------------------------------------------------------------
# Default configuration
# ---------------------------------------------------------------------------
DEFAULT_CONFIG = {
    "bitget_api_key": "",
    "bitget_secret": "",
    "bitget_passphrase": "",
    "sandbox_mode": True,
    "account_type": "classic",       # "classic" | "uma" (unified)
    "anthropic_api_key": "",
    "openai_api_key": "",
    "dashscope_api_key": "",
    "google_api_key": "",
    "deep_think_llm_provider": "anthropic",
    "deep_think_llm": "claude-sonnet-4-5",
    "quick_think_llm_provider": "anthropic",
    "quick_think_llm": "claude-haiku-4-5",
    "capital_usdt": 1000,
    "crypto_symbols": ["BTC/USDT:USDT", "ETH/USDT:USDT"],
    "interval_hours": 4,
    "auto_execute": True,
    "output_language": "Chinese",
    "margin_mode": "isolated",
    "default_leverage": 5,
    "feishu_webhook_url": "",
}

# ---------------------------------------------------------------------------
# Config persistence
# ---------------------------------------------------------------------------


def load_config() -> dict:
    """Load config from disk, merging with defaults."""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
            return {**DEFAULT_CONFIG, **saved}
        except (json.JSONDecodeError, IOError):
            logger.warning("Failed to load config, using defaults")
    return {**DEFAULT_CONFIG}


def save_config(cfg: dict) -> None:
    """Save config to disk."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)
    logger.info("Config saved to %s", CONFIG_FILE)


def mask_secret(secret: str, visible: int = 6) -> str:
    """Mask a secret string, showing only first N characters."""
    if not secret or len(secret) <= visible:
        return "***"
    return secret[:visible] + "..." + "*" * (len(secret) - visible)


def masked_config(cfg: dict) -> dict:
    """Return config with secrets masked."""
    m = {**cfg}
    for key in (
        "bitget_api_key",
        "bitget_secret",
        "bitget_passphrase",
        "anthropic_api_key",
        "openai_api_key",
        "dashscope_api_key",
        "google_api_key",
    ):
        if key in m and m[key]:
            m[key] = mask_secret(m[key])
    return m


# ---------------------------------------------------------------------------
# Bot process management
# ---------------------------------------------------------------------------


class BotProcess:
    """Manage the crypto_main.py subprocess lifecycle."""

    def __init__(self):
        self.process: Optional[asyncio.subprocess.Process] = None
        self.start_time: Optional[float] = None
        self.status = "stopped"  # stopped | starting | running | stopping | error
        self.error_message: Optional[str] = None
        self._monitor_task: Optional[asyncio.Task] = None

    @property
    def is_running(self) -> bool:
        return self.process is not None and self.process.returncode is None

    async def start(self, config: dict) -> dict:
        """Start the trading bot subprocess."""
        if self.is_running:
            return {"status": "running", "message": "Bot is already running"}

        self.status = "starting"
        self.error_message = None

        # Build environment from config
        env = os.environ.copy()
        env["BITGET_API_KEY"] = config.get("bitget_api_key", "")
        env["BITGET_SECRET"] = config.get("bitget_secret", "")
        env["BITGET_PASSPHRASE"] = config.get("bitget_passphrase", "")
        env["BITGET_SANDBOX"] = "true" if config.get("sandbox_mode", True) else "false"
        env["BITGET_ACCOUNT_TYPE"] = config.get("account_type", "classic")
        env["ANTHROPIC_API_KEY"] = config.get("anthropic_api_key", "")
        env["OPENAI_API_KEY"] = config.get("openai_api_key", "")
        env["DASHSCOPE_API_KEY"] = config.get("dashscope_api_key", "")
        env["CAPITAL_USDT"] = str(config.get("capital_usdt", 1000))
        env["FEISHU_WEBHOOK_URL"] = config.get("feishu_webhook_url", "")
        env["DEBUG"] = "false"

        symbols = ",".join(config.get("crypto_symbols", ["BTC/USDT:USDT"]))
        interval = config.get("interval_hours", 4)

        cmd = [
            sys.executable,
            str(PROJECT_DIR / "crypto_main.py"),
            "--symbol", symbols,
            "--interval-hours", str(interval),
        ]

        if not config.get("auto_execute", True):
            cmd.append("--no-execute")

        try:
            self.process = await asyncio.create_subprocess_exec(
                *cmd,
                env=env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(PROJECT_DIR),
            )
            self.start_time = time.time()
            self.status = "running"
            logger.info(
                "Bot started (PID=%d, sandbox=%s, symbols=%s)",
                self.process.pid,
                config.get("sandbox_mode", True),
                symbols,
            )

            # Start monitoring the process
            self._monitor_task = asyncio.create_task(self._monitor())

            return {
                "status": "running",
                "pid": self.process.pid,
                "message": "Bot started successfully",
            }

        except Exception as e:
            self.status = "error"
            self.error_message = str(e)
            logger.exception("Failed to start bot")
            raise HTTPException(status_code=500, detail=f"Failed to start bot: {e}")

    async def stop(self) -> dict:
        """Stop the trading bot gracefully."""
        if not self.is_running:
            self.status = "stopped"
            return {"status": "stopped", "message": "Bot is not running"}

        self.status = "stopping"
        try:
            # Send SIGTERM for graceful shutdown
            self.process.terminate()
            try:
                await asyncio.wait_for(self.process.wait(), timeout=10.0)
            except asyncio.TimeoutError:
                # Force kill if not responding
                self.process.kill()
                await self.process.wait()
        except ProcessLookupError:
            pass  # Process already exited
        except Exception as e:
            logger.warning("Error stopping bot: %s", e)

        self.status = "stopped"
        self.process = None
        self.start_time = None
        logger.info("Bot stopped")
        return {"status": "stopped", "message": "Bot stopped successfully"}

    async def _monitor(self):
        """Monitor the subprocess and update status if it exits."""
        if self.process:
            await self.process.wait()
            if self.status == "running":
                self.status = "error"
                self.error_message = f"Process exited with code {self.process.returncode}"
                logger.warning("Bot process exited unexpectedly (code=%d)", self.process.returncode)

    def get_status(self) -> dict:
        """Get current bot status."""
        result = {
            "status": self.status,
            "pid": self.process.pid if self.process else None,
            "uptime_seconds": 0,
        }
        if self.start_time and self.status == "running":
            result["uptime_seconds"] = int(time.time() - self.start_time)
        if self.error_message:
            result["error"] = self.error_message
        return result


bot = BotProcess()

# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(title="Crypto Trading Bot", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class ConfigRequest(BaseModel):
    bitget_api_key: str = ""
    bitget_secret: str = ""
    bitget_passphrase: str = ""
    sandbox_mode: bool = True
    account_type: str = "classic"
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    dashscope_api_key: str = ""
    google_api_key: str = ""
    deep_think_llm_provider: str = "anthropic"
    deep_think_llm: str = "claude-sonnet-4-5"
    quick_think_llm_provider: str = "anthropic"
    quick_think_llm: str = "claude-haiku-4-5"
    capital_usdt: float = 1000
    crypto_symbols: list = ["BTC/USDT:USDT", "ETH/USDT:USDT"]
    interval_hours: float = 4
    auto_execute: bool = True
    output_language: str = "Chinese"
    margin_mode: str = "isolated"
    default_leverage: int = 5
    feishu_webhook_url: str = ""


# ---------------------------------------------------------------------------
# Config API
# ---------------------------------------------------------------------------


@app.get("/api/config")
async def get_config():
    """Get current configuration (secrets masked)."""
    cfg = load_config()
    return {"success": True, "config": masked_config(cfg)}


@app.get("/api/config/full")
async def get_full_config():
    """Get full configuration (including secrets). Use with caution."""
    cfg = load_config()
    return {"success": True, "config": cfg}


@app.post("/api/config")
async def save_config_endpoint(req: ConfigRequest):
    """Save configuration."""
    cfg = req.model_dump()
    save_config(cfg)
    return {"success": True, "message": "Configuration saved successfully"}


def _create_bitget_exchange(cfg: dict) -> ccxt.bitget:
    """Create a Bitget exchange instance with proper account type."""
    account_type = cfg.get("account_type", "classic")
    ccxt_options = {"defaultType": "swap"}
    if account_type == "uma":
        ccxt_options["uta"] = True
    exchange = ccxt.bitget({
        "apiKey": cfg.get("bitget_api_key", ""),
        "secret": cfg.get("bitget_secret", ""),
        "password": cfg.get("bitget_passphrase", ""),
        "options": ccxt_options,
    })
    if cfg.get("sandbox_mode", True):
        exchange.set_sandbox_mode(True)
    return exchange


def _fetch_bitget_balance(exchange, cfg: dict):
    """Fetch Bitget USDT balance from swap account."""
    balance = exchange.fetch_balance()
    usdt = balance.get("USDT", {})
    return {"total": usdt.get("total", 0), "free": usdt.get("free", 0), "used": usdt.get("used", 0)}


@app.post("/api/config/validate")
async def validate_config(req: ConfigRequest):
    """Validate API key connectivity."""
    results = {}

    # Validate Bitget keys
    if req.bitget_api_key and req.bitget_secret and req.bitget_passphrase:
        try:
            cfg_dict = {
                "bitget_api_key": req.bitget_api_key,
                "bitget_secret": req.bitget_secret,
                "bitget_passphrase": req.bitget_passphrase,
                "sandbox_mode": req.sandbox_mode,
                "account_type": req.account_type,
            }
            exchange = _create_bitget_exchange(cfg_dict)

            # Try fetching balance as connectivity test
            usdt = _fetch_bitget_balance(exchange, cfg_dict)
            results["bitget"] = {
                "ok": True,
                "message": "Connection successful",
                "balance_usdt": usdt["total"],
            }
        except ccxt.NotSupported as e:
            results["bitget"] = {"ok": False, "message": f"Account type not supported: {e}"}
        except ccxt.AuthenticationError as e:
            results["bitget"] = {"ok": False, "message": f"Authentication failed: {e}"}
        except ccxt.NetworkError as e:
            results["bitget"] = {"ok": False, "message": f"Network error: {e}"}
        except Exception as e:
            results["bitget"] = {"ok": False, "message": f"Error: {e}"}
    else:
        results["bitget"] = {"ok": False, "message": "API credentials not provided"}

    # Validate Anthropic key
    if req.anthropic_api_key:
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=req.anthropic_api_key)
            # Simple test: list models (lightweight call)
            client.models.list()
            results["anthropic"] = {"ok": True, "message": "Connection successful"}
        except Exception as e:
            results["anthropic"] = {"ok": False, "message": f"Error: {e}"}
    else:
        results["anthropic"] = {"ok": False, "message": "API key not provided"}

    # Validate OpenAI key
    if req.openai_api_key:
        try:
            import openai
            client = openai.OpenAI(api_key=req.openai_api_key)
            client.models.list()
            results["openai"] = {"ok": True, "message": "Connection successful"}
        except Exception as e:
            results["openai"] = {"ok": False, "message": f"Error: {e}"}
    else:
        results["openai"] = {"ok": False, "message": "API key not provided"}

    # Validate Qwen (DashScope) key
    if req.dashscope_api_key:
        try:
            from openai import OpenAI
            client = OpenAI(
                api_key=req.dashscope_api_key,
                base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            )
            client.models.list()
            results["qwen"] = {"ok": True, "message": "Connection successful"}
        except Exception as e:
            results["qwen"] = {"ok": False, "message": f"Error: {e}"}
    else:
        results["qwen"] = {"ok": False, "message": "API key not provided"}

    return {"success": True, "results": results}


# ---------------------------------------------------------------------------
# Bot lifecycle API
# ---------------------------------------------------------------------------


@app.post("/api/bot/start")
async def start_bot():
    """Start the trading bot."""
    cfg = load_config()
    return await bot.start(cfg)


@app.post("/api/bot/stop")
async def stop_bot():
    """Stop the trading bot."""
    return await bot.stop()


@app.get("/api/bot/status")
async def bot_status():
    """Get bot status."""
    return bot.get_status()


# ---------------------------------------------------------------------------
# Account API
# ---------------------------------------------------------------------------


@app.get("/api/account/balance")
async def get_balance():
    """Get account balance from Bitget."""
    cfg = load_config()
    try:
        exchange = _create_bitget_exchange(cfg)
        balance = _fetch_bitget_balance(exchange, cfg)
        return {
            "success": True,
            "total": balance["total"],
            "free": balance["free"],
            "used": balance["used"],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/account/positions")
async def get_positions():
    """Get open positions from Bitget."""
    cfg = load_config()
    try:
        exchange = _create_bitget_exchange(cfg)
        positions = exchange.fetch_positions()
        open_positions = []
        for p in positions:
            contracts = float(p.get("contracts", 0) or 0)
            if contracts != 0:
                open_positions.append({
                    "symbol": p.get("symbol", ""),
                    "side": p.get("side", ""),
                    "contracts": contracts,
                    "entry_price": p.get("entryPrice", 0),
                    "mark_price": p.get("markPrice", 0),
                    "unrealized_pnl": p.get("unrealizedPnl", 0),
                    "leverage": p.get("leverage", 0),
                    "liquidation_price": p.get("liquidationPrice", 0),
                })

        return {"success": True, "positions": open_positions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Trade History API
# ---------------------------------------------------------------------------


def load_trade_history() -> list:
    """Load trade history from disk."""
    if HISTORY_FILE.exists():
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            logger.warning("Failed to load trade history, using empty list")
    return []


def save_trade_history(history: list) -> None:
    """Save trade history to disk."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)


@app.get("/api/trades/history")
async def get_trade_history(limit: int = 50):
    """Get trade history (persisted across page refreshes)."""
    history = load_trade_history()
    return {"success": True, "trades": history[-limit:][::-1]}


class TradeRecord(BaseModel):
    timestamp: str = ""
    action: str = ""       # "OPEN_LONG" | "OPEN_SHORT" | "CLOSE" | "ANALYSIS"
    symbol: str = ""
    details: dict = {}


@app.post("/api/trades/record")
async def record_trade(req: TradeRecord):
    """Record a trade entry to persistent history."""
    history = load_trade_history()
    entry = {
        "timestamp": req.timestamp or datetime.now(timezone.utc).isoformat(),
        "action": req.action,
        "symbol": req.symbol,
        "details": req.details,
    }
    history.append(entry)
    # Keep last 500 entries
    if len(history) > 500:
        history = history[-500:]
    save_trade_history(history)
    return {"success": True, "message": "Trade recorded"}


# ---------------------------------------------------------------------------
# Logs API
# ---------------------------------------------------------------------------


@app.get("/api/logs/tail")
async def get_logs_tail(lines: int = 100):
    """Get last N lines of the trading log."""
    if not LOG_FILE.exists():
        return {"success": True, "logs": []}

    try:
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            all_lines = f.readlines()
            tail = all_lines[-lines:]
        return {"success": True, "logs": [l.rstrip() for l in tail]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/logs/stream")
async def stream_logs():
    """SSE stream of new log lines."""

    async def event_generator():
        if not LOG_FILE.exists():
            # Wait for log file to appear
            for _ in range(30):
                await asyncio.sleep(1)
                if LOG_FILE.exists():
                    break
            else:
                yield "data: " + json.dumps({"line": "Waiting for log file...", "type": "info"}) + "\n\n"
                return

        with open(LOG_FILE, "r", encoding="utf-8") as f:
            # Seek to end
            f.seek(0, 2)
            while True:
                line = f.readline()
                if line:
                    line = line.rstrip()
                    # Determine log level from line content
                    log_type = "info"
                    if "[ERROR]" in line or "[CRITICAL]" in line:
                        log_type = "error"
                    elif "[WARNING]" in line or "[WARN]" in line:
                        log_type = "warning"
                    yield "data: " + json.dumps({"line": line, "type": log_type}) + "\n\n"
                else:
                    await asyncio.sleep(0.5)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ---------------------------------------------------------------------------
# Feishu Webhook API
# ---------------------------------------------------------------------------


class FeishuTestRequest(BaseModel):
    webhook_url: str


@app.post("/api/feishu/test")
async def test_feishu_webhook(req: FeishuTestRequest):
    """Test Feishu webhook connectivity by sending a test message."""
    import requests as req_lib

    if not req.webhook_url:
        raise HTTPException(status_code=400, detail="Webhook URL is required")

    payload = {
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {"tag": "plain_text", "content": "飞书通知测试"},
                "template": "green",
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "tag": "plain_text",
                        "content": "这是一条测试消息，说明飞书 Webhook 连接正常！",
                    },
                },
            ],
        },
    }

    try:
        resp = req_lib.post(req.webhook_url, json=payload, timeout=10)
        if resp.status_code == 200:
            result = resp.json()
            if result.get("StatusCode") == 0 or result.get("code") == 0:
                return {"success": True, "message": "飞书 Webhook 连接成功"}
            return {"success": False, "message": f"飞书返回错误: {result}"}
        raise HTTPException(status_code=500, detail=f"飞书返回 HTTP {resp.status_code}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"飞书 Webhook 测试失败: {e}")


# ---------------------------------------------------------------------------
# Frontend
# ---------------------------------------------------------------------------


@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    """Serve the single-page web UI."""
    frontend = PROJECT_DIR / "templates" / "index.html"
    if not frontend.exists():
        return HTMLResponse(
            "<h1>Frontend not found</h1><p>Run <code>npm run build</code> or check templates/index.html</p>"
        )
    return FileResponse(frontend)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main():
    import uvicorn

    parser = argparse.ArgumentParser(description="Crypto Trading Bot Web UI")
    parser.add_argument("--host", default="0.0.0.0", help="Host to listen on")
    parser.add_argument("--port", type=int, default=8000, help="Port to listen on")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload (dev)")
    args = parser.parse_args()

    logger.info("Starting Crypto Trading Bot Web UI on %s:%d", args.host, args.port)
    logger.info("Config file: %s", CONFIG_FILE)

    uvicorn.run(
        "server:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="info",
    )


if __name__ == "__main__":
    main()
