"""Перевірка TELEGRAM_TOKEN і TELEGRAM_CHAT_ID (без виводу секретів)."""
from __future__ import annotations

import re
import sys
from pathlib import Path

import requests

from config import dotenv_path, get_settings


def main() -> None:
    p = dotenv_path()
    if p is None:
        print("FAIL: не знайдено файл .env")
        print(f"  має бути: {Path(__file__).resolve().parent / '.env'}")
        print("  або в теці, звідки запускаєте python (поточна тека).")
        sys.exit(1)
    print(f"OK: .env знайдено: {p}")

    s = get_settings()
    token = s.telegram_token or ""
    chat = s.telegram_chat_id or ""

    if not token:
        print("FAIL: TELEGRAM_TOKEN порожній (перевірте рядок у .env без пробілів до/після =)")
        sys.exit(1)
    if not chat:
        print("FAIL: TELEGRAM_CHAT_ID порожній")
        sys.exit(1)

    if " " in token or len(token) < 40:
        print("FAIL: TELEGRAM_TOKEN схоже некоректний (пробіли або надто короткий)")
        sys.exit(1)
    if not re.match(r"^\d+:[A-Za-z0-9_-]+$", token):
        print("FAIL: TELEGRAM_TOKEN не у форматі <числа>:<рядок>")
        sys.exit(1)
    print("OK: формат TELEGRAM_TOKEN")

    if not re.match(r"^-?\d+$", chat):
        print("FAIL: TELEGRAM_CHAT_ID має бути числом (для супергруп часто -100...)")
        sys.exit(1)
    print("OK: формат TELEGRAM_CHAT_ID")

    r = requests.get(f"https://api.telegram.org/bot{token}/getMe", timeout=15)
    j = r.json()
    if not j.get("ok"):
        print("FAIL: getMe", j)
        sys.exit(1)
    res = j["result"]
    print(f"OK: getMe — бот @{res.get('username', '?')} (id {res.get('id')})")

    r2 = requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={
            "chat_id": chat,
            "text": "MSCIT: тест OK — token і chat_id підходять.",
        },
        timeout=15,
    )
    j2 = r2.json()
    if not j2.get("ok"):
        print("FAIL: sendMessage", j2)
        print(
            "Підказки: у приватний чат — напишіть боту /start; "
            "у групі — додайте бота."
        )
        sys.exit(1)
    print("OK: sendMessage — перевірте Telegram.")


if __name__ == "__main__":
    main()
