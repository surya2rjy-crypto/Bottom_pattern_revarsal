"""Technical indicators used by pattern & scoring engines."""

from __future__ import annotations

import numpy as np
import pandas as pd


def sma(series: pd.Series, window: int) -> pd.Series:
    return series.rolling(window, min_periods=max(2, window // 2)).mean()


def ema(series: pd.Series, window: int) -> pd.Series:
    return series.ewm(span=window, adjust=False).mean()


def rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high, low, close = df["High"], df["Low"], df["Close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            (high - low),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.rolling(period, min_periods=period // 2).mean()


def macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    macd_line = ema(close, fast) - ema(close, slow)
    signal_line = ema(macd_line, signal)
    hist = macd_line - signal_line
    return macd_line, signal_line, hist


def obv(close: pd.Series, volume: pd.Series) -> pd.Series:
    direction = np.sign(close.diff()).fillna(0)
    return (direction * volume).cumsum()


def enrich(df: pd.DataFrame) -> pd.DataFrame:
    """Add all indicators needed for screening."""
    out = df.copy()
    c = out["Close"]
    out["SMA20"] = sma(c, 20)
    out["SMA50"] = sma(c, 50)
    out["SMA100"] = sma(c, 100)
    out["SMA150"] = sma(c, 150)
    out["SMA200"] = sma(c, 200)
    out["EMA21"] = ema(c, 21)
    out["RSI14"] = rsi(c, 14)
    out["ATR14"] = atr(out, 14)
    out["ATR_PCT"] = (out["ATR14"] / c) * 100
    macd_line, signal_line, hist = macd(c)
    out["MACD"] = macd_line
    out["MACD_SIGNAL"] = signal_line
    out["MACD_HIST"] = hist
    out["OBV"] = obv(c, out["Volume"])
    out["VOL_SMA20"] = sma(out["Volume"], 20)
    out["VOL_SMA50"] = sma(out["Volume"], 50)
    out["HIGH_52W"] = c.rolling(252, min_periods=100).max()
    out["LOW_52W"] = c.rolling(252, min_periods=100).min()
    out["PCT_FROM_HIGH"] = (c / out["HIGH_52W"] - 1.0) * 100
    out["PCT_FROM_LOW"] = (c / out["LOW_52W"] - 1.0) * 100
    out["RANGE_PCT"] = (out["High"] - out["Low"]) / c * 100
    return out


def find_swing_lows(low: pd.Series, order: int = 5) -> pd.Series:
    """Boolean series: True where local swing low (order bars each side)."""
    vals = low.values
    n = len(vals)
    flags = np.zeros(n, dtype=bool)
    for i in range(order, n - order):
        window = vals[i - order : i + order + 1]
        if vals[i] == np.min(window) and np.sum(window == vals[i]) == 1:
            flags[i] = True
        elif vals[i] == np.min(window):
            # allow plateau: first occurrence
            if np.argmin(window) == order:
                flags[i] = True
    return pd.Series(flags, index=low.index)


def find_swing_highs(high: pd.Series, order: int = 5) -> pd.Series:
    vals = high.values
    n = len(vals)
    flags = np.zeros(n, dtype=bool)
    for i in range(order, n - order):
        window = vals[i - order : i + order + 1]
        if vals[i] == np.max(window) and np.argmax(window) == order:
            flags[i] = True
    return pd.Series(flags, index=high.index)
