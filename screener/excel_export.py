"""Professional multi-sheet Excel workbook export."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from openpyxl import Workbook
from openpyxl.formatting.rule import ColorScaleRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from screener.scoring import ScanResult


HEADER_FILL = PatternFill("solid", fgColor="1F4E79")
HEADER_FONT = Font(color="FFFFFF", bold=True, name="Calibri", size=11)
READY_FILL = PatternFill("solid", fgColor="C6EFCE")
FORMING_FILL = PatternFill("solid", fgColor="FFEB9C")
WATCH_FILL = PatternFill("solid", fgColor="DDEBF7")
ETF_FILL = PatternFill("solid", fgColor="E2D5F1")
THIN = Border(
    left=Side(style="thin", color="B0B0B0"),
    right=Side(style="thin", color="B0B0B0"),
    top=Side(style="thin", color="B0B0B0"),
    bottom=Side(style="thin", color="B0B0B0"),
)


COLUMNS = [
    ("Rank", 8),
    ("Symbol", 12),
    ("Name", 28),
    ("Type", 8),
    ("Industry", 18),
    ("Price", 10),
    ("Score", 9),
    ("Pattern", 22),
    ("Status", 12),
    ("% from 52W High", 14),
    ("% from 52W Low", 13),
    ("Pivot", 10),
    ("Support", 10),
    ("Dist to Pivot %", 12),
    ("Risk/Reward", 36),
    ("Correction", 10),
    ("Base", 9),
    ("PatternQ", 10),
    ("Volume", 9),
    ("Momentum", 10),
    ("SupportZone", 11),
    ("RS", 8),
    ("RSI", 8),
    ("Explanation", 80),
]


def _results_to_rows(results: list[ScanResult]) -> list[dict]:
    rows = []
    for i, r in enumerate(results, 1):
        cs = r.component_scores
        rows.append(
            {
                "Rank": i,
                "Symbol": r.symbol,
                "Name": r.name,
                "Type": r.asset_type,
                "Industry": r.industry,
                "Price": round(r.price, 2),
                "Score": r.total_score,
                "Pattern": r.primary_pattern,
                "Status": r.pattern_status,
                "% from 52W High": round(r.pct_from_high, 2),
                "% from 52W Low": round(r.pct_from_low, 2),
                "Pivot": round(r.pivot, 2) if r.pivot else None,
                "Support": round(r.support, 2) if r.support else None,
                "Dist to Pivot %": r.dist_to_pivot_pct,
                "Risk/Reward": r.risk_reward_hint,
                "Correction": cs.get("correction_quality"),
                "Base": cs.get("base_structure"),
                "PatternQ": cs.get("pattern_quality"),
                "Volume": cs.get("volume_signature"),
                "Momentum": cs.get("momentum_turn"),
                "SupportZone": cs.get("support_zone_strength"),
                "RS": cs.get("relative_strength"),
                "RSI": r.metrics.get("rsi"),
                "Explanation": r.explanation,
            }
        )
    return rows


def _write_sheet(wb: Workbook, title: str, results: list[ScanResult], banner: str, fill: PatternFill | None = None) -> None:
    # Excel sheet title max 31 chars
    title = title[:31]
    if title in wb.sheetnames:
        ws = wb[title]
    else:
        ws = wb.create_sheet(title)

    ws["A1"] = banner
    ws["A1"].font = Font(bold=True, size=14, color="1F4E79", name="Calibri")
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=8)

    ws["A2"] = f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')} | High-probability bottom reversal candidates only"
    ws["A2"].font = Font(italic=True, size=10, color="666666")

    headers = [c[0] for c in COLUMNS]
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=4, column=col, value=header)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = Alignment(horizontal="center", wrap_text=True, vertical="center")
        cell.border = THIN

    rows = _results_to_rows(results)
    for r_i, row in enumerate(rows):
        for c_i, key in enumerate(headers, 1):
            val = row.get(key)
            cell = ws.cell(row=5 + r_i, column=c_i, value=val)
            cell.border = THIN
            cell.alignment = Alignment(vertical="center", wrap_text=(key == "Explanation"))
            if fill and c_i == 1:
                cell.fill = fill
            if key == "Score" and isinstance(val, (int, float)):
                if val >= 72:
                    cell.fill = READY_FILL
                elif val >= 55:
                    cell.fill = FORMING_FILL

    for i, (_, width) in enumerate(COLUMNS, 1):
        ws.column_dimensions[get_column_letter(i)].width = width
    ws.row_dimensions[4].height = 30
    ws.freeze_panes = "A5"
    ws.auto_filter.ref = f"A4:{get_column_letter(len(headers))}{4 + max(1, len(rows))}"

    if rows:
        score_col = headers.index("Score") + 1
        ws.conditional_formatting.add(
            f"{get_column_letter(score_col)}5:{get_column_letter(score_col)}{4 + len(rows)}",
            ColorScaleRule(
                start_type="min",
                start_color="F8696B",
                mid_type="percentile",
                mid_value=50,
                mid_color="FFEB84",
                end_type="max",
                end_color="63BE7B",
            ),
        )


def _write_methodology_sheet(wb: Workbook) -> None:
    ws = wb.create_sheet("How_This_Works")
    ws["A1"] = "Bottom Reversal Screener — Logic & Metrics Guide"
    ws["A1"].font = Font(bold=True, size=16, color="1F4E79")
    ws.merge_cells("A1:B1")

    content = [
        ("", ""),
        ("PURPOSE", "Find high-probability bottoming / base / reversal setups in Nifty 500 stocks and Indian ETFs after a meaningful correction from the 52-week high."),
        ("", ""),
        ("UNIVERSE", "Nifty 500 equities (NSE) + curated liquid Indian ETFs. Liquidity filter: 20-day avg volume and minimum price."),
        ("GATE 1 — CORRECTION", "Price must be −12% to −55% from 52-week high, with enough time since the peak to form a base. Ideal depth is −18% to −35%."),
        ("GATE 2 — BASE", "Range/ATR compression, no waterfall selling, SMA50 flatten/reclaim attempts. We want coiling, not free-fall."),
        ("GATE 3 — PATTERN", "At least one classic high-probability structure: Rounded Bottom, VCP Base, Double Bottom, Descending Trendline Break, Strong Support Zone, or Wyckoff Spring."),
        ("GATE 4 — VOLUME", "Dry-up in the base, prior climax resolved, OBV accumulation, up-day volume > down-day volume."),
        ("GATE 5 — MOMENTUM", "RSI constructive / recovering, MACD histogram turning up, optional RSI bullish divergence."),
        ("GATE 6 — SUPPORT ZONE", "Zones with multiple historical touches that previously produced strong bounces score higher."),
        ("GATE 7 — RELATIVE STRENGTH", "3m/6m performance vs Nifty BeES benchmark — prefer names not lagging badly while basing."),
        ("", ""),
        ("SCORE", "Weighted blend of Correction, Base, Pattern, Volume, Momentum, Support Zone, RS. 0–100."),
        ("READY TO ENTRY (Sheet 1)", "Score ≥ configured ready threshold (default 72) AND pattern status NEAR_ENTRY/BREAKOUT AND within ~3% of pivot AND solid pattern+volume scores. These are the only names on page 1."),
        ("FORMING BASES", "Good structure building, but not yet at the entry trigger."),
        ("WATCHLIST", "Early / partial signals — monitor, do not treat as entries."),
        ("ETF sheets", "Same logic applied separately so ETFs do not crowd stock ideas."),
        ("", ""),
        ("PATTERNS — Rounded Bottom", "U-shaped saucer: declining left, flat mid, rising right, positive curvature, preferred volume U-shape, pivot = rim/neckline."),
        ("PATTERNS — VCP Base", "2–4 progressively tighter pullbacks after correction, higher lows preferred, volume/ATR dry-up, pivot = last contraction high."),
        ("PATTERNS — Double Bottom", "Two lows within ~3.5%, ≥10 sessions apart, neckline pivot, 2nd-low volume dry-up + RSI divergence bonus."),
        ("PATTERNS — Trendline Break", "Descending resistance across swing highs with good R²; rising lows (wedge) preferred; entry on reclaim."),
        ("PATTERNS — Strong Support Zone", "Clustered swing lows with prior strong bounce history; price defending the zone again."),
        ("PATTERNS — Wyckoff Spring", "Brief undercut of range low that quickly reclaims, ideally with volume climax — accumulation tell."),
        ("", ""),
        ("HOW TO USE", "1) Open Sheet 1 (Ready_To_Entry). 2) Read Explanation + Risk/Reward. 3) Confirm on chart. 4) Enter on pivot break / zone hold per your plan. 5) Stop below Support. Not financial advice."),
        ("DATA SOURCE", "Yahoo Finance daily OHLCV (.NS tickers). Nifty 500 list from NSE archives. Results depend on data quality/availability."),
        ("DISCLAIMER", "Educational / research tool only. Past pattern success does not guarantee future results. Always do your own due diligence."),
    ]

    ws.column_dimensions["A"].width = 28
    ws.column_dimensions["B"].width = 110
    for i, (a, b) in enumerate(content, start=3):
        ws.cell(row=i, column=1, value=a).font = Font(bold=True, color="1F4E79")
        ws.cell(row=i, column=2, value=b).alignment = Alignment(wrap_text=True)
        ws.row_dimensions[i].height = 36 if b else 10


def export_workbook(results: list[ScanResult], out_path: Path) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)

    etfs = [r for r in results if r.asset_type == "ETF"]

    ready = sorted(
        [r for r in results if r.bucket == "READY_ENTRY"],
        key=lambda x: x.total_score,
        reverse=True,
    )
    forming = sorted(
        [r for r in results if r.bucket == "FORMING"],
        key=lambda x: x.total_score,
        reverse=True,
    )
    watch = sorted(
        [r for r in results if r.bucket == "WATCHLIST"],
        key=lambda x: x.total_score,
        reverse=True,
    )
    ready_etfs = [r for r in ready if r.asset_type == "ETF"]
    forming_etfs = [r for r in forming if r.asset_type == "ETF"]

    wb = Workbook()
    # Remove default — we create named sheets
    default = wb.active
    wb.remove(default)

    # PAGE 1 — Ready to entry ONLY (combined, stocks first by score already)
    _write_sheet(
        wb,
        "1_Ready_To_Entry",
        ready,
        "READY TO ENTRY — High-probability setups near pivot / breakout zone (tradeable watch only)",
        READY_FILL,
    )
    _write_sheet(
        wb,
        "2_Forming_Bases",
        forming,
        "FORMING BASES — Constructive patterns, wait for trigger",
        FORMING_FILL,
    )
    _write_sheet(
        wb,
        "3_Watchlist_Early",
        watch,
        "WATCHLIST — Early / incomplete signals (not entries)",
        WATCH_FILL,
    )
    _write_sheet(
        wb,
        "4_ETF_Ready",
        ready_etfs,
        "ETF READY TO ENTRY — Corrected ETFs near reversal triggers",
        ETF_FILL,
    )
    _write_sheet(
        wb,
        "5_ETF_Forming",
        forming_etfs + [r for r in watch if r.asset_type == "ETF"],
        "ETF FORMING / WATCH — Not yet ready",
        ETF_FILL,
    )
    _write_sheet(
        wb,
        "6_All_Qualified",
        sorted([r for r in results if r.bucket != "REJECT"], key=lambda x: x.total_score, reverse=True),
        "ALL QUALIFIED (Ready + Forming + Watchlist)",
    )
    _write_methodology_sheet(wb)

    # Ensure Ready sheet is first
    wb.move_sheet("1_Ready_To_Entry", offset=-len(wb.sheetnames) + 1)

    wb.save(out_path)
    return out_path
