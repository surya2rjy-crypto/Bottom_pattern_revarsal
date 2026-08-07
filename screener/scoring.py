"""Composite scoring for high-probability bottom reversal candidates."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

from screener.patterns import (
    PatternHit,
    detect_double_bottom,
    detect_descending_trendline_break,
    detect_rounded_bottom,
    detect_support_zone_reversal,
    detect_vcp_contraction,
    detect_wyckoff_spring,
)


@dataclass
class ScanResult:
    symbol: str
    name: str
    asset_type: str
    industry: str
    price: float
    high_52w: float
    low_52w: float
    pct_from_high: float
    pct_from_low: float
    total_score: float
    bucket: str                  # READY_ENTRY | FORMING | WATCHLIST | REJECT
    primary_pattern: str
    pattern_status: str
    pivot: float | None
    support: float | None
    dist_to_pivot_pct: float | None
    risk_reward_hint: str
    explanation: str
    component_scores: dict[str, float] = field(default_factory=dict)
    patterns: list[PatternHit] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)


def _correction_quality(df: pd.DataFrame, cfg: dict) -> tuple[float, str, dict]:
    last = df.iloc[-1]
    pct = float(last["PCT_FROM_HIGH"])
    min_c = -float(cfg["correction"]["max_pct_from_high"])
    max_c = -float(cfg["correction"]["min_pct_from_high"])
    # pct is negative when below high
    if pct > max_c or pct < min_c:
        return 0.0, "Correction outside quality band", {"pct_from_high": pct}

    # Ideal sweet spot ~18-35% pullback
    depth = abs(pct)
    if 18 <= depth <= 35:
        score = 90
        note = f"Ideal corrective depth {depth:.1f}% from 52w high"
    elif 12 <= depth < 18:
        score = 70
        note = f"Moderate pullback {depth:.1f}% from 52w high"
    elif 35 < depth <= 45:
        score = 72
        note = f"Deep but still constructive pullback {depth:.1f}%"
    else:
        score = 55
        note = f"Edge-of-band pullback {depth:.1f}%"

    # Prefer that 52w high is not yesterday (time to base)
    high_idx = df["Close"].iloc[-252:].idxmax() if len(df) >= 100 else df["Close"].idxmax()
    bars_since = len(df.loc[high_idx:]) - 1
    if bars_since >= cfg["correction"]["days_since_52w_high_min"]:
        score = min(100, score + 8)
        note += f"; {bars_since}d since peak"
    else:
        score = max(0, score - 20)
        note += f"; only {bars_since}d since peak (too fresh)"

    return float(score), note, {"pct_from_high": pct, "bars_since_high": bars_since}


def _base_structure(df: pd.DataFrame, cfg: dict) -> tuple[float, str, dict]:
    """Is price coiling instead of free-falling?"""
    look = min(80, len(df) - 1)
    window = df.iloc[-look:]
    # Lower highs of downtrend stabilizing: last 20d range vs prior 40d range
    r_recent = float((window["High"].iloc[-20:].max() - window["Low"].iloc[-20:].min()) / window["Close"].iloc[-1] * 100)
    r_prior = float((window["High"].iloc[-60:-20].max() - window["Low"].iloc[-60:-20].min()) / window["Close"].iloc[-1] * 100) if look >= 60 else r_recent * 1.2

    atr_now = float(df["ATR_PCT"].iloc[-1])
    atr_old = float(df["ATR_PCT"].iloc[-min(50, len(df) - 1)])
    compress = atr_now < atr_old

    # No waterfall: last 10 closes not all lower
    last10 = df["Close"].iloc[-10:].values
    waterfall = all(last10[i] < last10[i - 1] for i in range(1, len(last10)))

    # Price vs SMA50/100 — reclaim attempts
    last = df.iloc[-1]
    above_50 = last["Close"] > last["SMA50"] if pd.notna(last["SMA50"]) else False
    slope_50 = float(df["SMA50"].iloc[-1] - df["SMA50"].iloc[-10]) if pd.notna(df["SMA50"].iloc[-1]) else 0

    score = 45.0
    notes = []
    if r_prior > 0 and r_recent < r_prior * 0.85:
        score += 15
        notes.append("range compressing")
    if compress:
        score += 12
        notes.append(f"ATR {atr_old:.2f}%→{atr_now:.2f}%")
    if not waterfall:
        score += 10
        notes.append("no waterfall")
    else:
        score -= 15
        notes.append("still waterfalling")
    if above_50:
        score += 10
        notes.append("above SMA50")
    elif last["Close"] > last["SMA50"] * 0.97 if pd.notna(last["SMA50"]) else False:
        score += 5
        notes.append("testing SMA50")
    if slope_50 > 0:
        score += 8
        notes.append("SMA50 flattening/up")

    # Base length estimate: days since most recent significant low cluster
    score = float(np.clip(score, 0, 100))
    return score, "; ".join(notes) or "base mixed", {"atr_now": atr_now, "range_recent": r_recent}


def _volume_signature(df: pd.DataFrame, cfg: dict) -> tuple[float, str, dict]:
    last = df.iloc[-1]
    vol20 = float(last["VOL_SMA20"] or 0)
    vol50 = float(last["VOL_SMA50"] or 1)
    dry = vol20 < vol50 * float(cfg["base"]["vol_dryup_ratio"])

    # Selling climax in past 40d then quieter
    recent = df.iloc[-40:]
    climax_idx = recent["Volume"].idxmax()
    climax_vol = float(recent.loc[climax_idx, "Volume"])
    climax_done = climax_vol > vol50 * 1.8 and climax_idx != recent.index[-1]

    # OBV rising over last 20 while price flat/up
    obv_slope = float(df["OBV"].iloc[-1] - df["OBV"].iloc[-20])
    price_chg = float(df["Close"].iloc[-1] / df["Close"].iloc[-20] - 1) * 100
    accum = obv_slope > 0 and price_chg > -3

    score = 40.0
    notes = []
    if dry:
        score += 20
        notes.append("volume dry-up in base")
    if climax_done:
        score += 15
        notes.append("prior volume climax resolved")
    if accum:
        score += 18
        notes.append("OBV accumulation")
    # Up-day volume > down-day volume last 15
    w = df.iloc[-15:]
    up = w.loc[w["Close"] > w["Close"].shift(1), "Volume"].mean()
    down = w.loc[w["Close"] < w["Close"].shift(1), "Volume"].mean()
    if pd.notna(up) and pd.notna(down) and down > 0 and up > down:
        score += 10
        notes.append("up-day vol > down-day vol")

    return float(np.clip(score, 0, 100)), "; ".join(notes) or "volume neutral", {
        "vol20_vs_50": vol20 / vol50 if vol50 else None
    }


def _momentum_turn(df: pd.DataFrame) -> tuple[float, str, dict]:
    last = df.iloc[-1]
    rsi = float(last["RSI14"]) if pd.notna(last["RSI14"]) else 50
    hist = float(last["MACD_HIST"]) if pd.notna(last["MACD_HIST"]) else 0
    hist_prev = float(df["MACD_HIST"].iloc[-3]) if pd.notna(df["MACD_HIST"].iloc[-3]) else hist

    score = 40.0
    notes = []
    if 40 <= rsi <= 60:
        score += 18
        notes.append(f"RSI neutral-constructive ({rsi:.0f})")
    elif 30 <= rsi < 40:
        score += 12
        notes.append(f"RSI recovering ({rsi:.0f})")
    elif rsi < 30:
        score += 5
        notes.append(f"RSI oversold ({rsi:.0f})")
    elif 60 < rsi <= 70:
        score += 10
        notes.append(f"RSI strong ({rsi:.0f})")
    else:
        score += 2
        notes.append(f"RSI extended ({rsi:.0f})")

    if hist > hist_prev and hist > 0:
        score += 20
        notes.append("MACD hist expanding positive")
    elif hist > hist_prev:
        score += 12
        notes.append("MACD hist turning up")

    # RSI bullish divergence vs recent low
    low_price_idx = df["Close"].iloc[-40:].idxmin()
    low_rsi_at_price = float(df.loc[low_price_idx, "RSI14"])
    rsi_now = rsi
    price_now = float(last["Close"])
    price_low = float(df.loc[low_price_idx, "Close"])
    if rsi_now > low_rsi_at_price + 3 and price_now <= price_low * 1.05:
        score += 15
        notes.append("RSI bullish divergence")

    return float(np.clip(score, 0, 100)), "; ".join(notes), {"rsi": rsi, "macd_hist": hist}


def _relative_strength(df: pd.DataFrame, bench: pd.DataFrame | None) -> tuple[float, str, dict]:
    """Stock 3m / 6m return vs benchmark (NiftyBees proxy)."""
    if bench is None or bench.empty or len(df) < 70:
        # Absolute RS fallback: recent performance from low
        ret_3m = float(df["Close"].iloc[-1] / df["Close"].iloc[-63] - 1) * 100
        score = 50 + np.clip(ret_3m, -20, 20)
        return float(np.clip(score, 0, 100)), f"3m return {ret_3m:.1f}% (no bench)", {"rs_3m": ret_3m}

    # Align dates
    joined = pd.concat(
        [df["Close"].rename("s"), bench["Close"].rename("b")],
        axis=1,
        join="inner",
    ).dropna()
    if len(joined) < 70:
        return 50.0, "RS unavailable", {}

    def ret(col, n):
        return float(joined[col].iloc[-1] / joined[col].iloc[-n] - 1) * 100

    rs3 = ret("s", 63) - ret("b", 63)
    rs6 = ret("s", min(126, len(joined) - 1)) - ret("b", min(126, len(joined) - 1))
    score = 50 + np.clip(rs3 * 1.2, -25, 30) + np.clip(rs6 * 0.5, -15, 15)
    note = f"RS 3m {rs3:+.1f}% vs bench; 6m {rs6:+.1f}%"
    return float(np.clip(score, 0, 100)), note, {"rs_3m": rs3, "rs_6m": rs6}


def collect_patterns(df: pd.DataFrame) -> list[PatternHit]:
    detectors = [
        detect_rounded_bottom,
        detect_vcp_contraction,
        detect_double_bottom,
        detect_descending_trendline_break,
        detect_support_zone_reversal,
        detect_wyckoff_spring,
    ]
    hits: list[PatternHit] = []
    for fn in detectors:
        try:
            hit = fn(df)
            if hit is not None:
                hits.append(hit)
        except Exception:
            continue
    hits.sort(key=lambda h: h.score, reverse=True)
    return hits


def analyze_symbol(
    symbol: str,
    name: str,
    asset_type: str,
    industry: str,
    df: pd.DataFrame,
    cfg: dict,
    bench: pd.DataFrame | None = None,
) -> ScanResult | None:
    if df is None or len(df) < 120:
        return None

    last = df.iloc[-1]
    price = float(last["Close"])
    if price < float(cfg["universe"]["min_price"]):
        return None
    vol20 = float(last["VOL_SMA20"] or 0)
    if vol20 < float(cfg["universe"]["min_avg_volume"]):
        return None

    corr_s, corr_n, corr_m = _correction_quality(df, cfg)
    if corr_s <= 0:
        return None

    base_s, base_n, base_m = _base_structure(df, cfg)
    vol_s, vol_n, vol_m = _volume_signature(df, cfg)
    mom_s, mom_n, mom_m = _momentum_turn(df)
    rs_s, rs_n, rs_m = _relative_strength(df, bench)

    patterns = collect_patterns(df)
    if not patterns:
        # Require at least one recognizable structure for high-probability list
        pattern_s = 25.0
        primary = "No clear classic pattern"
        pstatus = "FORMING"
        pivot = None
        support = float(df["Low"].iloc[-60:].min())
        pattern_notes = "Structure incomplete — excluded from high-conviction unless other scores elite"
    else:
        primary_hit = patterns[0]
        # Blend top 2 pattern scores
        pattern_s = primary_hit.score
        if len(patterns) > 1:
            pattern_s = 0.7 * primary_hit.score + 0.3 * patterns[1].score
            pattern_s = min(100, pattern_s + 5)  # confluence bonus
        primary = " + ".join(h.name for h in patterns[:2])
        pstatus = primary_hit.status
        # Prefer NEAR_ENTRY/BREAKOUT status from any top pattern
        for h in patterns:
            if h.status in ("NEAR_ENTRY", "BREAKOUT"):
                pstatus = h.status
                pivot = h.pivot
                support = h.support
                break
        else:
            pivot = primary_hit.pivot
            support = primary_hit.support
        pattern_notes = " | ".join(f"{h.name}: {h.notes}" for h in patterns[:3])

    weights = cfg["scoring"]["weights"]
    components = {
        "correction_quality": corr_s,
        "base_structure": base_s,
        "pattern_quality": pattern_s,
        "volume_signature": vol_s,
        "momentum_turn": mom_s,
        "support_zone_strength": next((h.score for h in patterns if h.name == "Strong Support Zone"), base_s * 0.6),
        "relative_strength": rs_s,
    }

    total = 0.0
    wsum = 0.0
    for k, w in weights.items():
        total += components.get(k, 0) * w
        wsum += w
    total_score = float(total / wsum) if wsum else 0.0

    # Hard quality gates for READY_ENTRY
    dist_to_pivot = None
    if pivot and pivot > 0:
        dist_to_pivot = (pivot - price) / pivot * 100

    ready_min = float(cfg["entry"]["ready_min_score"])
    forming_min = float(cfg["entry"]["forming_min_score"])
    watch_min = float(cfg["entry"]["watchlist_min_score"])
    near = float(cfg["entry"]["near_pivot_pct"])

    # High-probability Ready gate: confluence OR elite single pattern,
    # constructive volume, and proximity to a defined pivot.
    confluence = len(patterns) >= 2
    elite_pattern = pattern_s >= 72
    near_pivot = dist_to_pivot is not None and dist_to_pivot <= near + 0.5
    # If already through pivot (BREAKOUT), require volume participation
    breakout_ok = True
    if pstatus == "BREAKOUT":
        v50 = float(df["VOL_SMA50"].iloc[-1] or 1)
        breakout_ok = float(df["Volume"].iloc[-1]) >= v50 * 1.2

    ready = (
        total_score >= ready_min
        and patterns
        and pstatus in ("NEAR_ENTRY", "BREAKOUT")
        and near_pivot
        and pattern_s >= 65
        and vol_s >= 50
        and base_s >= 50
        and (confluence or elite_pattern)
        and breakout_ok
        and corr_s >= 55
    )

    if ready:
        bucket = "READY_ENTRY"
    elif total_score >= forming_min and patterns and pattern_s >= 52:
        bucket = "FORMING"
    elif total_score >= watch_min:
        bucket = "WATCHLIST"
    else:
        bucket = "REJECT"

    # Risk-reward hint
    if pivot and support and pivot > support:
        risk = price - support
        reward = pivot - price
        if risk > 0:
            # to pivot is short-term; stretch target = pivot + (pivot-support)
            stretch = (pivot - support)
            rr = stretch / risk if risk else 0
            risk_reward_hint = f"Stop~{support:.2f} | Pivot~{pivot:.2f} | Ext~{pivot+stretch:.2f} | R:R≈{rr:.1f}"
        else:
            risk_reward_hint = f"Above support {support:.2f}; pivot {pivot:.2f}"
    else:
        risk_reward_hint = "See chart for stop/pivot"

    explanation = (
        f"SCORE {total_score:.0f}/100 — {primary} ({pstatus}). "
        f"Correction: {corr_n}. Base: {base_n}. Volume: {vol_n}. "
        f"Momentum: {mom_n}. RS: {rs_n}. Patterns: {pattern_notes}."
    )

    return ScanResult(
        symbol=symbol,
        name=name,
        asset_type=asset_type,
        industry=industry,
        price=price,
        high_52w=float(last["HIGH_52W"]),
        low_52w=float(last["LOW_52W"]),
        pct_from_high=float(last["PCT_FROM_HIGH"]),
        pct_from_low=float(last["PCT_FROM_LOW"]),
        total_score=round(total_score, 1),
        bucket=bucket,
        primary_pattern=primary,
        pattern_status=pstatus,
        pivot=float(pivot) if pivot else None,
        support=float(support) if support else None,
        dist_to_pivot_pct=round(dist_to_pivot, 2) if dist_to_pivot is not None else None,
        risk_reward_hint=risk_reward_hint,
        explanation=explanation,
        component_scores={k: round(v, 1) for k, v in components.items()},
        patterns=patterns,
        metrics={
            **corr_m,
            **base_m,
            **vol_m,
            **mom_m,
            **rs_m,
            "sma50": float(last["SMA50"]) if pd.notna(last["SMA50"]) else None,
            "sma200": float(last["SMA200"]) if pd.notna(last["SMA200"]) else None,
            "rsi": float(last["RSI14"]) if pd.notna(last["RSI14"]) else None,
            "avg_vol_20": vol20,
        },
    )
