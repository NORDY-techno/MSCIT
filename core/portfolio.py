from __future__ import annotations

from abc import ABC, abstractmethod
from decimal import Decimal

from core.models import Holding, PortfolioSnapshot


class IPriceProvider(ABC):
    @abstractmethod
    def get_prices_usd(self, symbols: list[str]) -> dict[str, Decimal]:
        ...


class IPortfolioRepository(ABC):
    @abstractmethod
    def load_holdings(self) -> list[Holding]:
        ...

    @abstractmethod
    def save_snapshot(self, snapshot: PortfolioSnapshot) -> None:
        ...


class BasePortfolioApplication(ABC):
    def __init__(
        self,
        price_provider: IPriceProvider,
        repository: IPortfolioRepository,
    ) -> None:
        self._prices = price_provider
        self._repo = repository

    @abstractmethod
    def run(self) -> PortfolioSnapshot:
        ...


class DefaultPortfolioApplication(BasePortfolioApplication):
    def run(self) -> PortfolioSnapshot:
        holdings = self._repo.load_holdings()
        if not holdings:
            snap = PortfolioSnapshot(Decimal("0"), {}, tuple())
            self._repo.save_snapshot(snap)
            return snap
        prices = self._prices.get_prices_usd([h.symbol for h in holdings])
        total = Decimal("0")
        for h in holdings:
            p = prices.get(h.symbol)
            if p is not None:
                total += h.amount * p
        snap = PortfolioSnapshot(total, prices, tuple(holdings))
        self._repo.save_snapshot(snap)
        return snap
