from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class Holding:
    symbol: str
    amount: Decimal


@dataclass(frozen=True, slots=True)
class PortfolioSnapshot:
    total_value_usd: Decimal
    prices: dict[str, Decimal]
    holdings: tuple[Holding, ...]
    captured_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
