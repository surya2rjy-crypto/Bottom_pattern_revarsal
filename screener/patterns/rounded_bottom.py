"""Rounded / saucer bottom detector."""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import linregress

from screener.patterns.base_common import PatternHit


def detect_rounded_bottom(df: pd.DataFrame, lookback: int = 90) -> PatternHit | None:
    """
    Detect a U-shaped saucer base:
    - Left side declining (negative slope)
    - Middle trough with compressed volatility
    - Right side rising (positive slope)
    - Prefer volume dry-up mid-base and expansion on right side
    """
    if len(df) < lookback + 10:
        return None

    window = df.iloc[-lookback:].copy()
    close = window["Close"].values
    vol = window["Volume"].values
    n = len(close)
    x = np.arange(n)

    # Split into thirds
    t1, t2 = n // 3, 2 * n // 3
    left, mid, right = close[:t1], close[t1:t2], close[t2:]
    if min(len(left), len(mid), len(right)) < 8:
        return None

    left_slope = linregress(np.arange(len(left)), left).slope
    right_slope = linregress(np.arange(len(right)), right).slope
    mid_slope = abs(linregress(np.arange(len(mid)), mid).slope)

    trough_idx = int(np.argmin(close))
    trough = float(close[trough_idx])
    left_high = float(np.max(left))
    right_high = float(np.max(right))
    rim = float(max(left_high, np.percentile(close[: max(5, t1)], 90)))

    depth_pct = (left_high - trough) / left_high * 100 if left_high > 0 else 0
    # Depth should be meaningful but not a crash
    if depth_pct < 8 or depth_pct > 45:
        return None

    # Trough should be near middle of window (rounded, not V at edge)
    trough_pos = trough_idx / n
    if trough_pos < 0.25 or trough_pos > 0.75:
        return None

    # Left declining, right rising, mid relatively flat
    price_scale = np.mean(close)
    if left_slope >= -0.01 * price_scale / len(left):
        return None
    if right_slope <= 0.005 * price_scale / len(right):
        return None

    # Quadratic curvature: positive coefficient => U-shape on price
    try:
        coeffs = np.polyfit(x, close, 2)
        curvature = coeffs[0]
    except Exception:
        curvature = 0.0
    if curvature <= 0:
        return None

    # Volume U-shape preference
    v_left = np.mean(vol[:t1]) + 1e-9
    v_mid = np.mean(vol[t1:t2]) + 1e-9
    v_right = np.mean(vol[t2:]) + 1e-9
    vol_ok = v_mid < v_left * 0.9 and v_right > v_mid

    last = float(close[-1])
    dist_to_rim = (rim - last) / rim * 100 if rim else 99

    score = 55.0
    score += min(15.0, depth_pct * 0.4)
    score += min(12.0, curvature * 1e6)  # scaled gently
    if vol_ok:
        score += 10
    # Symmetry bonus
    left_drop = left_high - trough
    right_rise = right_high - trough
    if left_drop > 0:
        sym = min(left_drop, right_rise) / max(left_drop, right_rise)
        score += sym * 10

    if last >= rim * 0.995 and vol[-5:].mean() > (window["VOL_SMA50"].iloc[-1] or vol.mean()):
        status = "BREAKOUT"
        score += 8
    elif dist_to_rim <= 3.0:
        status = "NEAR_ENTRY"
        score += 6
    elif right_slope > 0 and last > trough * 1.03:
        status = "FORMING"
    else:
        status = "FORMING"

    score = float(np.clip(score, 0, 100))
    if score < 50:
        return None

    notes = (
        f"Saucer depth {depth_pct:.1f}% over ~{lookback}d; "
        f"rim {rim:.2f}; trough at bar {trough_idx}; "
        f"{'volume U-shape OK' if vol_ok else 'volume mixed'}"
    )
    return PatternHit(
        name="Rounded Bottom",
        score=score,
        pivot=rim,
        support=trough,
        status=status,
        notes=notes,
        extras={"depth_pct": depth_pct, "lookback": lookback},
    )
