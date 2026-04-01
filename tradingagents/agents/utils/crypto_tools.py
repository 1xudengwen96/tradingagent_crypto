# tradingagents/agents/utils/crypto_tools.py
"""
加密货币专用 LangChain 工具集。
这些工具通过 route_to_vendor 路由到 Bitget 数据层，并绑定到各智能体节点。
"""

from langchain_core.tools import tool
from typing import Annotated

from tradingagents.dataflows.interface import route_to_vendor


@tool
def get_crypto_ohlcv(
    symbol: Annotated[str, "Trading pair in Bitget format, e.g. 'BTC/USDT:USDT'"],
    timeframe: Annotated[str, "Candle timeframe: '1m','5m','15m','1h','4h','1d'"],
    limit: Annotated[int, "Number of candles to fetch (max 1000)"] = 200,
) -> str:
    """
    Retrieve OHLCV (Open/High/Low/Close/Volume) candlestick data for a crypto perpetual contract.
    Use this to analyze price history, trend direction, and volatility.
    Always call this first before computing technical indicators.
    Args:
        symbol: e.g. 'BTC/USDT:USDT' or 'ETH/USDT:USDT'
        timeframe: candle interval
        limit: number of candles
    Returns:
        Formatted table of OHLCV data with summary statistics.
    """
    return route_to_vendor("get_crypto_ohlcv", symbol, timeframe, limit)


@tool
def get_crypto_indicators(
    symbol: Annotated[str, "Trading pair in Bitget format, e.g. 'BTC/USDT:USDT'"],
    timeframe: Annotated[str, "Candle timeframe: '1m','5m','15m','1h','4h','1d'"],
    limit: Annotated[int, "Number of candles used for indicator calculation"] = 200,
) -> str:
    """
    Calculate technical indicators for a crypto perpetual contract.
    Includes: SMA-20/50, EMA-10/20, MACD, RSI-14, Bollinger Bands, ATR-14, VWMA-20.
    Use this AFTER fetching OHLCV data to get actionable signals.
    Args:
        symbol: e.g. 'BTC/USDT:USDT' or 'ETH/USDT:USDT'
        timeframe: candle interval
        limit: number of candles for calculation
    Returns:
        Formatted indicator values with trend direction and signal interpretation.
    """
    return route_to_vendor("get_crypto_indicators", symbol, timeframe, limit)


@tool
def get_funding_rate(
    symbol: Annotated[str, "Trading pair in Bitget format, e.g. 'BTC/USDT:USDT'"],
) -> str:
    """
    Fetch the current and historical funding rate for a perpetual futures contract on Bitget.
    Funding rates indicate market sentiment: negative rates mean shorts pay longs (bullish bias),
    positive rates mean longs pay shorts (bearish bias / overleveraged longs).
    Critical for evaluating cost of holding positions and market positioning.
    Args:
        symbol: e.g. 'BTC/USDT:USDT' or 'ETH/USDT:USDT'
    Returns:
        Current funding rate, annualized cost, next settlement time, and historical analysis.
    """
    return route_to_vendor("get_funding_rate", symbol)


@tool
def get_orderbook(
    symbol: Annotated[str, "Trading pair in Bitget format, e.g. 'BTC/USDT:USDT'"],
    depth: Annotated[int, "Number of order book levels to fetch (default 20)"] = 20,
) -> str:
    """
    Fetch the order book (market depth) for a crypto perpetual contract.
    Shows buy/sell pressure from limit orders stacked at various price levels.
    Useful for identifying support/resistance zones and short-term directional bias.
    Args:
        symbol: e.g. 'BTC/USDT:USDT'
        depth: number of bid/ask levels
    Returns:
        Order book snapshot with bid/ask distribution and pressure analysis.
    """
    return route_to_vendor("get_orderbook", symbol, depth)


@tool
def get_open_interest(
    symbol: Annotated[str, "Trading pair in Bitget format, e.g. 'BTC/USDT:USDT'"],
) -> str:
    """
    Fetch the open interest (total outstanding contracts) for a perpetual futures pair.
    Rising OI with rising price = strong trend. Falling OI with rising price = short covering.
    A critical on-chain/market-structure metric for crypto contract trading.
    Args:
        symbol: e.g. 'BTC/USDT:USDT' or 'ETH/USDT:USDT'
    Returns:
        Current open interest in contracts and USDT, with trend and interpretation.
    """
    return route_to_vendor("get_open_interest", symbol)


@tool
def get_crypto_news(
    coin: Annotated[str, "Coin code, e.g. 'BTC', 'ETH'"],
    limit: Annotated[int, "Number of news articles to fetch (default 20)"] = 20,
) -> str:
    """
    Fetch the latest news articles for a specific cryptocurrency from CryptoPanic.
    Includes sentiment votes (bullish/bearish) from the crypto community.
    Use this to gauge social media sentiment and market-moving news events.
    Args:
        coin: e.g. 'BTC' or 'ETH'
        limit: number of articles
    Returns:
        News headlines with publication date, source, and community sentiment.
    """
    return route_to_vendor("get_crypto_news", coin, limit)


@tool
def get_crypto_global_news(
    limit: Annotated[int, "Number of global crypto news articles (default 20)"] = 20,
) -> str:
    """
    Fetch global cryptocurrency market news covering macro events, regulatory updates,
    DeFi/NFT trends, and broader market sentiment. Use this to understand macro tailwinds
    and headwinds that affect all crypto assets.
    Args:
        limit: number of articles
    Returns:
        Global crypto market news headlines with source and related currencies.
    """
    return route_to_vendor("get_crypto_global_news", limit)


@tool
def get_crypto_ticker(
    symbol: Annotated[str, "Trading pair in Bitget format, e.g. 'BTC/USDT:USDT'"],
) -> str:
    """
    Fetch the latest market ticker snapshot for a crypto perpetual contract.
    Provides current price, 24h price change percentage, 24h high/low, and trading volume.
    Args:
        symbol: e.g. 'BTC/USDT:USDT' or 'ETH/USDT:USDT'
    Returns:
        Latest price, 24h change %, high/low, and volume data.
    """
    return route_to_vendor("get_crypto_ticker", symbol)
