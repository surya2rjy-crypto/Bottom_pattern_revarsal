# Bottom Reversal Screener — Methodology & Metrics

This document explains **how the screener works**, **why each filter exists**, and **how scores are built**. It is designed for swing / positional traders hunting **high-probability bottoms and bases** after a correction from the 52-week high — on **Nifty 500 equities** and **Indian ETFs**.

---

## 1. Research basis (what “high probability” means here)

Bottom fishing has a poor base rate if you only buy “down a lot.” Professional process combines:

| Idea | Source / tradition | How we use it |
|------|--------------------|---------------|
| Corrective depth + time | Classical TA / IBD bases | Must be off 52w high long enough to form a base; avoid brand-new spikes down |
| Rounded / saucer bottom | Classic chart patterns | Slow U-turn with volume dry-up mid-base |
| VCP (volatility contraction) | Mark Minervini | Adapted **inside a corrective base**: tighter pullbacks, volume dry-up, pivot break |
| Double / W bottom | Classical TA | Two matched lows, neckline, seller exhaustion on 2nd low |
| Descending trendline / falling wedge | Classical TA | Supply line break with rising lows |
| Support zone memory | Auction / S/R theory | Zones that previously produced **strong reversals** when retested |
| Spring / shakeout | Wyckoff | Undercut of range low that quickly reclaims on climax volume |
| Volume & OBV | Wyckoff / volume analysis | Dry-up in base, accumulation, up-day volume dominance |
| Momentum turn | RSI / MACD | Divergence + histogram turn — timing, not prediction alone |

**Design goal:** fewer names, higher quality. Page 1 of Excel shows **only Ready-To-Entry** names.

---

## 2. Pipeline (end-to-end)

```
Nifty 500 CSV (NSE) + Indian ETF list
        ↓
Yahoo Finance daily OHLCV (.NS)
        ↓
Indicators (SMA, ATR, RSI, MACD, OBV, 52w stats)
        ↓
Gate: correction from 52w high
        ↓
Base quality + Pattern detectors (6 families)
        ↓
Volume / Momentum / RS / Support-zone scoring
        ↓
Composite score + bucket (Ready / Forming / Watch)
        ↓
Excel workbook (Ready sheet first)
```

---

## 3. Universe filters

| Metric | Logic | Why |
|--------|-------|-----|
| Nifty 500 | Official NSE constituent list (refreshed when online) | Liquid, investable large/mid universe |
| Indian ETFs | Curated liquid NSE ETFs (index, sector, gold, silver, etc.) | Same reversal logic on thematic beta |
| Min price | Default ≥ ₹20 | Avoid illiquid penny noise |
| Min avg volume | 20-day average ≥ 50,000 | Need exits; patterns fail in dead tape |
| History | ~2 years daily | Need 52w context + multi-month bases |

---

## 4. Gate — Correction from 52-week high

Both **stocks and ETFs** must be corrected from their 52-week high.

| Parameter | Default | Meaning |
|-----------|---------|---------|
| Min distance from high | 12% | Still near highs → not a “bottom” study |
| Max distance from high | 55% | Deeper often = structural damage / value trap |
| Ideal band | 18–35% | Historically constructive for base-building |
| Days since 52w high | ≥ 20 | Time needed for a real base |

**Component score `correction_quality`:** rewards ideal depth + maturity of the decline; penalizes “peak was last week.”

---

## 5. Gate — Base structure

We want **coiling after decline**, not a waterfall.

| Check | Logic |
|-------|-------|
| Range compression | Recent 20d range &lt; prior range |
| ATR compression | ATR% now &lt; ATR% ~50d ago |
| No waterfall | Last 10 closes not strictly declining |
| SMA50 behaviour | Reclaim / test / slope flattening upward |

**Component score `base_structure`.**

---

## 6. Pattern detectors (high-probability structures)

At least one pattern should fire for Ready/Forming quality lists.

### 6.1 Rounded Bottom (Saucer)

- Window split into left / mid / right thirds  
- Left slope down, right slope up, mid relatively flat  
- Positive quadratic curvature (U-shape)  
- Trough near middle of window (not a V at the edge)  
- Depth typically ~8–45%  
- Bonus: volume U-shape (high → dry → expanding)  
- **Pivot** = rim / neckline resistance  
- Status: FORMING / NEAR_ENTRY (within ~3% of rim) / BREAKOUT  

### 6.2 VCP Base (post-correction)

Minervini VCP adapted for **bases after correction** (not Stage-2 breakouts only):

- 2–4 swing pullbacks with **progressively smaller % depths**  
- Prefer **higher lows**  
- Volume dry-up on later contractions  
- ATR% contracting  
- **Pivot** = most recent contraction high  
- Breakout preferred on volume surge vs 50-day volume  

### 6.3 Double Bottom (W)

- Two swing lows within ~3.5%  
- Separation 10–80 sessions  
- Neckline = intervening high  
- Bonus: 2nd low on lower volume; RSI bullish divergence  
- **Pivot** = neckline  

### 6.4 Descending Trendline Break

- Linear fit through last 3–5 swing highs must slope **down** with solid R²  
- Prefer rising swing lows (falling-wedge character)  
- Entry when price reclaims the line  
- **Pivot** = trendline value today  

### 6.5 Strong Support Zone

- Cluster swing lows into zones (±2.5%)  
- Require multiple touches  
- Measure **historical bounce size** after each touch  
- Prefer zones with prior **strong reversals**  
- Current price defending / reclaiming that zone after the correction  
- This encodes: *“if price came to this zone before, it reversed hard.”*  

### 6.6 Wyckoff Spring

- Define a trading range  
- Brief undercut of range low  
- Fast reclaim above range low  
- Prefer volume climax on spring bar  
- **Pivot** = range high  

**Component score `pattern_quality`:** top pattern score, with confluence bonus if two patterns agree.

---

## 7. Volume signature

| Signal | Logic | Interpretation |
|--------|-------|----------------|
| Dry-up | 20d vol &lt; 75% of 50d vol | Supply exhausted in base |
| Climax resolved | Huge volume spike earlier, not today | Capitulation already happened |
| OBV rising | OBV up while price flat/mild up | Quiet accumulation |
| Up-day vol &gt; down-day vol | Last ~15 sessions | Demand winning short-term battles |

**Component score `volume_signature`.**

---

## 8. Momentum turn

| Signal | Logic |
|--------|-------|
| RSI zone | Prefer ~40–60 (constructive) over dead &lt;30 or euphoric &gt;70 at bottoms |
| MACD histogram | Turning up / expanding positive |
| RSI divergence | RSI higher at equal/lower price low |

**Component score `momentum_turn`.** Timing aid — never used alone.

---

## 9. Relative strength

Vs **NIFTYBEES** benchmark:

- RS 3-month and 6-month = stock return − benchmark return  
- Prefer names that are basing without catastrophic relative lag  

**Component score `relative_strength`.**

---

## 10. Composite score & buckets

Default weights (`config/settings.yaml`):

| Component | Weight |
|-----------|--------|
| Correction quality | 12 |
| Base structure | 22 |
| Pattern quality | 20 |
| Volume signature | 15 |
| Momentum turn | 12 |
| Support zone strength | 12 |
| Relative strength | 7 |

**Total score** = weighted average (0–100).

| Bucket | Rule (defaults) | Excel sheet |
|--------|-----------------|-------------|
| **READY_ENTRY** | Score ≥ 80 **and** classical trigger pattern NEAR_ENTRY/BREAKOUT **and** within ~2.5% of pivot **and** confluence (2 triggers or trigger+support zone) **and** volume/base/momentum floors | **Sheet 1 only** |
| FORMING | Score ≥ 60 with recognizable pattern | Sheet 2 |
| WATCHLIST | Score ≥ 48 | Sheet 3 |
| REJECT | Below thresholds / failed gates | Not exported as primary ideas |

ETFs use the **same logic**, also split onto ETF-specific sheets.

---

## 11. Columns in Excel (what each means)

| Column | Meaning |
|--------|---------|
| Score | Composite conviction 0–100 |
| Pattern | Best pattern(s) detected |
| Status | FORMING / NEAR_ENTRY / BREAKOUT |
| % from 52W High | Correction depth (negative) |
| Pivot | Trigger / neckline / rim / trendline |
| Support | Structural invalidation / stop reference |
| Dist to Pivot % | How close to trigger |
| Risk/Reward | Suggested stop / pivot / extension sketch |
| Correction…RS | Component scores |
| Explanation | Full plain-English rationale |

---

## 12. How to trade off the Ready sheet (process, not advice)

1. Open **1_Ready_To_Entry** only for new risk.  
2. Read **Explanation** + confirm pattern on a daily chart.  
3. Prefer entries on **pivot break** or **successful zone hold** after spring/test.  
4. Place invalidation below **Support** (or pattern low).  
5. If name is on Forming sheet — wait; do not force.  
6. Size smaller when market index itself is in free-fall.

---

## 13. Tuning for stricter / looser results

Edit `config/settings.yaml`:

- Raise `entry.ready_min_score` (e.g. 78) → fewer, stricter Ready names  
- Narrow `correction` band → only “perfect” pullbacks  
- Raise `universe.min_avg_volume` → more liquid only  

---

## 14. Limitations (read this)

- Patterns are **statistical**, not guarantees.  
- Yahoo Finance data can have gaps/adjustments.  
- Corporate actions / illiquid sessions can distort volume.  
- No fundamentals / news / FII flows in v1 (price-volume structure only).  
- ETF creations/redemptions can make volume less “Wyckoff-pure” than stocks.  
- **Not financial advice.**

---

## 15. Why this tends to work better than “% down” screens

A name that is merely −30% from high can still be in a cascade. This screener requires **evidence of seller exhaustion + structural base + recognizable reversal template + proximity to a defined trigger**, then ranks with transparent component scores so you can see *why* a name made Sheet 1.
