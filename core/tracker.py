>from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from core.models import Holding, PortfolioSnapshot

_USD_CENT = Decimal("0.01")


def quantize_usd(amount: Decimal) -> Decimal:
    return amount.quantize(_USD_CENT, rounding=ROUND_HALF_UP)


def format_coin_amount(amount: Decimal, decimals: int = 4) -> str:
    """Округлення балансу монети для виводу (напр. 4.2990)."""
    step = Decimal(10) ** -decimals
    q = amount.quantize(step, rounding=ROUND_HALF_UP)
    return format(q, "f")


@dataclass(frozen=True, slots=True)
class SignificantHolding:
    holding: Holding
    price_usd: Decimal
    value_usd: Decimal


class PortfolioTracker:
    def __init__(self, min_value_usd: Decimal = Decimal("1")) -> None:
        self._min = min_value_usd

    def significant_holdings(self, snapshot: PortfolioSnapshot) -> tuple[SignificantHolding, ...]:
        out: list[SignificantHolding] = []
        for h in snapshot.holdings:
            price = snapshot.prices.get(h.symbol)
            if price is None:
                continue
            value = h.amount * price
            if value > self._min:
                out.append(
                    SignificantHolding(h, price, quantize_usd(value)),
                )
        return tuple(out)
