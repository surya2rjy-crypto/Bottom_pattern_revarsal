"""Historical support-zone strength: zones that previously produced strong reversals."""

from __future__ import annotations

import numpy as np
import pandas as pd

from screener.indicators import find_swing_lows
from screener.patterns.base_common import PatternHit


def detect_support_zone_reversal(
    df: pd.DataFrame,
    lookback: int = 252,
    zone_tol_pct: float = 2.5,
) -> PatternHit | None:
    """
    Identify a price zone that has acted as support multiple times
    (prior bounce was meaningful), and check if price is again defending
    that zone after the correction from 52w high.
    """
    if len(df) < 120:
        return None

    window = df.iloc[-lookback:].copy()
    low_flags = find_swing_lows(window["Low"], order=6)
    swing_lows = window.loc[low_flags, ["Low", "Close", "ATR14"]]
    if len(swing_lows) < 3:
        return None

    lows = swing_lows["Low"].values.astype(float)
    # Cluster lows into zones
    zones: list[dict] = []
    used = np.zeros(len(lows), dtype=bool)
    for i, lv in enumerate(lows):
        if used[i]:
            continue
        members = [i]
        used[i] = True
        for j in range(i + 1, len(lows)):
            if used[j]:
                continue
            if abs(lows[j] - lv) / lv * 100 <= zone_tol_pct:
                members.append(j)
                used[j] = True
        zone_level = float(np.mean(lows[members]))
        zones.append({"level": zone_level, "touches": len(members), "members": members})

    # Keep zones with >= 2 touches
    zones = [z for z in zones if z["touches"] >= 2]
    if not zones:
        return None

    last = float(window["Close"].iloc[-1])
    last_low = float(window["Low"].iloc[-1])
    atr = float(window["ATR14"].iloc[-1] or last * 0.02)

    # Score each zone by historical bounce quality + current proximity
    best: PatternHit | None = None
    for z in zones:
        level = z["level"]
        # Measure bounce after each touch
        bounce_scores = []
        idxs = list(swing_lows.index)
        for m in z["members"]:
            touch_idx = idxs[m]
            loc = window.index.get_loc(touch_idx)
            if isinstance(loc, slice):
                continue
            forward = window.iloc[loc : min(loc + 25, len(window))]
            if forward.empty:
                continue
            bounce_pct = (float(forward["High"].max()) - level) / level * 100
            bounce_scores.append(bounce_pct)

        if not bounce_scores:
            continue
        avg_bounce = float(np.mean(bounce_scores))
        strong_reversals = sum(1 for b in bounce_scores if b >= max(4.0, (atr / level) * 100 * 2))
        if strong_reversals < 1 and avg_bounce < 4:
            continue

        # Current distance to zone
        dist_pct = (last - level) / level * 100
        # Prefer sitting on / slightly above zone after testing it
        if dist_pct < -3 or dist_pct > 12:
            continue

        recently_tested = False
        recent = window.iloc[-15:]
        if ((recent["Low"] - level).abs() / level * 100 <= zone_tol_pct).any():
            recently_tested = True
        if not recently_tested and dist_pct > 5:
            continue

        score = 50.0
        score += min(15.0, z["touches"] * 5)
        score += min(20.0, avg_bounce * 1.5)
        score += min(12.0, strong_reversals * 6)
        if recently_tested:
            score += 8
        if 0 <= dist_pct <= 4:
            score += 10
        elif -1.5 <= dist_pct < 0:
            score += 6  # slight undercut/reclaim territory

        # Holding above zone after test
        holding = last > level and last_low <= level * (1 + zone_tol_pct / 100)
        if holding:
            score += 6

        if 0 <= dist_pct <= 3 and holding:
            status = "NEAR_ENTRY"
        elif last > level * 1.03 and recently_tested:
            status = "FORMING"
        else:
            status = "NEAR_ENTRY" if dist_pct <= 4 else "FORMING"

        # Pivot ~ first resistance above zone (recent local high)
        pivot = float(window["High"].iloc[-30:].max())
        hit = PatternHit(
            name="Strong Support Zone",
            score=float(np.clip(score, 0, 100)),
            pivot=pivot,
            support=level,
            status=status,
            notes=(
                f"Zone {level:.2f} touched {z['touches']}x; "
                f"avg bounce {avg_bounce:.1f}%; "
                f"strong reversals {strong_reversals}; "
                f"price {dist_pct:+.1f}% from zone"
            ),
            extras={
                "zone": level,
                "touches": z["touches"],
                "avg_bounce_pct": avg_bounce,
                "strong_reversals": strong_reversals,
            },
        )
        if best is None or hit.score > best.score:
            best = hit

    if best is None or best.score < 55:
        return None
    return best
