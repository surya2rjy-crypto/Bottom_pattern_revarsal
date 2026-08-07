"""Double / triple bottom + W-pattern detector."""

from __future__ import annotations

import numpy as np
import pandas as pd

from screener.indicators import find_swing_highs, find_swing_lows
from screener.patterns.base_common import PatternHit


def detect_double_bottom(df: pd.DataFrame, lookback: int = 100) -> PatternHit | None:
    """
    Classic W / double bottom:
    - Two swing lows within ~3% of each other
    - Separation of at least ~10 sessions
    - Neckline = intervening swing high
    - Prefer 2nd low on lower volume (seller exhaustion)
    """
    if len(df) < 60:
        return None

    window = df.iloc[-lookback:].copy()
    low_flags = find_swing_lows(window["Low"], order=5)
    high_flags = find_swing_highs(window["High"], order=5)
    swing_lows = list(window.loc[low_flags, "Low"].items())
    if len(swing_lows) < 2:
        return None

    # Evaluate last few low pairs
    best: PatternHit | None = None
    for i in range(len(swing_lows) - 1):
        for j in range(i + 1, len(swing_lows)):
            d1_idx, d1 = swing_lows[i]
            d2_idx, d2 = swing_lows[j]
            d1, d2 = float(d1), float(d2)
            sep = window.index.get_loc(d2_idx) - window.index.get_loc(d1_idx)
            if isinstance(sep, slice):
                continue
            if sep < 10 or sep > 80:
                continue
            avg_low = (d1 + d2) / 2
            if avg_low <= 0:
                continue
            tol = abs(d1 - d2) / avg_low * 100
            if tol > 3.5:
                continue

            mid = window.loc[d1_idx:d2_idx]
            if mid.empty:
                continue
            neckline = float(mid["High"].max())
            depth = (neckline - avg_low) / neckline * 100
            if depth < 6 or depth > 40:
                continue

            # Volume at lows
            v1 = float(window.loc[d1_idx, "Volume"])
            v2 = float(window.loc[d2_idx, "Volume"])
            second_low_dry = v2 < v1 * 0.9

            last = float(window["Close"].iloc[-1])
            dist = (neckline - last) / neckline * 100

            score = 58.0
            score += max(0, 10 - tol * 2)
            score += min(12, depth * 0.35)
            if second_low_dry:
                score += 8
            if d2 >= d1 * 0.998:  # higher/equal second low (bullish)
                score += 6

            # RSI divergence proxy: RSI at 2nd low higher
            try:
                r1 = float(window.loc[d1_idx, "RSI14"])
                r2 = float(window.loc[d2_idx, "RSI14"])
                if r2 > r1 + 2 and d2 <= d1 * 1.01:
                    score += 10
            except Exception:
                pass

            if last >= neckline * 0.998:
                vol_ratio = float(window["Volume"].iloc[-1] / (window["VOL_SMA50"].iloc[-1] or 1))
                status = "BREAKOUT" if vol_ratio >= 1.3 else "NEAR_ENTRY"
                score += 8 if status == "BREAKOUT" else 4
            elif dist <= 3.0:
                status = "NEAR_ENTRY"
                score += 6
            else:
                status = "FORMING"

            score = float(np.clip(score, 0, 100))
            hit = PatternHit(
                name="Double Bottom",
                score=score,
                pivot=neckline,
                support=min(d1, d2),
                status=status,
                notes=(
                    f"Lows {d1:.2f}/{d2:.2f} (tol {tol:.1f}%), "
                    f"neckline {neckline:.2f}, depth {depth:.1f}%, "
                    f"{'2nd-low vol dry' if second_low_dry else 'vol mixed'}"
                ),
                extras={"tol_pct": tol, "depth_pct": depth},
            )
            if best is None or hit.score > best.score:
                best = hit

    if best is None or best.score < 55:
        return None
    return best
