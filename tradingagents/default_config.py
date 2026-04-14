import os

DEFAULT_CONFIG = {
    "project_dir": os.path.abspath(os.path.join(os.path.dirname(__file__), ".")),
    "results_dir": os.getenv("TRADINGAGENTS_RESULTS_DIR", "./results"),
    "data_cache_dir": os.path.join(
        os.path.abspath(os.path.join(os.path.dirname(__file__), ".")),
        "dataflows/data_cache",
    ),
    # LLM settings
    "llm_provider": "openai",
    "deep_think_llm": "gpt-5.4",
    "quick_think_llm": "gpt-5.4-mini",
    "backend_url": "https://api.openai.com/v1",
    # Provider-specific thinking configuration
    "google_thinking_level": None,      # "high", "minimal", etc.
    "openai_reasoning_effort": None,    # "medium", "high", "low"
    "anthropic_effort": None,           # "high", "medium", "low"
    # Output language for analyst reports and final decision
    # Internal agent debate stays in English for reasoning quality
    "output_language": "English",
    # Debate and discussion settings
    "max_debate_rounds": 1,
    "max_risk_discuss_rounds": 1,
    "max_recur_limit": 100,
    # Data vendor configuration
    # Category-level configuration (default for all tools in category)
    "data_vendors": {
        "core_stock_apis": "yfinance",       # Options: alpha_vantage, yfinance
        "technical_indicators": "yfinance",  # Options: alpha_vantage, yfinance
        "fundamental_data": "yfinance",      # Options: alpha_vantage, yfinance
        "news_data": "yfinance",             # Options: alpha_vantage, yfinance
        "crypto_data": "bitget",             # Crypto perpetual futures data
    },
    # Tool-level configuration (takes precedence over category-level)
    "tool_vendors": {
        # Example: "get_stock_data": "alpha_vantage",  # Override category default
    },
}

# ---------------------------------------------------------------------------
# Crypto-specific configuration (used by CryptoTradingAgentsGraph)
# ---------------------------------------------------------------------------

CRYPTO_CONFIG = {
    # Symbols to trade (Bitget perpetual futures format)
    "crypto_symbols": ["BTC/USDT:USDT", "ETH/USDT:USDT"],

    # Bitget API credentials — set via environment variables
    "bitget_api_key": os.getenv("BITGET_API_KEY", ""),
    "bitget_secret": os.getenv("BITGET_SECRET", ""),
    "bitget_passphrase": os.getenv("BITGET_PASSPHRASE", ""),

    # Exchange settings
    "sandbox_mode": True,          # Set False for live trading
    "account_type": "classic",     # "classic" | "uma" (unified)
    "margin_mode": "isolated",     # "isolated" | "cross"
    "default_leverage": 5,         # Fallback if parser fails

    # Data settings — 4小时线和日线专用
    "timeframe": os.getenv("TIMEFRAME", "4h"),  # OHLCV candle timeframe (4h or 1d)
    "candle_limit": 200,           # Number of candles to fetch

    # Capital allocation
    "capital_usdt": 1000.0,        # Total account capital for position sizing

    # Scheduling (APScheduler cron-style)
    "schedule_hour": "0",          # Run daily at midnight UTC
    "schedule_minute": "5",

    # LLM configuration - 仅使用通义千问(Qwen)作为唯一LLM提供商
    # 深度思考模型: 用于研究经理和投资组合经理
    "deep_think_llm_provider": "qwen",
    "deep_think_llm": "qwen-max",

    # 快速思考模型: 用于分析师、交易员、辩论者
    "quick_think_llm_provider": "qwen",
    "quick_think_llm": "qwen-plus",

    # DashScope API Key (通义千问唯一接口)
    "dashscope_api_key": os.getenv("DASHSCOPE_API_KEY", ""),

    # Debate rounds
    "max_debate_rounds": 1,
    "max_risk_discuss_rounds": 1,

    # Output language
    "output_language": "English",

    # CryptoPanic API (optional — public API works without key but has rate limits)
    "cryptopanic_api_key": os.getenv("CRYPTOPANIC_API_KEY", ""),
}
