"""Shared pattern result type."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class PatternHit:
    name: str
    score: float                 # 0-100 pattern confidence
    pivot: float | None          # breakout / neckline / resistance to reclaim
    support: float | None        # structural stop reference
    status: str                  # FORMING | NEAR_ENTRY | BREAKOUT | FAILED
    notes: str = ""
    extras: dict[str, Any] = field(default_factory=dict)
