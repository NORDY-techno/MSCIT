from __future__ import annotations

from decimal import Decimal

from core.models import Holding, PortfolioSnapshot
from core.portfolio import IPortfolioRepository, IPriceProvider
from services.bitget_client import BitgetRestClient

_STABLE = frozenset(
    {"usdt", "usdc", "usd", "busd", "dai", "tusd", "usdp", "pyusd", "fdusd"}
)


def _dec(v: object) -> Decimal:
    if v is None:
        return Decimal("0")
    try:
        return Decimal(str(v))
    except Exception:
        return Decimal("0")


def _ticker_rows(data: object) -> list:
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for k in ("list", "tickers", "items"):
            inner = data.get(k)
            if isinstance(inner, list):
                return inner
    return []


class BitgetSpotPortfolioRepository(IPortfolioRepository):
    def __init__(self, client: BitgetRestClient) -> None:
        self._c = client
        self._snapshots: list[PortfolioSnapshot] = []

    def load_holdings(self) -> list[Holding]:
        raw = self._c.request_json(
            "GET", "/api/v2/spot/account/assets", params={"assetType": "all"}
        )
        data = raw.get("data")
        if not isinstance(data, list):
            return []
        out: list[Holding] = []
        for row in data:
            if not isinstance(row, dict):
                continue
            coin = str(row.get("coin", "")).strip().lower()
            if not coin:
                continue
            amt = _dec(row.get("available")) + _dec(row.get("frozen")) + _dec(row.get("locked"))
            if amt > 0:
                out.append(Holding(coin, amt))
        return out

    def save_snapshot(self, snapshot: PortfolioSnapshot) -> None:
        self._snapshots.append(snapshot)

    @property
    def snapshots(self) -> tuple[PortfolioSnapshot, ...]:
        return tuple(self._snapshots)


class BitgetSpotPriceProvider(IPriceProvider):
    def __init__(self, client: BitgetRestClient) -> None:
        self._c = client
        self._cache: dict[str, Decimal] | None = None

    def get_prices_usd(self, symbols: list[str]) -> dict[str, Decimal]:
        if not symbols:
            return {}
        out: dict[str, Decimal] = {}
        for sym in symbols:
            s = sym.strip().lower()
            if not s:
                continue
            if s in _STABLE:
                out[s] = Decimal("1")
        if not any(sym.strip().lower() not in _STABLE for sym in symbols if sym.strip()):
            return out
        tickers = self._ticker_map()
        for sym in symbols:
            s = sym.strip().lower()
            if not s or s in _STABLE:
                continue
            p = tickers.get(f"{s.upper()}USDT")
            if p is not None:
                out[s] = p
        return out

    def _ticker_map(self) -> dict[str, Decimal]:
        if self._cache is not None:
            return self._cache
        raw = self._c.request_json("GET", "/api/v2/spot/market/tickers")
        data = raw.get("data")
        m: dict[str, Decimal] = {}
        for row in _ticker_rows(data):
            if not isinstance(row, dict):
                continue
            sym = row.get("symbol") or row.get("instId") or row.get("inst_id")
            pair = str(sym or "").strip().upper()
            last = row.get("lastPr") or row.get("last") or row.get("close")
            if pair and last is not None:
                try:
                    m[pair] = Decimal(str(last))
                except Exception:
                    pass
        self._cache = m
        return m

    def clear_cache(self) -> None:
        self._cache = None
