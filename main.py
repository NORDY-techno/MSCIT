"""Bitget spot-моніторинг: оновлення кожні 30 с (Ctrl+C — вихід)."""

from __future__ import annotations

import sys
import time
from decimal import Decimal
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

from config import get_settings
from core.portfolio import DefaultPortfolioApplication
from core.tracker import PortfolioTracker, format_coin_amount, quantize_usd
from logger import get_logger, setup_logging
from services.bitget_client import BitgetAPIError, BitgetRestClient
from services.bitget_spot import BitgetSpotPortfolioRepository, BitgetSpotPriceProvider
from services.telegram_notify import send_portfolio_telegram, send_telegram_plain

POLL_SEC = 5 * 60
BALANCE_CHANGE_THRESHOLD = Decimal("0.001")


def _log(log, snap, visible) -> None:
    log.info(
        "Портфель ~ %s USDT; позиції > $1: %s",
        quantize_usd(snap.total_value_usd),
        len(visible),
    )
    for r in visible:
        h = r.holding
        log.info(
            "  %s: %s @ %s → ~%s",
            h.symbol,
            format_coin_amount(h.amount),
            r.price_usd,
            r.value_usd,
        )


def main() -> None:
    s = get_settings()
    setup_logging(s.log_level, Path("logs") / "app.log")
    log = get_logger(__name__)
    if not s.bitget_credentials_complete():
        log.error("Заповніть BITGET_API_KEY, BITGET_API_SECRET, BITGET_API_PASSPHRASE у .env")
        sys.exit(1)

    c = BitgetRestClient(s.bitget_api_key, s.bitget_api_secret, s.bitget_api_passphrase, s.bitget_base_url)
    prices = BitgetSpotPriceProvider(c)
    app = DefaultPortfolioApplication(prices, BitgetSpotPortfolioRepository(c))
    tr = PortfolioTracker()
    log.info("Інтервал %s с, Ctrl+C — стоп.", POLL_SEC)
    if s.telegram_enabled():
        log.info("Telegram: надсилання тільки при зміні балансу > 0.1%%")
        try:
            assert s.telegram_token and s.telegram_chat_id
            send_telegram_plain(
                s.telegram_token,
                s.telegram_chat_id,
                "MSCIT: старт моніторингу — тестове повідомлення OK.",
            )
            log.info("Telegram: тест на старті відправлено.")
        except Exception as exc:
            log.warning("Telegram (старт): %s", exc)

    previous_total_value: Decimal | None = None

    try:
        while True:
            try:
                prices.clear_cache()
                snap = app.run()
            except BitgetAPIError as e:
                log.error("%s", e)
            except KeyboardInterrupt:
                log.info("Зупинка.")
                break
            else:
                _log(log, snap, tr.significant_holdings(snap))
                if s.telegram_enabled():
                    if previous_total_value is None:
                        previous_total_value = snap.total_value_usd
                    else:
                        if previous_total_value == 0:
                            changed = snap.total_value_usd != 0
                        else:
                            changed = (
                                abs(snap.total_value_usd - previous_total_value)
                                / previous_total_value
                            ) >= BALANCE_CHANGE_THRESHOLD

                        if changed:
                            try:
                                assert s.telegram_token and s.telegram_chat_id
                                send_portfolio_telegram(
                                    s.telegram_token,
                                    s.telegram_chat_id,
                                    snap,
                                )
                            except Exception as exc:
                                log.warning("Telegram: %s", exc)
                        previous_total_value = snap.total_value_usd
            try:
                time.sleep(POLL_SEC)
            except KeyboardInterrupt:
                log.info("Зупинка.")
                break
    finally:
        c.close()


if __name__ == "__main__":
    main()
