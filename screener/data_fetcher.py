"""Market data download helpers (Yahoo Finance)."""

from __future__ import annotations

import time
from typing import Iterable

import pandas as pd
import yfinance as yf
from tqdm import tqdm


def _normalize_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize any yfinance OHLCV shape to Open/High/Low/Close/Volume."""
    if df is None or df.empty:
        return pd.DataFrame()

    out = df.copy()

    # Flatten MultiIndex columns if present
    if isinstance(out.columns, pd.MultiIndex):
        # Prefer selecting a single ticker frame before calling this;
        # if still multi, try to collapse Price level.
        lvl0 = [str(x).lower() for x in out.columns.get_level_values(0)]
        price_names = {"open", "high", "low", "close", "adj close", "volume"}
        if any(x in price_names for x in lvl0):
            # level 0 is price
            out.columns = [str(c[0]) for c in out.columns]
        else:
            # level 1 is price (Ticker, Price)
            out.columns = [str(c[1]) for c in out.columns]

    mapping: dict = {}
    for c in out.columns:
        cl = str(c).strip().lower()
        if cl == "open":
            mapping[c] = "Open"
        elif cl == "high":
            mapping[c] = "High"
        elif cl == "low":
            mapping[c] = "Low"
        elif cl in ("close", "adj close", "adjclose"):
            # Prefer plain Close; if both exist last write wins after rename uniqueness
            mapping[c] = "Close"
        elif cl == "volume":
            mapping[c] = "Volume"
    out = out.rename(columns=mapping)

    # If duplicate Close columns appeared, keep first
    out = out.loc[:, ~pd.Index(out.columns).duplicated(keep="first")]

    keep = [c for c in ["Open", "High", "Low", "Close", "Volume"] if c in out.columns]
    if "Close" not in keep:
        return pd.DataFrame()
    out = out[keep].copy()
    out.index = pd.to_datetime(out.index)
    out = out[~out.index.duplicated(keep="last")].sort_index()
    out = out.dropna(subset=["Close"])
    # Coerce numerics
    for c in keep:
        out[c] = pd.to_numeric(out[c], errors="coerce")
    out = out.dropna(subset=["Close"])
    if "Volume" in out.columns:
        out["Volume"] = out["Volume"].fillna(0)
    return out


def _extract_ticker_frame(raw: pd.DataFrame, ticker: str) -> pd.DataFrame:
    if raw is None or raw.empty:
        return pd.DataFrame()

    if not isinstance(raw.columns, pd.MultiIndex):
        return _normalize_ohlcv(raw)

    levels0 = set(map(str, raw.columns.get_level_values(0)))
    levels1 = set(map(str, raw.columns.get_level_values(1)))

    try:
        if ticker in levels0:
            part = raw[ticker].copy()
            return _normalize_ohlcv(part)
        if ticker in levels1:
            part = raw.xs(ticker, axis=1, level=1).copy()
            return _normalize_ohlcv(part)
    except Exception:
        return pd.DataFrame()

    # Single-ticker download sometimes still multi-indexed with one ticker
    if len(levels0) == 1 or len(levels1) == 1:
        return _normalize_ohlcv(raw)
    return pd.DataFrame()


def download_one(ticker: str, period: str = "2y") -> pd.DataFrame:
    try:
        raw = yf.download(
            ticker,
            period=period,
            auto_adjust=True,
            progress=False,
            threads=False,
        )
        return _normalize_ohlcv(raw) if not isinstance(raw.columns, pd.MultiIndex) else _extract_ticker_frame(raw, ticker)
    except Exception:
        return pd.DataFrame()


def download_history(
    tickers: Iterable[str],
    period: str = "2y",
    batch_size: int = 40,
    pause: float = 0.05,
    show_progress: bool = True,
) -> dict[str, pd.DataFrame]:
    """
    Download OHLCV for many tickers.
    Returns mapping yf_ticker -> DataFrame.
    """
    tickers = list(dict.fromkeys(tickers))
    result: dict[str, pd.DataFrame] = {}
    batches = [tickers[i : i + batch_size] for i in range(0, len(tickers), batch_size)]
    iterator = tqdm(batches, desc="Downloading market data", unit="batch") if show_progress else batches

    for batch in iterator:
        try:
            raw = yf.download(
                tickers=batch,
                period=period,
                group_by="ticker",
                auto_adjust=True,
                threads=True,
                progress=False,
            )
        except Exception:
            for t in batch:
                nd = download_one(t, period=period)
                if len(nd) >= 120:
                    result[t] = nd
                time.sleep(pause)
            continue

        for t in batch:
            nd = _extract_ticker_frame(raw, t)
            if len(nd) >= 120:
                result[t] = nd
        time.sleep(pause)

    # Fill gaps with one-by-one retries for misses
    missing = [t for t in tickers if t not in result]
    if missing:
        retry_iter = tqdm(missing, desc="Retrying missing", unit="sym") if show_progress else missing
        for t in retry_iter:
            nd = download_one(t, period=period)
            if len(nd) >= 120:
                result[t] = nd
            time.sleep(pause)

    return result
