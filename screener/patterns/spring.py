"""Wyckoff spring / shakeout detector near base lows."""

from __future__ import annotations

import numpy as np
import pandas as pd

from screener.patterns.base_common import PatternHit


def detect_wyckoff_spring(df: pd.DataFrame, lookback: int = 80) -> PatternHit | None:
    """
    Spring: brief undercut of a trading-range low that quickly reclaims,
    ideally on volume climax then dry-up — classic accumulation tell.
    """
    if len(df) < lookback:
        return None

    window = df.iloc[-lookback:].copy()
    # Define range using middle portion lows/highs excluding last 10 bars
    base = window.iloc[:-8]
    if len(base) < 30:
        return None

    range_low = float(base["Low"].quantile(0.05))
    range_high = float(base["High"].quantile(0.90))
    if range_high <= range_low:
        return None
    depth = (range_high - range_low) / range_high * 100
    if depth < 5 or depth > 35:
        return None

    recent = window.iloc[-20:]
    min_low = float(recent["Low"].min())
    min_loc = recent["Low"].idxmin()
    # Must undercut range low
    undercut_pct = (range_low - min_low) / range_low * 100
    if undercut_pct < 0.3 or undercut_pct > 6:
        return None

    # Must reclaim above range_low after spring
    after = window.loc[min_loc:]
    if after.empty:
        return None
    last = float(window["Close"].iloc[-1])
    if last < range_low:
        return None

    # Volume climax on spring bar preferred
    spring_vol = float(window.loc[min_loc, "Volume"])
    avg_vol = float(window["VOL_SMA50"].iloc[-1] or window["Volume"].mean())
    climax = spring_vol > avg_vol * 1.3

    # Quick reclaim (within ~8 sessions)
    reclaim_bars = len(after)
    quick = reclaim_bars <= 10

    score = 55.0
    score += min(12.0, undercut_pct * 4)
    score += 10 if climax else 0
    score += 8 if quick else 0
    score += 8 if last > (range_low + range_high) / 2 * 0.98 else 0

    dist_to_pivot = (range_high - last) / range_high * 100
    if last >= range_high * 0.995:
        status = "BREAKOUT"
        score += 8
    elif dist_to_pivot <= 3.5:
        status = "NEAR_ENTRY"
        score += 6
    else:
        status = "FORMING"

    score = float(np.clip(score, 0, 100))
    if score < 58:
        return None

    notes = (
        f"Undercut {undercut_pct:.1f}% below {range_low:.2f}, "
        f"reclaimed in {reclaim_bars} bars; "
        f"{'volume climax' if climax else 'no climax'}; range high {range_high:.2f}"
    )
    return PatternHit(
        name="Wyckoff Spring",
        score=score,
        pivot=range_high,
        support=min_low,
        status=status,
        notes=notes,
        extras={"undercut_pct": undercut_pct, "range_low": range_low, "range_high": range_high},
    )
