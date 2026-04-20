import os

DEFAULT_CONFIG = {
    "project_dir": os.path.abspath(os.path.join(os.path.dirname(__file__), ".")),
    "results_dir": os.getenv("TRADINGAGENTS_RESULTS_DIR", "./results"),
    "data_cache_dir": os.path.join(
        os.path.abspath(os.path.join(os.path.dirname(__file__), ".")),
        "dataflows/data_cache",
    ),
    # LLM settings - 仅使用通义千问 (Qwen) 作为唯一 LLM 提供商
    "llm_provider": "qwen",
    "deep_think_llm": "qwen3-max",        # 用于研究经理和投资组合经理（最新旗舰）
    "quick_think_llm": "qwen3.6-plus",      # 用于分析师（最新平衡模型）
    "backend_url": "https://dashscope.aliyun.com/api/v1",
    
    # Provider-specific thinking configuration
    "google_thinking_level": None,
    "openai_reasoning_effort": None,
    "anthropic_effort": None,
    
    # Output language for analyst reports and final decision
    "output_language": "Chinese",
    
    # Debate and discussion settings (精简后不再需要，保留以备未来重新启用)
    "max_debate_rounds": 0,              # 已移除辩论机制
    "max_risk_discuss_rounds": 0,        # 已移除风险辩论
    "max_recur_limit": 100,
    
    # Data vendor configuration - 加密货币仅使用 Binance
    "data_vendors": {
        "crypto_data": "binance",         # Crypto perpetual futures data (唯一数据源)
    },

    # Tool-level configuration (takes precedence over category-level)
    "tool_vendors": {
        # 所有 crypto 工具强制使用 binance
        "get_crypto_ohlcv": "binance",
        "get_crypto_indicators": "binance",
        "get_funding_rate": "binance",
        "get_orderbook": "binance",
        "get_open_interest": "binance",
        "get_crypto_news": "binance",
        "get_crypto_global_news": "binance",
        "get_crypto_ticker": "binance",
    },
}

# ---------------------------------------------------------------------------
# Crypto-specific configuration (4H/1D 中线交易专用配置)
# ---------------------------------------------------------------------------

CRYPTO_CONFIG = {
    # Symbols to trade (Binance perpetual futures format)
    # 聚焦主流币种：BTC/ETH/SOL/XRP/DOGE/BNB/XAU/XAG
    "crypto_symbols": ["BTC/USDT", "ETH/USDT"],

    # Binance API credentials — set via environment variables
    "binance_api_key": os.getenv("BINANCE_API_KEY", ""),
    "binance_secret": os.getenv("BINANCE_SECRET", ""),

    # Exchange settings
    "sandbox_mode": os.getenv("BINANCE_SANDBOX", "true").lower() == "true",  # Set False for live trading
    "shadow_mode": True,           # True = 影子账户（虚拟交易）, False = 实盘交易
    "margin_mode": "isolated",     # "isolated" | "cross"
    "default_leverage": 1,         # 不使用杠杆（通过仓位大小控制风险）
    "slippage": 0.0005,            # 滑点（0.05% = 万分之五）

    # Data settings — 4 小时线和日线专用 (核心周期)
    "timeframe": os.getenv("TIMEFRAME", "4h"),  # OHLCV candle timeframe (4h or 1d)
    "candle_limit": 200,           # Number of candles to fetch

    # Capital allocation
    "capital_usdt": 1000.0,        # Total account capital for position sizing

    # Scheduling (APScheduler cron-style)
    # 4H 周期：每 4 小时执行一次 (0, 4, 8, 12, 16, 20 点)
    # 1D 周期：每日 08:00 (UTC+8) 执行全局扫描
    "schedule_hour": "*/4",        # 4H 周期
    "schedule_minute": "5",

    # LLM configuration - 仅使用通义千问 (Qwen)
    "deep_think_llm_provider": "qwen",
    "deep_think_llm": "qwen3-max",

    "quick_think_llm_provider": "qwen",
    "quick_think_llm": "qwen3.6-plus",

    # DashScope API Key (通义千问唯一接口)
    "dashscope_api_key": os.getenv("DASHSCOPE_API_KEY", ""),

    # 视觉化分析配置（支持 Qwen-VL-Max）
    "enable_vision_analysis": False,  # 是否启用 K 线图表视觉分析
    "vision_llm": "qwen-vl-max",     # 视觉分析模型

    # Output language
    "output_language": "Chinese",

    # CryptoPanic API (optional — public API works without key but has rate limits)
    "cryptopanic_api_key": os.getenv("CRYPTOPANIC_API_KEY", ""),

    # 4H/1D 交易策略参数
    "risk_per_trade": 0.01,          # 单笔最大亏损（总资金的 1%）
    "atr_multiplier": 1.5,           # 止损 = 1.5 × ATR14
    "tp1_risk_reward": 2.0,          # 止盈 1 盈亏比
    "tp2_risk_reward": 3.5,          # 止盈 2 盈亏比
    "max_position_pct": 0.30,        # 单笔仓位上限（30%）
}
