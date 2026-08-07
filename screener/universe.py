"""Build investable universe: Nifty 500 + Indian ETFs."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import pandas as pd
import requests

from screener.config_loader import DATA_DIR


NIFTY500_URL = "https://archives.nseindia.com/content/indices/ind_nifty500list.csv"
FALLBACK_CSV = DATA_DIR / "nifty500_raw.csv"
ETF_CSV = DATA_DIR / "indian_etfs.csv"


@dataclass(frozen=True)
class Instrument:
    symbol: str          # NSE symbol without suffix
    name: str
    asset_type: str      # STOCK | ETF
    industry: str = ""
    yf_ticker: str = ""

    def __post_init__(self) -> None:
        if not self.yf_ticker:
            object.__setattr__(self, "yf_ticker", f"{self.symbol}.NS")


def _headers() -> dict:
    return {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "text/csv,application/octet-stream,*/*",
    }


def refresh_nifty500(dest: Path = FALLBACK_CSV, timeout: int = 30) -> Path:
    """Download latest Nifty 500 list; keep prior file on failure."""
    try:
        r = requests.get(NIFTY500_URL, headers=_headers(), timeout=timeout)
        r.raise_for_status()
        dest.write_bytes(r.content)
    except Exception:
        if not dest.exists():
            raise
    return dest


def load_nifty500(refresh: bool = True) -> list[Instrument]:
    path = refresh_nifty500() if refresh else FALLBACK_CSV
    if not path.exists():
        refresh_nifty500()
    df = pd.read_csv(path)
    # Normalize columns
    cols = {c.lower().strip(): c for c in df.columns}
    sym_col = cols.get("symbol") or cols.get("ticker")
    name_col = cols.get("company name") or cols.get("company") or cols.get("name")
    ind_col = cols.get("industry") or cols.get("sector")
    out: list[Instrument] = []
    for _, row in df.iterrows():
        symbol = str(row[sym_col]).strip().upper()
        if not symbol or symbol == "NAN":
            continue
        name = str(row[name_col]).strip() if name_col else symbol
        industry = str(row[ind_col]).strip() if ind_col else ""
        out.append(Instrument(symbol=symbol, name=name, asset_type="STOCK", industry=industry))
    return out


def load_etfs() -> list[Instrument]:
    if not ETF_CSV.exists():
        return []
    df = pd.read_csv(ETF_CSV)
    out: list[Instrument] = []
    seen: set[str] = set()
    for _, row in df.iterrows():
        symbol = str(row["symbol"]).strip().upper()
        if not symbol or symbol in seen:
            continue
        seen.add(symbol)
        name = str(row.get("name", symbol)).strip()
        category = str(row.get("category", "ETF")).strip()
        out.append(
            Instrument(
                symbol=symbol,
                name=name,
                asset_type="ETF",
                industry=category,
            )
        )
    return out


def build_universe(
    include_nifty500: bool = True,
    include_etfs: bool = True,
    refresh: bool = True,
) -> list[Instrument]:
    items: list[Instrument] = []
    seen: set[str] = set()

    def add_all(batch: Iterable[Instrument]) -> None:
        for inst in batch:
            if inst.symbol in seen:
                continue
            seen.add(inst.symbol)
            items.append(inst)

    if include_nifty500:
        add_all(load_nifty500(refresh=refresh))
    if include_etfs:
        add_all(load_etfs())
    return items


def export_universe_snapshot(instruments: list[Instrument], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["symbol", "name", "asset_type", "industry", "yf_ticker"])
        for i in instruments:
            w.writerow([i.symbol, i.name, i.asset_type, i.industry, i.yf_ticker])
