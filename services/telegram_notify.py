from __future__ import annotations

import html
from typing import Iterable

import requests

from core.models import PortfolioSnapshot
from core.tracker import format_coin_amount, quantize_usd

_TELEGRAM_URL = "https://api.telegram.org/bot{token}/sendMessage"


def send_telegram_plain(token: str, chat_id: str, text: str) -> None:
    """Простий текст без HTML — зручно для тесту та діагностики."""
    r = requests.post(
        _TELEGRAM_URL.format(token=token),
        json={"chat_id": chat_id, "text": text},
        timeout=30,
    )
    r.raise_for_status()
    body = r.json()
    if not body.get("ok"):
        raise RuntimeError(body)


# Ліміт повідомлення Telegram 4096; залишаємо запас під <pre>…</pre>
_MAX = 3500


def portfolio_table_text(snap: PortfolioSnapshot) -> str:
    head = ("монета", "баланс", "ціна", "USDT")
    rows_data: list[tuple[str, str, str, str]] = []
    for h in snap.holdings:
        p = snap.prices.get(h.symbol)
        if p is not None:
            rows_data.append(
                (
                    h.symbol,
                    format_coin_amount(h.amount),
                    str(p),
                    str(quantize_usd(h.amount * p)),
                ),
            )
        else:
            rows_data.append((h.symbol, format_coin_amount(h.amount), "—", "—"))
    rows: list[tuple[str, str, str, str]] = [head] + rows_data
    w = [max(len(rows[r][c]) for r in range(len(rows))) for c in range(4)]
    sep = "-" * (sum(w) + 9)
    out = [
        f"Bitget spot  {snap.captured_at:%Y-%m-%d %H:%M} UTC",
        f"Σ {quantize_usd(snap.total_value_usd)} USDT",
        "",
        f"{head[0]:<{w[0]}}  {head[1]:>{w[1]}}  {head[2]:>{w[2]}}  {head[3]:>{w[3]}}",
        sep,
    ]
    for sym, amt, px, vl in rows_data:
        out.append(f"{sym:<{w[0]}}  {amt:>{w[1]}}  {px:>{w[2]}}  {vl:>{w[3]}}")
    return "\n".join(out)


def _split_message(text: str) -> Iterable[str]:
    if len(text) <= _MAX:
        yield text
        return
    buf: list[str] = []
    n = 0
    for line in text.split("\n"):
        if n + len(line) + 1 > _MAX and buf:
            yield "\n".join(buf)
            buf = []
            n = 0
        buf.append(line)
        n += len(line) + 1
    if buf:
        yield "\n".join(buf)


def send_portfolio_telegram(token: str, chat_id: str, snap: PortfolioSnapshot) -> None:
    plain = portfolio_table_text(snap)
    for part in _split_message(plain):
        wrapped = f"<pre>{html.escape(part)}</pre>"
        r = requests.post(
            _TELEGRAM_URL.format(token=token),
            json={"chat_id": chat_id, "text": wrapped, "parse_mode": "HTML"},
            timeout=30,
        )
        r.raise_for_status()
        body = r.json()
        if not body.get("ok"):
            raise RuntimeError(body)
