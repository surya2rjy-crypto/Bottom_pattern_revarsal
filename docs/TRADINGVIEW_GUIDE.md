# TradingView Indicator Guide — Bottom Reversal Pro

This document explains how to install and use the Pine Script indicator that mirrors the Python **Bottom Reversal Screener** (Nifty 500 + Indian ETFs methodology) on TradingView charts.

The indicator lives only under `tradingview/` and does **not** change the Python screener.

---

## 1. Install on TradingView

1. Open a chart (recommended: **Daily**, NSE symbol e.g. `NSE:RELIANCE` or `NSE:NIFTYBEES`).
2. Bottom panel → **Pine Editor**.
3. Delete the default stub → paste the full contents of  
   `tradingview/Bottom_Reversal_Pro.pine`.
4. Click **Save** (name it e.g. `Bottom Reversal Pro`).
5. Click **Add to chart**.
6. (Optional) Click **⋯** on the script → **Add to favorites** so it appears in indicators quickly.

### Alerts

1. Click **Alerts** → Create alert.
2. Condition → select **Bottom Reversal Pro**.
3. Choose:
   - **Ready To Entry** — first bar that flips to Ready
   - **Pivot Breakout** — close clears pivot with volume bias
   - **Forming Base** — early watch

---

## 2. Dashboard fields

| Field | Meaning |
|-------|---------|
| STATUS | `READY TO ENTRY` / `FORMING BASE` / `WATCHLIST` / `NO SETUP` |
| SCORE | Weighted 0–100 conviction (same philosophy as Excel screener) |
| Pattern | Best pattern(s): Rounded Bottom, VCP Base, Double Bottom, Trendline Break, Strong Support Zone, Wyckoff Spring |
| Pat Status | `FORMING` / `NEAR_ENTRY` / `BREAKOUT` |
| % vs 52W High | Correction depth (must be in band for setups) |
| Pivot | Trigger level (neckline / rim / last contraction high / trendline) |
| Support | Invalidation / stop reference |
| Dist→Pivot | How close price is to the trigger |
| Component rows | Correction, Base, PatternQ, Volume, Momentum, SupportZone, RS proxy |
| Risk map | Suggested stop / pivot sketch |

---

## 3. Logic map (Python screener ↔ Pine)

| Screener concept | Pine implementation |
|------------------|---------------------|
| Corrected from 52w high (−12% to −55%, ideal 18–35%) | `high52`, `pctFromHigh`, `corrScore`, `inCorrBand` |
| Days since peak | `barsSinceHigh` ≥ input min |
| Base coil (range/ATR compress, no waterfall, SMA50) | `baseScore` |
| Volume dry-up, climax done, OBV, up-day vol | `volScore` |
| RSI / MACD hist / RSI divergence | `momScore` |
| RS vs benchmark | Local **RS proxy** (3m return vs SMA200 slope) — TV single-symbol limit |
| Rounded bottom | Left/right slopes + rim/trough + volume U-shape |
| VCP | Progressive swing pullback depths + ATR/vol dry-up |
| Double bottom | Two pivot lows within tolerance + neckline |
| Trendline break | Descending swing-high line extrapolated to now |
| Strong support zone | Clustered pivot lows with prior bounce strength |
| Wyckoff spring | Undercut of range low + quick reclaim |
| Ready gate | Score ≥ 80, trigger pattern, confluence, near pivot ≤ 2.5%, volume/momentum floors |

**Ready-To-Entry** (green) is intentionally strict — same design goal as Excel sheet 1.

---

## 4. Using TradingView Screener

Hidden plots (for screener / strategies):

- `BR Score`
- `BR Ready Flag` (1 = Ready)
- `BR Forming Flag`
- `BR % from 52W High`

Typical filter idea:

1. Add script to chart once and keep it saved.
2. Open **Stock Screener** → filter exchange **NSE**.
3. Where your plan allows custom indicator filters, require:
   - `BR Ready Flag` = 1  
   - optional: pullback depth via `% from 52W High` between −55 and −12  

> Note: Custom indicator screening availability depends on TradingView subscription. If unavailable, scan watchlists manually or use the Python Excel screener for the full Nifty 500 universe, then confirm on TV with this indicator.

---

## 5. Recommended workflow

1. Run Python `run_screener.bat` → get Excel Ready list (full universe).
2. Open each Ready symbol on TradingView with **Bottom Reversal Pro**.
3. Confirm dashboard Status = READY, pivot/support make sense visually.
4. Set alert for breakout if you want to wait for the trigger.
5. Manage risk below **Support**.

Or use the Pine indicator standalone on any chart / watchlist.

---

## 6. Inputs you may tune

| Input group | When to tighten |
|-------------|-----------------|
| Ready min score | Raise to 85 for fewer signals |
| Near-pivot % | Lower to 1.5 for only very tight entries |
| Min/max pullback | Narrow band for “cleaner” corrections |
| Swing pivot length | 4–6 daily; higher = fewer swings |

---

## 7. Differences vs Python screener

| Topic | Difference |
|-------|------------|
| Universe | TV = one symbol (or TV screener). Python = full Nifty 500 + ETF list auto |
| Relative strength | Pine uses SMA200 slope proxy; Python uses NIFTYBEES benchmark |
| Data | TradingView vs Yahoo Finance — small OHLC/volume differences possible |
| Excel export | Python only |

Both share the same research basis and Ready/Forming philosophy.

---

## Fix: Runtime error RE10008

If you see a red `!` with **Runtime error: RE10008**, replace the script with the latest
`tradingview/Bottom_Reversal_Pro.pine` from this repo.

**Cause:** Pine historical-buffer limits — usually dynamic `ta.highest/lowest` lengths,
deep history inside loops, or per-bar array allocation.

**What we changed:**
- Fixed-length `ta.*` calls only (no dynamic lengths)
- `max_bars_back=500` + explicit buffers on key series
- No `array.new_*()` on every bar
- Simpler saucer slopes / support-zone bounce proxies

Then in TradingView: Pine Editor → paste updated script → Save → Add to chart.
Use **Daily** timeframe for best results.

