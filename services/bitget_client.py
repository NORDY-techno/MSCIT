from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from typing import Any
from urllib.parse import urlencode

import requests

from logger import get_logger

_log = get_logger(__name__)


def _prehash(ts: str, method: str, path: str, qs: str, body: str) -> str:
    m = method.upper()
    return f"{ts}{m}{path}?{qs}{body}" if qs else f"{ts}{m}{path}{body}"


def _sign(secret: str, msg: str) -> str:
    d = hmac.new(secret.encode("utf-8"), msg.encode("utf-8"), hashlib.sha256).digest()
    return base64.b64encode(d).decode("ascii")


class BitgetAPIError(RuntimeError):
    pass


class BitgetRestClient:
    def __init__(
        self,
        api_key: str,
        secret_key: str,
        passphrase: str,
        base_url: str = "https://api.bitget.com",
        timeout_seconds: float = 15.0,
    ) -> None:
        self._api_key = api_key
        self._secret_key = secret_key
        self._passphrase = passphrase
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout_seconds
        self._session = requests.Session()

    @staticmethod
    def _qs(params: dict[str, Any] | None) -> str:
        if not params:
            return ""
        return urlencode(sorted((k, str(v)) for k, v in params.items() if v is not None))

    def request_json(
        self,
        method: str,
        request_path: str,
        *,
        params: dict[str, Any] | None = None,
        body: dict[str, Any] | None = None,
    ) -> Any:
        m = method.upper()
        qs = self._qs(params)
        body_str = json.dumps(body, separators=(",", ":"), ensure_ascii=False) if body else ""
        ts = str(int(time.time() * 1000))
        sign = _sign(self._secret_key, _prehash(ts, m, request_path, qs, body_str))
        headers = {
            "ACCESS-KEY": self._api_key,
            "ACCESS-SIGN": sign,
            "ACCESS-TIMESTAMP": ts,
            "ACCESS-PASSPHRASE": self._passphrase,
            "Content-Type": "application/json",
            "locale": "en-US",
        }
        url = f"{self._base_url}{request_path}" + (f"?{qs}" if qs else "")
        _log.debug("%s %s", m, request_path)
        if m == "GET":
            r = self._session.get(url, headers=headers, timeout=self._timeout)
        elif m == "POST":
            r = self._session.post(
                url,
                data=body_str.encode("utf-8") if body_str else None,
                headers=headers,
                timeout=self._timeout,
            )
        else:
            raise ValueError(m)
        r.raise_for_status()
        payload = r.json()
        if isinstance(payload, dict):
            c = payload.get("code")
            if c is not None and str(c) != "00000":
                raise BitgetAPIError(f"Bitget code={c}: {payload.get('message', payload)}")
        return payload

    def close(self) -> None:
        self._session.close()
