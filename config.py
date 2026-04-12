from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


def dotenv_path() -> Path | None:
    """Перший наявний .env: каталог проєкту, потім поточна тека запуску."""
    root = Path(__file__).resolve().parent
    for p in (root / ".env", Path.cwd() / ".env"):
        if p.is_file():
            return p
    return None


def _parse_env_raw(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        k, _, rest = s.partition("=")
        k = k.strip()
        v = rest.strip()
        if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
            v = v[1:-1]
        if k:
            out[k] = v
    return out


def _file_env() -> dict[str, str]:
    p = dotenv_path()
    if not p:
        return {}
    try:
        raw = p.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        raw = p.read_text(encoding="utf-16")
    return _parse_env_raw(raw)


@dataclass(frozen=True)
class Settings:
    bitget_api_key: str | None
    bitget_api_secret: str | None
    bitget_api_passphrase: str | None
    bitget_base_url: str
    log_level: str
    telegram_token: str | None
    telegram_chat_id: str | None

    def bitget_credentials_complete(self) -> bool:
        return bool(self.bitget_api_key and self.bitget_api_secret and self.bitget_api_passphrase)

    def telegram_enabled(self) -> bool:
        return bool(self.telegram_token and self.telegram_chat_id)


def get_settings() -> Settings:
    path = dotenv_path()
    disk = _file_env()
    if path:
        load_dotenv(path, override=True)

    def pick(key: str, default: str = "") -> str:
        ev = os.getenv(key)
        if ev is not None and ev.strip():
            return ev.strip()
        return (disk.get(key) or default).strip()

    def opt(key: str) -> str | None:
        v = pick(key)
        return v if v else None

    return Settings(
        bitget_api_key=opt("BITGET_API_KEY"),
        bitget_api_secret=opt("BITGET_API_SECRET"),
        bitget_api_passphrase=opt("BITGET_API_PASSPHRASE"),
        bitget_base_url=pick("BITGET_BASE_URL", "https://api.bitget.com").rstrip("/"),
        log_level=pick("LOG_LEVEL", "INFO").upper(),
        telegram_token=opt("TELEGRAM_TOKEN"),
        telegram_chat_id=opt("TELEGRAM_CHAT_ID"),
    )
