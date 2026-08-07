"""
Bottom Reversal Screener — CLI entry point.

Scans Nifty 500 + Indian ETFs for high-probability bottom / base /
reversal setups after a correction from the 52-week high.
"""

from __future__ import annotations

import argparse
import sys
import traceback
from datetime import datetime
from pathlib import Path

# Allow running as `python -m screener.main` or `python screener/main.py`
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from screener.config_loader import OUTPUT_DIR, load_settings
from screener.data_fetcher import download_history
from screener.excel_export import export_workbook
from screener.indicators import enrich
from screener.scoring import ScanResult, analyze_symbol
from screener.universe import build_universe, export_universe_snapshot


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Professional bottom-reversal screener for Nifty 500 + Indian ETFs"
    )
    p.add_argument("--stocks-only", action="store_true", help="Skip ETFs")
    p.add_argument("--etfs-only", action="store_true", help="Scan ETFs only")
    p.add_argument("--limit", type=int, default=0, help="Limit symbols (debug/smoke test)")
    p.add_argument("--no-refresh-universe", action="store_true", help="Use cached Nifty 500 CSV")
    p.add_argument("--quiet", action="store_true", help="Less console output")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    cfg = load_settings()
    print("=" * 70)
    print("  BOTTOM REVERSAL SCREENER  |  Nifty 500 + Indian ETFs")
    print("  High-probability bases: Rounded / VCP / Double Bottom /")
    print("  Trendline Break / Support Zone / Wyckoff Spring")
    print("=" * 70)

    include_stocks = not args.etfs_only
    include_etfs = not args.stocks_only
    if args.etfs_only:
        include_stocks = False
        include_etfs = True

    print("\n[1/5] Building universe...")
    universe = build_universe(
        include_nifty500=include_stocks and cfg["universe"]["include_nifty500"],
        include_etfs=include_etfs and cfg["universe"]["include_etfs"],
        refresh=not args.no_refresh_universe,
    )
    if args.limit and args.limit > 0:
        universe = universe[: args.limit]
    export_universe_snapshot(universe, OUTPUT_DIR / "universe_snapshot.csv")
    print(f"      Symbols: {len(universe)} "
          f"(stocks={sum(1 for u in universe if u.asset_type=='STOCK')}, "
          f"etfs={sum(1 for u in universe if u.asset_type=='ETF')})")

    tickers = [u.yf_ticker for u in universe]
    # Always fetch benchmark for RS
    bench_ticker = "NIFTYBEES.NS"
    if bench_ticker not in tickers:
        tickers.append(bench_ticker)

    print("\n[2/5] Downloading daily market data (Yahoo Finance)...")
    print("      This can take several minutes on first run...")
    hist = download_history(
        tickers,
        period="2y",
        batch_size=int(cfg["performance"]["batch_size"]),
        pause=float(cfg["performance"]["request_pause_sec"]),
        show_progress=not args.quiet,
    )
    print(f"      Received history for {len(hist)} tickers")

    bench = hist.get(bench_ticker)
    if bench is not None:
        bench = enrich(bench)

    print("\n[3/5] Computing indicators & detecting patterns...")
    results: list[ScanResult] = []
    errors = 0
    for inst in universe:
        df = hist.get(inst.yf_ticker)
        if df is None or df.empty:
            continue
        try:
            edf = enrich(df)
            res = analyze_symbol(
                symbol=inst.symbol,
                name=inst.name,
                asset_type=inst.asset_type,
                industry=inst.industry,
                df=edf,
                cfg=cfg,
                bench=bench,
            )
            if res is not None and res.bucket != "REJECT":
                results.append(res)
        except Exception:
            errors += 1
            if not args.quiet:
                # Keep going; log lightly
                pass

    print(f"      Qualified names: {len(results)} (skipped errors: {errors})")
    ready_n = sum(1 for r in results if r.bucket == "READY_ENTRY")
    forming_n = sum(1 for r in results if r.bucket == "FORMING")
    watch_n = sum(1 for r in results if r.bucket == "WATCHLIST")
    print(f"      Ready={ready_n} | Forming={forming_n} | Watchlist={watch_n}")

    print("\n[4/5] Writing Excel workbook...")
    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    out_name = f"{cfg['output']['filename_prefix']}_{stamp}.xlsx"
    out_path = OUTPUT_DIR / out_name
    export_workbook(results, out_path)

    # Also write a stable "latest" copy
    latest = OUTPUT_DIR / f"{cfg['output']['filename_prefix']}_LATEST.xlsx"
    export_workbook(results, latest)

    print("\n[5/5] Done.")
    print("-" * 70)
    print(f"  Excel (timestamped): {out_path}")
    print(f"  Excel (latest):      {latest}")
    print("-" * 70)
    print("  Sheet 1 = Ready_To_Entry only (actionable zone).")
    print("  Other sheets = Forming / Watchlist / ETFs / Methodology.")
    print("  Read docs/METHODOLOGY.md for full metric explanations.")
    print("=" * 70)

    if ready_n:
        print("\nTop Ready-To-Entry ideas:")
        top = sorted(
            [r for r in results if r.bucket == "READY_ENTRY"],
            key=lambda x: x.total_score,
            reverse=True,
        )[:10]
        for r in top:
            print(
                f"  {r.total_score:5.1f}  {r.symbol:<12}  {r.primary_pattern:<28}  "
                f"{r.pct_from_high:+.1f}% from high  | {r.pattern_status}"
            )
    else:
        print("\nNo Ready-To-Entry names today — check Forming_Bases sheet.")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nCancelled.")
        raise SystemExit(130)
    except Exception as exc:
        print("\nFATAL ERROR:", exc)
        traceback.print_exc()
        raise SystemExit(1)
