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

- Dashboard: Status, Score 0–100, pattern name, pivot/support, component scores
- Green background + **READY** label = high-probability entry zone
- Orange = forming base (wait)
- Teal line = pivot / neckline / rim  
- Red line = structural support / stop reference

## TradingView Screener (optional)

After adding the script to favorites, in TV Screener filter on:

- `BR Ready Flag` = 1  
- and/or `BR Score` ≥ 80  

(Exact screener UX depends on your TradingView plan.)
