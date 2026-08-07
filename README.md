# Bottom Reversal Screener

Professional Python screener that finds **high-probability bottom / base / reversal** setups in **Nifty 500 stocks + Indian ETFs** after a meaningful correction from the 52-week high.

## What it finds

Only names that clear multiple gates:

1. Corrected from 52-week high (quality depth band)
2. Forming a proper base (not free-falling)
3. Classic high-probability structure: **Rounded Bottom, VCP, Double Bottom, Descending Trendline Break, Strong Support Zone, Wyckoff Spring**
4. Volume + momentum confirmation
5. Scored with a plain-English explanation

## Excel output

| Sheet | Contents |
|-------|----------|
| **1_Ready_To_Entry** | **Page 1 — actionable zone only** (near pivot / breakout) |
| 2_Forming_Bases | Good bases, wait for trigger |
| 3_Watchlist_Early | Early / incomplete signals |
| 4_ETF_Ready | ETF ready-to-entry |
| 5_ETF_Forming | ETF forming / watch |
| 6_All_Qualified | Combined qualified list |
| How_This_Works | Built-in logic guide |

Files are written to `output/Bottom_Reversal_Screener_LATEST.xlsx`.

## Windows — run with one click

1. Install **Python 3.10+** from [python.org](https://www.python.org/downloads/) (tick **Add Python to PATH**).
2. Double-click **`run_screener.bat`**.
3. Wait for download + scan (several minutes first time).
4. Excel opens from the `output\` folder.

Smoke test (fast): double-click **`run_smoke_test.bat`**.

## Manual run

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
python -m screener.main
```

Useful flags:

```bash
python -m screener.main --limit 50      # debug subset
python -m screener.main --stocks-only
python -m screener.main --etfs-only
```

## Configuration

Edit `config/settings.yaml` to tighten/loosen thresholds (correction band, ready score, volume, etc.).

## Documentation

Full metric & pattern logic: **[docs/METHODOLOGY.md](docs/METHODOLOGY.md)**

## Disclaimer

Research / educational tool only. Not investment advice. Always confirm on charts and manage risk.
