"""Descending trendline break / falling-wedge style reclaim."""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import linregress

from screener.indicators import find_swing_highs, find_swing_lows
from screener.patterns.base_common import PatternHit


def detect_descending_trendline_break(df: pd.DataFrame, lookback: int = 90) -> PatternHit | None:
    """
    Fit descending resistance across recent swing highs.
    Bullish when price reclaims / closes above that line with improving volume,
    preferably with rising swing lows (falling wedge character).
    """
    if len(df) < 50:
        return None

    window = df.iloc[-lookback:].copy()
    high_flags = find_swing_highs(window["High"], order=4)
    low_flags = find_swing_lows(window["Low"], order=4)
    sh = window.loc[high_flags]
    sl = window.loc[low_flags]
    if len(sh) < 3:
        return None

    # Use last 3-5 swing highs
    sh_use = sh.iloc[-5:]
    x = np.arange(len(window))
    # Map index positions
    positions = [window.index.get_loc(i) for i in sh_use.index]
    positions = [p if isinstance(p, (int, np.integer)) else p.start for p in positions]
    y = sh_use["High"].values.astype(float)
    if len(positions) < 3:
        return None

    slope, intercept, r_value, _, _ = linregress(positions, y)
    if slope >= 0:  # must be descending
        return None
    if abs(r_value) < 0.75:
        return None

    last_pos = len(window) - 1
    line_now = intercept + slope * last_pos
    last = float(window["Close"].iloc[-1])
    if line_now <= 0:
        return None

    # Rising lows?
    rising_lows = False
    if len(sl) >= 2:
        recent_lows = sl["Low"].values[-3:]
        rising_lows = all(recent_lows[k] >= recent_lows[k - 1] * 0.997 for k in range(1, len(recent_lows)))

    dist = (line_now - last) / line_now * 100
    vol_ratio = float(window["Volume"].iloc[-1] / (window["VOL_SMA50"].iloc[-1] or 1))

    score = 52.0
    score += min(15.0, abs(r_value) * 15)
    score += 8 if rising_lows else 0
    # Steeper but not vertical
    slope_pct = abs(slope) / float(window["Close"].mean()) * 100
    score += min(8.0, slope_pct * 20)

    if last > line_now * 1.002:
        status = "BREAKOUT" if vol_ratio >= 1.25 else "NEAR_ENTRY"
        score += 12 if status == "BREAKOUT" else 6
    elif dist <= 2.5:
        status = "NEAR_ENTRY"
        score += 8
    else:
        status = "FORMING"

    support = float(sl["Low"].iloc[-1]) if len(sl) else float(window["Low"].min())
    score = float(np.clip(score, 0, 100))
    if score < 55:
        return None

    notes = (
        f"Desc. resistance R²={r_value**2:.2f}, line≈{line_now:.2f}, "
        f"dist {dist:.1f}%, {'rising lows (wedge)' if rising_lows else 'lows mixed'}"
    )
    return PatternHit(
        name="Trendline Break",
        score=score,
        pivot=float(line_now),
        support=support,
        status=status,
        notes=notes,
        extras={"r2": float(r_value**2), "slope": float(slope)},
    )
