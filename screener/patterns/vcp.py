"""VCP-style volatility contraction inside a corrective base."""

from __future__ import annotations

import numpy as np
import pandas as pd

from screener.indicators import find_swing_highs, find_swing_lows
from screener.patterns.base_common import PatternHit


def detect_vcp_contraction(df: pd.DataFrame, lookback: int = 120) -> PatternHit | None:
    """
    Adapted VCP for bottoming bases (post-correction):
    - Multiple pullbacks with progressively smaller % depths
    - Volume dries up on later contractions
    - Higher lows preferred
    - Pivot = most recent contraction high
    """
    if len(df) < max(80, lookback // 2):
        return None

    window = df.iloc[-lookback:].copy()
    lows_flag = find_swing_lows(window["Low"], order=4)
    highs_flag = find_swing_highs(window["High"], order=4)
    swing_lows = window.loc[lows_flag, "Low"]
    swing_highs = window.loc[highs_flag, "High"]

    if len(swing_lows) < 2 or len(swing_highs) < 2:
        return None

    # Build contractions: peak -> trough depth sequence (most recent 2-4)
    # Pair chronological highs/lows
    events = []
    for idx, price in swing_highs.items():
        events.append(("H", idx, float(price)))
    for idx, price in swing_lows.items():
        events.append(("L", idx, float(price)))
    events.sort(key=lambda x: x[1])

    contractions: list[float] = []
    contraction_vols: list[float] = []
    troughs: list[float] = []
    peaks: list[float] = []

    i = 0
    while i < len(events) - 1:
        if events[i][0] == "H":
            # find next low
            j = i + 1
            while j < len(events) and events[j][0] != "L":
                j += 1
            if j < len(events):
                peak = events[i][2]
                trough = events[j][2]
                if peak > 0 and trough < peak:
                    depth = (peak - trough) / peak * 100
                    if 2 <= depth <= 35:
                        seg = window.loc[events[i][1] : events[j][1], "Volume"]
                        contractions.append(depth)
                        contraction_vols.append(float(seg.mean()) if len(seg) else np.nan)
                        troughs.append(trough)
                        peaks.append(peak)
                i = j
            else:
                break
        else:
            i += 1

    if len(contractions) < 2:
        return None

    recent = contractions[-4:]
    recent_vols = contraction_vols[-4:]
    recent_troughs = troughs[-4:]
    recent_peaks = peaks[-4:]

    # Progressive contraction: each depth <= prior * 0.95 (allow small noise)
    shrinking = all(recent[k] <= recent[k - 1] * 0.98 for k in range(1, len(recent)))
    # At least overall last < first
    overall_shrink = recent[-1] < recent[0] * 0.85

    if not (shrinking or overall_shrink):
        return None

    higher_lows = all(recent_troughs[k] >= recent_troughs[k - 1] * 0.995 for k in range(1, len(recent_troughs)))

    # Volume dry-up across contractions
    vol_dry = False
    if len(recent_vols) >= 2 and not any(np.isnan(recent_vols)):
        vol_dry = recent_vols[-1] < recent_vols[0] * 0.85

    # ATR contraction
    atr_now = float(window["ATR_PCT"].iloc[-1])
    atr_prev = float(window["ATR_PCT"].iloc[-min(40, len(window) - 1)])
    atr_contract = atr_now < atr_prev * 0.85

    pivot = float(max(recent_peaks[-2:]))
    support = float(min(recent_troughs[-2:]))
    last = float(window["Close"].iloc[-1])
    dist = (pivot - last) / pivot * 100 if pivot else 99

    score = 50.0
    score += 12 if shrinking else 6
    score += 8 if overall_shrink else 0
    score += 10 if higher_lows else 0
    score += 10 if vol_dry else 0
    score += 8 if atr_contract else 0
    score += min(10.0, (recent[0] - recent[-1]))  # magnitude of contraction

    if last >= pivot * 0.998:
        # breakout attempt
        vol_ratio = float(window["Volume"].iloc[-1] / (window["VOL_SMA50"].iloc[-1] or 1))
        if vol_ratio >= 1.4:
            status = "BREAKOUT"
            score += 10
        else:
            status = "NEAR_ENTRY"
            score += 5
    elif dist <= 3.0:
        status = "NEAR_ENTRY"
        score += 7
    else:
        status = "FORMING"

    score = float(np.clip(score, 0, 100))
    if score < 52:
        return None

    depths_txt = " → ".join(f"{d:.1f}%" for d in recent)
    notes = (
        f"Contractions {depths_txt}; "
        f"{'higher lows' if higher_lows else 'mixed lows'}; "
        f"{'vol dry-up' if vol_dry else 'vol flat'}; "
        f"ATR {atr_prev:.2f}%→{atr_now:.2f}%"
    )
    return PatternHit(
        name="VCP Base",
        score=score,
        pivot=pivot,
        support=support,
        status=status,
        notes=notes,
        extras={"contractions": recent, "atr_now": atr_now},
    )
