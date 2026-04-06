# tradingagents/dataflows/bitget_vendor.py
"""
Bitget 数据层 —— 通过 CCXT 获取加密货币合约市场数据。
支持 Sandbox 沙盒模式，所有函数均返回格式化字符串（与原 yfinance 接口保持一致）。
"""

import ccxt
import pandas as pd
import requests
from datetime import datetime, timedelta, timezone
from typing import Optional
from .config import get_config


# ─────────────────────────────────────────────
# 日线对齐工具（硬性 UTC 00:00 收盘保证）
# ─────────────────────────────────────────────

def _get_last_closed_daily_utc_ts() -> int:
    """
    返回上一根已完整收盘的日线 K 线的 UTC 00:00 开盘时间戳（毫秒）。

    加密货币日线以 UTC 00:00 作为收盘时刻。
    若当前时间为 UTC 14:00，则最后一根已收盘的日线是昨天 UTC 00:00 开盘的 K 线。
    本函数确保永远不会把当天尚未走完的半截 K 线纳入计算。
    """
    now_utc = datetime.now(timezone.utc)
    # 截断到今天 UTC 00:00 —— 这是当前未收盘 K 线的开盘时间
    today_open = now_utc.replace(hour=0, minute=0, second=0, microsecond=0)
    # 上一根已收盘日线的开盘时间
    last_closed_open = today_open - timedelta(days=1)
    return int(last_closed_open.timestamp() * 1000)


def _filter_closed_daily_candles(df: pd.DataFrame) -> pd.DataFrame:
    """
    过滤掉当前未收盘的日线 K 线（即 datetime >= 今天 UTC 00:00 的 K 线）。

    Args:
        df: 包含 datetime 列（UTC时区感知）的 OHLCV DataFrame

    Returns:
        只含已完整收盘 K 线的 DataFrame
    """
    now_utc = datetime.now(timezone.utc)
    today_open = now_utc.replace(hour=0, minute=0, second=0, microsecond=0)
    # 过滤：只保留开盘时间 < 今天 UTC 00:00 的 K 线
    return df[df["datetime"] < today_open].copy()


# ─────────────────────────────────────────────
# 交易所实例（单例缓存）
# ─────────────────────────────────────────────
_exchange_cache: Optional[ccxt.bitget] = None


def get_bitget_exchange() -> ccxt.bitget:
    """获取（或创建）Bitget 交易所实例，支持沙盒模式。"""
    global _exchange_cache
    if _exchange_cache is not None:
        return _exchange_cache

    config = get_config()
    exchange = ccxt.bitget(
        {
            "apiKey": config.get("bitget_api_key", ""),
            "secret": config.get("bitget_secret", ""),
            "password": config.get("bitget_passphrase", ""),
            "options": {
                "defaultType": "swap",  # 永续合约
            },
            "enableRateLimit": True,
        }
    )

    if config.get("sandbox_mode", True):
        exchange.set_sandbox_mode(True)

    _exchange_cache = exchange
    return exchange


def reset_exchange_cache():
    """重置交易所缓存（测试或配置更新后使用）。"""
    global _exchange_cache
    _exchange_cache = None


# ─────────────────────────────────────────────
# K 线 / OHLCV
# ─────────────────────────────────────────────

def get_crypto_ohlcv(symbol: str, timeframe: str = "1h", limit: int = 200) -> str:
    """
    获取加密货币 OHLCV K 线数据。

    对于日线（1d）周期，会自动过滤掉当前未收盘的 K 线，
    确保所有计算基于 UTC 00:00 已完整收盘的历史数据，
    消除"假收盘"信号（Fake Signals）。

    Args:
        symbol: 交易对，如 'BTC/USDT:USDT'（Bitget 永续合约格式）
        timeframe: K 线周期，如 '1m','5m','15m','1h','4h','1d'
        limit: 返回 K 线数量（最多 1000）

    Returns:
        格式化的 CSV 字符串，包含 timestamp, open, high, low, close, volume
    """
    try:
        exchange = get_bitget_exchange()
        # 日线模式：多拉 1 根，以备过滤后仍有足够数量
        fetch_limit = limit + 1 if timeframe in ("1d", "3d") else limit
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=fetch_limit)

        if not ohlcv:
            return f"No OHLCV data available for {symbol}"

        df = pd.DataFrame(
            ohlcv,
            columns=["timestamp", "open", "high", "low", "close", "volume"],
        )
        df["datetime"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
        df = df[["datetime", "open", "high", "low", "close", "volume"]]
        df = df.sort_values("datetime").reset_index(drop=True)

        # ── 日线专属：强制过滤未收盘 K 线 ──────────────────────────────
        # 加密货币日线以 UTC 00:00 收盘。任何开盘时间 >= 今天 UTC 00:00
        # 的 K 线都是未走完的半截，必须剔除。
        if timeframe in ("1d", "3d"):
            before_count = len(df)
            df = _filter_closed_daily_candles(df)
            after_count = len(df)
            closed_note = (
                f"[UTC-Aligned] Showing {after_count} closed daily candles "
                f"(filtered {before_count - after_count} unclosed candle)\n"
            )
        else:
            closed_note = ""

        if df.empty:
            return f"No closed daily candles available for {symbol} (all candles are still open)"

        result = f"OHLCV Data for {symbol} ({timeframe}, last {len(df)} candles)\n"
        result += closed_note
        result += f"Latest closed price: {df['close'].iloc[-1]:.4f} USDT\n"
        result += f"24h High: {df['high'].tail(24).max():.4f} | 24h Low: {df['low'].tail(24).min():.4f}\n"
        result += f"Latest Volume: {df['volume'].iloc[-1]:.2f}\n\n"
        result += df.tail(50).to_string(index=False)
        return result

    except Exception as e:
        return f"Error fetching OHLCV for {symbol}: {str(e)}"


# ─────────────────────────────────────────────
# 技术指标
# ─────────────────────────────────────────────

def get_crypto_indicators(symbol: str, timeframe: str = "1h", limit: int = 200) -> str:
    """
    计算加密货币技术指标（SMA/EMA/MACD/RSI/Bollinger/ATR/VWMA）。

    对于日线（1d）周期，会自动过滤掉当前未收盘的 K 线，
    确保 RSI、MACD 等所有指标只基于已确定收盘价计算，
    避免产生假信号。

    Args:
        symbol: 交易对，如 'BTC/USDT:USDT'
        timeframe: K 线周期
        limit: 用于计算指标的 K 线数量

    Returns:
        格式化字符串，包含各技术指标的最新值及趋势分析
    """
    try:
        exchange = get_bitget_exchange()
        fetch_limit = limit + 1 if timeframe in ("1d", "3d") else limit
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=fetch_limit)

        if not ohlcv:
            return f"No data available for indicators calculation of {symbol}"

        df = pd.DataFrame(
            ohlcv,
            columns=["timestamp", "open", "high", "low", "close", "volume"],
        )
        df["datetime"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
        df = df.sort_values("datetime").reset_index(drop=True)

        # ── 日线专属：强制过滤未收盘 K 线 ──────────────────────────────
        # 技术指标（RSI/MACD 等）的最后一个值若基于半截 K 线会严重失真。
        if timeframe in ("1d", "3d"):
            df = _filter_closed_daily_candles(df)
            closed_note = f"[UTC-Aligned: indicators based on {len(df)} closed daily candles only]\n"
        else:
            closed_note = ""

        if df.empty:
            return f"No closed candles available for indicator calculation of {symbol}"

        close = df["close"]
        high = df["high"]
        low = df["low"]
        volume = df["volume"]

        # Moving averages
        df["sma_20"] = close.rolling(20).mean()
        df["sma_50"] = close.rolling(50).mean()
        df["ema_10"] = close.ewm(span=10, adjust=False).mean()
        df["ema_20"] = close.ewm(span=20, adjust=False).mean()

        # MACD
        ema_12 = close.ewm(span=12, adjust=False).mean()
        ema_26 = close.ewm(span=26, adjust=False).mean()
        df["macd"] = ema_12 - ema_26
        df["macd_signal"] = df["macd"].ewm(span=9, adjust=False).mean()
        df["macd_hist"] = df["macd"] - df["macd_signal"]

        # RSI (14)
        delta = close.diff()
        gain = delta.where(delta > 0, 0.0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0.0)).rolling(14).mean()
        rs = gain / loss.replace(0, float("nan"))
        df["rsi"] = 100 - 100 / (1 + rs)

        # Bollinger Bands (20, 2σ)
        df["boll_mid"] = close.rolling(20).mean()
        bb_std = close.rolling(20).std()
        df["boll_upper"] = df["boll_mid"] + 2 * bb_std
        df["boll_lower"] = df["boll_mid"] - 2 * bb_std

        # ATR (14)
        tr1 = high - low
        tr2 = (high - close.shift()).abs()
        tr3 = (low - close.shift()).abs()
        df["atr"] = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1).rolling(14).mean()

        # VWMA (20)
        df["vwma"] = (close * volume).rolling(20).sum() / volume.rolling(20).sum()

        last = df.iloc[-1]
        prev = df.iloc[-2]
        current_price = last["close"]

        def fmt(v):
            return f"{v:.4f}" if pd.notna(v) else "N/A"

        def trend(cur, pre):
            if pd.isna(cur) or pd.isna(pre):
                return ""
            return "↑" if cur > pre else "↓"

        result = f"=== Technical Indicators for {symbol} ({timeframe}) ===\n"
        result += closed_note
        result += f"Last Closed Price: {fmt(current_price)} USDT\n\n"

        result += "--- Moving Averages ---\n"
        result += f"SMA-20:  {fmt(last['sma_20'])}  {trend(last['sma_20'], prev['sma_20'])}\n"
        result += f"SMA-50:  {fmt(last['sma_50'])}  {trend(last['sma_50'], prev['sma_50'])}\n"
        result += f"EMA-10:  {fmt(last['ema_10'])}  {trend(last['ema_10'], prev['ema_10'])}\n"
        result += f"EMA-20:  {fmt(last['ema_20'])}  {trend(last['ema_20'], prev['ema_20'])}\n"
        result += f"Price vs SMA-20: {'ABOVE' if current_price > last['sma_20'] else 'BELOW'}\n"
        result += f"Price vs SMA-50: {'ABOVE' if current_price > last['sma_50'] else 'BELOW'}\n\n"

        result += "--- MACD ---\n"
        result += f"MACD:        {fmt(last['macd'])}\n"
        result += f"Signal:      {fmt(last['macd_signal'])}\n"
        result += f"Histogram:   {fmt(last['macd_hist'])} ({'Bullish' if last['macd_hist'] > 0 else 'Bearish'})\n\n"

        result += "--- RSI ---\n"
        rsi_val = last["rsi"]
        rsi_status = "Overbought (>70)" if rsi_val > 70 else ("Oversold (<30)" if rsi_val < 30 else "Neutral")
        result += f"RSI-14: {fmt(rsi_val)} — {rsi_status}\n\n"

        result += "--- Bollinger Bands ---\n"
        result += f"Upper: {fmt(last['boll_upper'])}\n"
        result += f"Mid:   {fmt(last['boll_mid'])}\n"
        result += f"Lower: {fmt(last['boll_lower'])}\n"
        bb_pct = (current_price - last["boll_lower"]) / (last["boll_upper"] - last["boll_lower"]) * 100 if (last["boll_upper"] - last["boll_lower"]) != 0 else 50
        result += f"BB %:  {bb_pct:.1f}% (0=lower band, 100=upper band)\n\n"

        result += "--- Volatility & Volume ---\n"
        result += f"ATR-14: {fmt(last['atr'])} ({fmt(last['atr'] / current_price * 100)}% of price)\n"
        result += f"VWMA-20: {fmt(last['vwma'])}\n"

        return result

    except Exception as e:
        return f"Error calculating indicators for {symbol}: {str(e)}"


# ─────────────────────────────────────────────
# 资金费率
# ─────────────────────────────────────────────

def get_funding_rate(symbol: str) -> str:
    """
    获取永续合约当前资金费率及历史资金费率。

    Args:
        symbol: 交易对，如 'BTC/USDT:USDT'

    Returns:
        格式化字符串，包含当前资金费率、结算周期及历史平均费率
    """
    try:
        exchange = get_bitget_exchange()

        # 当前资金费率
        funding_info = exchange.fetch_funding_rate(symbol)
        current_rate = funding_info.get("fundingRate", None)
        next_time = funding_info.get("fundingDatetime", None)

        # 历史资金费率（最近 30 条）
        history = []
        try:
            history_data = exchange.fetch_funding_rate_history(symbol, limit=30)
            history = [h.get("fundingRate", 0) for h in history_data if h.get("fundingRate") is not None]
        except Exception:
            pass

        result = f"=== Funding Rate for {symbol} ===\n"
        if current_rate is not None:
            rate_pct = current_rate * 100
            annualized = current_rate * 3 * 365 * 100  # 8h settlement × 3/day × 365
            sentiment = "Bullish (Longs pay Shorts)" if current_rate < 0 else "Bearish (Shorts pay Longs)"
            result += f"Current Rate:    {rate_pct:.6f}%\n"
            result += f"Annualized Est:  {annualized:.2f}%\n"
            result += f"Market Sentiment: {sentiment}\n"
        else:
            result += "Current Rate:    N/A\n"

        if next_time:
            result += f"Next Settlement: {next_time}\n"

        if history:
            avg_rate = sum(history) / len(history)
            max_rate = max(history)
            min_rate = min(history)
            result += f"\n--- Last {len(history)} Funding Periods ---\n"
            result += f"Average Rate: {avg_rate * 100:.6f}%\n"
            result += f"Max Rate:     {max_rate * 100:.6f}%\n"
            result += f"Min Rate:     {min_rate * 100:.6f}%\n"
            result += f"Positive (Bearish) Periods: {sum(1 for r in history if r > 0)}/{len(history)}\n"

        return result

    except Exception as e:
        return f"Error fetching funding rate for {symbol}: {str(e)}"


# ─────────────────────────────────────────────
# 订单簿（市场深度）
# ─────────────────────────────────────────────

def get_orderbook(symbol: str, depth: int = 20) -> str:
    """
    获取市场深度（订单簿）数据。

    Args:
        symbol: 交易对，如 'BTC/USDT:USDT'
        depth: 订单簿深度（档位数量）

    Returns:
        格式化字符串，包含买卖盘挂单分布及买卖压力分析
    """
    try:
        exchange = get_bitget_exchange()
        ob = exchange.fetch_order_book(symbol, limit=depth)

        bids = ob.get("bids", [])  # [[price, size], ...]
        asks = ob.get("asks", [])

        if not bids or not asks:
            return f"Order book empty for {symbol}"

        best_bid = bids[0][0]
        best_ask = asks[0][0]
        spread = best_ask - best_bid
        spread_pct = spread / best_bid * 100

        total_bid_vol = sum(b[1] for b in bids[:depth])
        total_ask_vol = sum(a[1] for a in asks[:depth])
        bid_ask_ratio = total_bid_vol / total_ask_vol if total_ask_vol > 0 else 0

        pressure = "Buying Pressure (More Bids)" if bid_ask_ratio > 1.1 else (
            "Selling Pressure (More Asks)" if bid_ask_ratio < 0.9 else "Balanced"
        )

        result = f"=== Order Book for {symbol} ===\n"
        result += f"Best Bid: {best_bid:.4f} | Best Ask: {best_ask:.4f}\n"
        result += f"Spread:   {spread:.4f} ({spread_pct:.4f}%)\n\n"

        result += f"--- Volume Distribution (Top {min(depth, 5)} levels) ---\n"
        result += "ASKS (Sell Orders):\n"
        for price, size in sorted(asks[:5], reverse=True):
            result += f"  {price:.4f}  x  {size:.4f}\n"
        result += "BIDS (Buy Orders):\n"
        for price, size in bids[:5]:
            result += f"  {price:.4f}  x  {size:.4f}\n"

        result += f"\n--- Pressure Analysis ---\n"
        result += f"Total Bid Volume ({depth} levels): {total_bid_vol:.4f}\n"
        result += f"Total Ask Volume ({depth} levels): {total_ask_vol:.4f}\n"
        result += f"Bid/Ask Ratio: {bid_ask_ratio:.3f} — {pressure}\n"

        return result

    except Exception as e:
        return f"Error fetching order book for {symbol}: {str(e)}"


# ─────────────────────────────────────────────
# 未平仓合约（Open Interest）
# ─────────────────────────────────────────────

def get_open_interest(symbol: str) -> str:
    """
    获取永续合约未平仓合约量。

    Args:
        symbol: 交易对，如 'BTC/USDT:USDT'

    Returns:
        格式化字符串，包含当前未平仓量及趋势解读
    """
    try:
        exchange = get_bitget_exchange()

        oi_data = exchange.fetch_open_interest(symbol)
        oi = oi_data.get("openInterest", None)
        oi_value = oi_data.get("openInterestValue", None)

        # 历史 OI（若支持）
        history = []
        try:
            hist = exchange.fetch_open_interest_history(symbol, limit=24)
            history = [(h.get("timestamp"), h.get("openInterest")) for h in hist]
        except Exception:
            pass

        result = f"=== Open Interest for {symbol} ===\n"
        if oi is not None:
            result += f"Open Interest (Contracts): {oi:,.2f}\n"
        if oi_value is not None:
            result += f"Open Interest (USDT):      {oi_value:,.2f}\n"

        if history:
            oi_values = [h[1] for h in history if h[1] is not None]
            if oi_values:
                trend = "Increasing" if oi_values[-1] > oi_values[0] else "Decreasing"
                change_pct = (oi_values[-1] - oi_values[0]) / oi_values[0] * 100 if oi_values[0] else 0
                result += f"\n--- OI Trend (Last {len(oi_values)} periods) ---\n"
                result += f"Trend:    {trend}\n"
                result += f"Change:   {change_pct:+.2f}%\n"
                result += f"High OI:  {max(oi_values):,.2f}\n"
                result += f"Low OI:   {min(oi_values):,.2f}\n"
                result += "\nInterpretation:\n"
                if trend == "Increasing":
                    result += "  Rising OI with price UP → Strong bullish trend confirmation\n"
                    result += "  Rising OI with price DOWN → Strong bearish trend\n"
                else:
                    result += "  Falling OI with price UP → Short covering (potential reversal risk)\n"
                    result += "  Falling OI with price DOWN → Long liquidations\n"

        return result

    except Exception as e:
        return f"Error fetching open interest for {symbol}: {str(e)}"


# ─────────────────────────────────────────────
# 加密货币行情概览（ticker）
# ─────────────────────────────────────────────

def get_crypto_ticker(symbol: str) -> str:
    """
    获取币种最新行情快照。

    Args:
        symbol: 交易对，如 'BTC/USDT:USDT'

    Returns:
        格式化字符串，包含最新价格、24h 涨跌幅、成交量等
    """
    try:
        exchange = get_bitget_exchange()
        ticker = exchange.fetch_ticker(symbol)

        last = ticker.get("last", None)
        change_pct = ticker.get("percentage", None)
        high_24h = ticker.get("high", None)
        low_24h = ticker.get("low", None)
        vol_24h = ticker.get("baseVolume", None)
        quote_vol = ticker.get("quoteVolume", None)

        result = f"=== Market Ticker for {symbol} ===\n"
        result += f"Last Price:    {last:.4f} USDT\n" if last else "Last Price: N/A\n"
        result += f"24h Change:    {change_pct:+.2f}%\n" if change_pct is not None else ""
        result += f"24h High:      {high_24h:.4f}\n" if high_24h else ""
        result += f"24h Low:       {low_24h:.4f}\n" if low_24h else ""
        result += f"24h Volume:    {vol_24h:,.2f} (base)\n" if vol_24h else ""
        result += f"24h Turnover:  {quote_vol:,.2f} USDT\n" if quote_vol else ""

        return result

    except Exception as e:
        return f"Error fetching ticker for {symbol}: {str(e)}"


# ─────────────────────────────────────────────
# 加密货币新闻（通过 CryptoPanic 免费 API）
# ─────────────────────────────────────────────

def get_crypto_news(coin: str, limit: int = 20) -> str:
    """
    获取加密货币相关新闻（使用 CryptoPanic 公共 API）。

    Args:
        coin: 币种代码，如 'BTC', 'ETH'
        limit: 返回新闻条数

    Returns:
        格式化字符串，包含最新新闻标题、时间及情绪标签
    """
    try:
        # 使用 CryptoPanic 公共 API（无需 API key 即可访问部分数据）
        url = f"https://cryptopanic.com/api/v1/posts/?auth_token=free&currencies={coin}&public=true&limit={limit}"
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        posts = data.get("results", [])
        if not posts:
            return f"No crypto news found for {coin}"

        result = f"=== Crypto News for {coin} (Latest {len(posts)} articles) ===\n\n"
        for i, post in enumerate(posts, 1):
            title = post.get("title", "No title")
            published = post.get("published_at", "")[:10]
            source = post.get("source", {}).get("title", "Unknown")
            votes = post.get("votes", {})
            positive = votes.get("positive", 0)
            negative = votes.get("negative", 0)
            sentiment = "🟢 Bullish" if positive > negative else ("🔴 Bearish" if negative > positive else "⚪ Neutral")

            result += f"{i}. [{published}] {title}\n"
            result += f"   Source: {source} | Sentiment: {sentiment} (👍{positive} 👎{negative})\n\n"

        return result

    except Exception as e:
        # 如果 API 调用失败，返回提示
        return f"Crypto news unavailable for {coin} (API error: {str(e)}). Please check CryptoPanic API or use alternative news source."


# ─────────────────────────────────────────────
# 宏观加密市场新闻
# ─────────────────────────────────────────────

def get_crypto_global_news(limit: int = 20) -> str:
    """
    宏观日历与黑天鹅预警 — 日线交易专用。

    不再返回微观新闻，只筛选可能引发市场大幅波动的宏观事件：
    1. 美联储（Fed）利率决议 / 鲍威尔讲话
    2. 美国 CPI / 非农 / PCE 数据发布
    3. 行业重大崩盘事件（交易所倒闭、监管禁令等）

    如果当天有重磅宏观事件，交易系统应输出 "Neutral" 以规避波动。
    """
    MACRO_KEYWORDS = [
        "fed", "federal reserve", "interest rate", "jerome powell", "powell",
        "cpi", "consumer price", "nonfarm", "non-farm", "payroll", "pce",
        "inflation", "quantitative easing", "quantitative tightening",
        "sec", "regulation", "ban", "crackdown", "lawsuit",
        "bankruptcy", "collapse", "fraud", "ftx", "luna", "terra",
        "blacklist", "sanction", "treasury",
        "war", "geopolitical", "crisis",
    ]

    try:
        # Fetch broader market news with higher limit for filtering
        url = f"https://cryptopanic.com/api/v1/posts/?auth_token=free&public=true&kind=news&limit={limit * 3}"
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        posts = data.get("results", [])
        if not posts:
            return "No global crypto market news available"

        # Filter for macro-impactful news only
        macro_posts = []
        for post in posts:
            title = (post.get("title", "") or "").lower()
            source = (post.get("source", {}).get("title", "") or "").lower()
            if any(kw in title or kw in source for kw in MACRO_KEYWORDS):
                macro_posts.append(post)
            if len(macro_posts) >= limit:
                break

        if not macro_posts:
            return (
                "=== Macro Calendar & Black Swan Filter ===\n\n"
                "[CLEAN] No macro-impactful crypto news detected.\n"
                "No Fed decisions, CPI/NFP releases, or systemic risk events found.\n"
                "Market conditions appear normal for daily swing trading.\n"
            )

        result = (
            "=== Macro Calendar & Black Swan Warning ===\n"
            "WARNING: These events may cause significant market volatility.\n"
            "If any event is scheduled for today, consider staying NEUTRAL.\n\n"
        )
        for i, post in enumerate(macro_posts, 1):
            title = post.get("title", "No title")
            published = post.get("published_at", "")[:10]
            source = post.get("source", {}).get("title", "Unknown")
            currencies = ", ".join(
                [c.get("code", "") for c in post.get("currencies", [])]
            ) or "General"

            result += f"{i}. [{published}] {title}\n"
            result += f"   Source: {source} | Related: {currencies}\n\n"

        result += (
            "\n=== Trading Guidance ===\n"
            "If any of the above events are scheduled for today, "
            "the system should default to NEUTRAL/CLOSE to avoid volatility risk.\n"
        )

        return result

    except Exception as e:
        return f"Macro news unavailable (API error: {str(e)})"
