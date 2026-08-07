# TradingView — Bottom Reversal Pro

Pine Script indicator that mirrors the **Bottom Reversal Screener** logic on any chart (NSE stocks, Indian ETFs, or other symbols).

> This folder is independent of the Python Excel screener. It does not modify screener code.

## Files

| File | Purpose |
|------|---------|
| `Bottom_Reversal_Pro.pine` | Main overlay indicator (score, patterns, Ready/Forming, alerts) |
| `../docs/TRADINGVIEW_GUIDE.md` | Install, usage, screener tips, logic map |

## Quick install

1. Open [TradingView](https://www.tradingview.com/) → chart (prefer **1D**)
2. Pine Editor → **Open** → paste contents of `Bottom_Reversal_Pro.pine`
3. **Save** → **Add to chart**
4. Optional: create alerts on `Ready To Entry` / `Pivot Breakout`

## What you see

- **Pattern drawings on chart** (main feature):
  - Blue **W** = Double Bottom (+ dashed neckline)
  - Purple **zigzag** = VCP contractions (+ pivot)
  - Teal **U curve** = Rounded / Saucer bottom (+ rim)
  - Orange **line** = Descending trendline break
  - Green **band** = Strong support-zone pattern
  - Red **box / SPRING** = Wyckoff spring
  - Grey ▲▼ = swing pivots used by detectors
- Dashboard table: score, status, pivot/support numbers
- No background fill and no generic S/R plot lines (kept clean for learning patterns)

## Display toggles

| Input | Default | Purpose |
|-------|---------|---------|
| Draw detected patterns | On | Master switch for drawings |
| Draw all active patterns | On | Off = only primary/secondary names |
| Mark swing highs/lows | On | See the pivots the engine uses |
| Show READY marker | Off | Optional |

## TradingView Screener (optional)

After adding the script to favorites, in TV Screener filter on:

- `BR Ready Flag` = 1  
- and/or `BR Score` ≥ 80  

(Exact screener UX depends on your TradingView plan.)
