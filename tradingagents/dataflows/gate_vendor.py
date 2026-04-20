# tradingagents/dataflows/gate_vendor.py
"""
Gate.io 数据层 —— 通过 CCXT 获取加密货币合约市场数据。
所有函数均返回格式化字符串。
"""

import ccxt
import pandas as pd
from datetime import datetime, timezone
from typing import Optional


# ─────────────────────────────────────────────
# 日线对齐工具
# ─────────────────────────────────────────────

def _filter_closed_daily_candles(df: pd.DataFrame) -> pd.DataFrame:
    """过滤掉当前未收盘的日线 K 线。"""
    now_utc = datetime.now(timezone.utc)
    today_open = now_utc.replace(hour=0, minute=0, second=0, microsecond=0)
    return df[df["datetime"] < today_open].copy()


# ─────────────────────────────────────────────
# 交易所实例（单例缓存）
# ─────────────────────────────────────────────
_exchange_cache: Optional[ccxt.gate] = None


def get_gate_exchange() -> ccxt.gate:
    """获取（或创建）Gate.io 交易所实例。"""
    global _exchange_cache
    if _exchange_cache is not None:
        return _exchange_cache

    exchange = ccxt.gate({
        'options': {'defaultType': 'swap'},
        'enableRateLimit': True,
    })

    _exchange_cache = exchange
    return exchange


def reset_exchange_cache():
    """重置交易所缓存。"""
    global _exchange_cache
    _exchange_cache = None


# ─────────────────────────────────────────────
# K 线 / OHLCV
# ─────────────────────────────────────────────

def get_gate_ohlcv(symbol: str, timeframe: str = "1h", limit: int = 200) -> str:
    """
    获取加密货币 OHLCV K 线数据。
    """
    try:
        exchange = get_gate_exchange()
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)

        if not ohlcv:
            return f"No OHLCV data available for {symbol}"

        df = pd.DataFrame(
            ohlcv,
            columns=["timestamp", "open", "high", "low", "close", "volume"],
        )
        df["datetime"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
        df = df[["datetime", "open", "high", "low", "close", "volume"]]
        df = df.sort_values("datetime").reset_index(drop=True)

        # 日线过滤
        if timeframe in ("1d", "3d"):
            df = _filter_closed_daily_candles(df)

        if df.empty:
            return f"No closed candles available for {symbol}"

        result = f"OHLCV Data for {symbol} ({timeframe}, last {len(df)} candles)\n"
        result += f"Latest closed price: {df['close'].iloc[-1]:.4f} USDT\n"
        result += f"24h High: {df['high'].tail(24).max():.4f} | 24h Low: {df['low'].tail(24).min():.4f}\n\n"
        result += df.tail(50).to_string(index=False)
        return result

    except Exception as e:
        return f"Error fetching OHLCV for {symbol}: {str(e)}"


# ─────────────────────────────────────────────
# 技术指标
# ─────────────────────────────────────────────

def get_gate_indicators(symbol: str, timeframe: str = "1h", limit: int = 200) -> str:
    """
    计算加密货币技术指标（SMA/EMA/MACD/RSI/Bollinger/ATR）。
    """
    try:
        exchange = get_gate_exchange()
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)

        if not ohlcv:
            return f"No data available for indicators calculation of {symbol}"

        df = pd.DataFrame(
            ohlcv,
            columns=["timestamp", "open", "high", "low", "close", "volume"],
        )
        df["datetime"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
        df = df.sort_values("datetime").reset_index(drop=True)

        # 日线过滤
        if timeframe in ("1d", "3d"):
            df = _filter_closed_daily_candles(df)

        if df.empty:
            return f"No candles available for indicator calculation of {symbol}"

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

        result += "--- Volatility ---\n"
        result += f"ATR-14: {fmt(last['atr'])} ({fmt(last['atr'] / current_price * 100)}% of price)\n"

        return result

    except Exception as e:
        return f"Error calculating indicators for {symbol}: {str(e)}"


# ─────────────────────────────────────────────
# Ticker
# ─────────────────────────────────────────────

def get_gate_ticker(symbol: str) -> str:
    """获取最新行情快照。"""
    try:
        exchange = get_gate_exchange()
        ticker = exchange.fetch_ticker(symbol)

        last = ticker.get("last", None)
        change_pct = ticker.get("percentage", None)
        high_24h = ticker.get("high", None)
        low_24h = ticker.get("low", None)
        vol_24h = ticker.get("baseVolume", None)

        result = f"=== Market Ticker for {symbol} ===\n"
        result += f"Last Price:    {last:.4f} USDT\n" if last else "Last Price: N/A\n"
        result += f"24h Change:    {change_pct:+.2f}%\n" if change_pct is not None else ""
        result += f"24h High:      {high_24h:.4f}\n" if high_24h else ""
        result += f"24h Low:       {low_24h:.4f}\n" if low_24h else ""
        result += f"24h Volume:    {vol_24h:,.2f}\n" if vol_24h else ""

        return result

    except Exception as e:
        return f"Error fetching ticker for {symbol}: {str(e)}"


# ─────────────────────────────────────────────
# Order Book
# ─────────────────────────────────────────────

def get_gate_orderbook(symbol: str, depth: int = 20) -> str:
    """获取市场深度（订单簿）数据。"""
    try:
        exchange = get_gate_exchange()
        ob = exchange.fetch_order_book(symbol, limit=depth)

        bids = ob.get("bids", [])
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

        pressure = "Buying Pressure" if bid_ask_ratio > 1.1 else ("Selling Pressure" if bid_ask_ratio < 0.9 else "Balanced")

        result = f"=== Order Book for {symbol} ===\n"
        result += f"Best Bid: {best_bid:.4f} | Best Ask: {best_ask:.4f}\n"
        result += f"Spread:   {spread:.4f} ({spread_pct:.4f}%)\n\n"

        result += f"--- Pressure Analysis ---\n"
        result += f"Total Bid Volume: {total_bid_vol:.4f}\n"
        result += f"Total Ask Volume: {total_ask_vol:.4f}\n"
        result += f"Bid/Ask Ratio: {bid_ask_ratio:.3f} — {pressure}\n"

        return result

    except Exception as e:
        return f"Error fetching order book for {symbol}: {str(e)}"


# ─────────────────────────────────────────────
# Funding Rate
# ─────────────────────────────────────────────

def get_gate_funding_rate(symbol: str) -> str:
    """获取永续合约当前资金费率。"""
    try:
        exchange = get_gate_exchange()
        funding_info = exchange.fetch_funding_rate(symbol)
        current_rate = funding_info.get("fundingRate", None)

        result = f"=== Funding Rate for {symbol} ===\n"
        if current_rate is not None:
            rate_pct = current_rate * 100
            sentiment = "Bullish (Longs pay Shorts)" if current_rate < 0 else "Bearish (Shorts pay Longs)"
            result += f"Current Rate:    {rate_pct:.6f}%\n"
            result += f"Market Sentiment: {sentiment}\n"
        else:
            result += "Current Rate:    N/A\n"

        return result

    except Exception as e:
        return f"Error fetching funding rate for {symbol}: {str(e)}"


# ─────────────────────────────────────────────
# Open Interest
# ─────────────────────────────────────────────

def get_gate_open_interest(symbol: str) -> str:
    """
    获取永续合约未平仓合约量。
    注意：Gate.io API 不支持 open interest，返回提示信息。
    """
    # Gate.io 不支持未平仓量数据，返回空数据但不报错
    return f"=== Open Interest for {symbol} ===\n[Gate.io] Open interest data is not available via Gate.io API.\nThis metric would show total outstanding contracts if using Binance/Bitget."


# ─────────────────────────────────────────────
# Volume Anomaly Detection
# ─────────────────────────────────────────────

def detect_gate_volume_anomaly(symbol: str, timeframe: str = "4h", lookback_period: int = 50) -> str:
    """检测成交量异常。"""
    try:
        exchange = get_gate_exchange()
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=lookback_period + 10)

        if not ohlcv:
            return f"No volume data available for {symbol}"

        df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
        df["datetime"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
        df = df.sort_values("datetime").reset_index(drop=True)

        volume = df["volume"]
        vol_mean = volume.rolling(20).mean()
        vol_std = volume.rolling(20).std()
        vol_upper = vol_mean + 2 * vol_std
        vol_lower = vol_mean + 0.5 * vol_std

        latest_vol = volume.iloc[-1]
        latest_mean = vol_mean.iloc[-1]
        latest_std = vol_std.iloc[-1]
        latest_upper = vol_upper.iloc[-1]

        z_score = (latest_vol - latest_mean) / latest_std if latest_std > 0 else 0

        anomaly_type = "NORMAL"
        anomaly_desc = "成交量处于正常范围"

        if latest_vol > latest_upper:
            anomaly_type = "UNUSUALLY_HIGH"
            anomaly_desc = f"异常放量（+{z_score:.1f}σ）— 可能是主力进场/突破确认信号"
        elif latest_vol < vol_lower.iloc[-1]:
            anomaly_type = "UNUSUALLY_LOW"
            anomaly_desc = f"异常缩量（-{abs(z_score):.1f}σ）— 市场观望情绪浓厚"

        result = f"=== Volume Anomaly Detection for {symbol} ({timeframe}) ===\n\n"
        result += f"Latest Volume: {latest_vol:,.0f}\n"
        result += f"20-period Avg Volume: {latest_mean:,.0f}\n"
        result += f"Volume vs Avg: {((latest_vol / latest_mean - 1) * 100):+.1f}%\n\n"
        result += f"Anomaly Type: {anomaly_type}\n"
        result += f"Analysis: {anomaly_desc}\n"

        return result

    except Exception as e:
        return f"Error detecting volume anomaly for {symbol}: {str(e)}"


# ─────────────────────────────────────────────
# Global News (macro)
# ─────────────────────────────────────────────

def get_gate_crypto_global_news(limit: int = 20) -> str:
    """获取宏观加密市场新闻（通过 CryptoPanic）。"""
    try:
        # CryptoPanic free API endpoint
        url = f"https://cryptopanic.com/api/v1/posts/?public=true&kind=news&limit={limit}"
        import requests
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        posts = data.get("results", [])
        if not posts:
            return "No global crypto news available"

        result = f"=== Global Crypto News (Latest {len(posts)} articles) ===\n\n"
        for i, post in enumerate(posts, 1):
            title = post.get("title", "No title")
            published = post.get("published_at", "")[:10]
            source = post.get("source", {}).get("title", "Unknown")

            result += f"{i}. [{published}] {title}\n"
            result += f"   Source: {source}\n\n"

        return result

    except Exception as e:
        # 如果 API 失败，返回友好提示
        return f"=== Global Crypto News ===\n[News unavailable] CryptoPanic API request failed.\nThis is a free API with rate limits. News data would be displayed here when available."
