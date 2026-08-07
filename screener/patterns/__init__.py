"""Pattern detection package for bottom / base / reversal structures."""

from screener.patterns.base_common import PatternHit
from screener.patterns.rounded_bottom import detect_rounded_bottom
from screener.patterns.vcp import detect_vcp_contraction
from screener.patterns.double_bottom import detect_double_bottom
from screener.patterns.trendline import detect_descending_trendline_break
from screener.patterns.support_zone import detect_support_zone_reversal
from screener.patterns.spring import detect_wyckoff_spring

__all__ = [
    "PatternHit",
    "detect_rounded_bottom",
    "detect_vcp_contraction",
    "detect_double_bottom",
    "detect_descending_trendline_break",
    "detect_support_zone_reversal",
    "detect_wyckoff_spring",
]
