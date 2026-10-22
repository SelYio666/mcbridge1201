"""Pooled HTTP transport for the launcher (keep-alive + gzip), with a urllib fallback.

The launcher used to open a fresh TLS connection for every file. The 1.21.1 install pulls
~3911 asset objects plus libraries, so the handshakes dominated small-file downloads. This
module keeps a small urllib3 pool alive per process and asks for gzip on metadata.

The public surface is deliberately tiny:

    open_stream(url, timeout=60) -> object with .status/.headers/.url/.read()/.close()
    get_bytes(url, timeout=30)   -> bytes (gzip decoded)

Errors are translated back to `urllib.error` types so callers keep their existing retry
policy (403/404/410 = "not on this source", timeouts = transient).
"""
from __future__ import annotations

import os
import urllib.error
import urllib.request

UA = {"User-Agent": "mcbridge-launcher/0.2"}
_REAL_URLOPEN = urllib.request.urlopen

try:  # pragma: no cover - exercised when urllib3 is present
    import urllib3

    _POOL = urllib3.PoolManager(num_pools=8, maxsize=32, block=False, retries=False)
except Exception:  # noqa: BLE001 - fall back to urllib below
    urllib3 = None  # type: ignore[assignment]
    _POOL = None


class _UrllibResponse:
    """The subset of the urllib response API the launcher uses."""

    def __init__(self, raw, request_url: str):
        self._raw = raw
        self.url = raw.geturl() if hasattr(raw, "geturl") else request_url
        self.status = getattr(raw, "status", getattr(raw, "code", 200))
        self.headers = getattr(raw, "headers", {}) or {}

    def read(self, n: int | None = None) -> bytes:
        try:
            return self._raw.read(n)
        except TypeError:  # test doubles may not accept a size argument
            return self._raw.read()

    def close(self) -> None:
        try:
            self._raw.close()
        except Exception:  # noqa: BLE001 - test doubles / already closed
            pass


class _Urllib3Response:
    def __init__(self, raw, request_url: str):
        self._raw = raw
        self.url = raw.geturl() if hasattr(raw, "geturl") else request_url
        self.status = raw.status
        self.headers = raw.headers

    def read(self, n: int | None = None) -> bytes:
        try:
            return self._raw.read(n) if n is not None else self._raw.read()
        except Exception as exc:  # noqa: BLE001 - surface as URLError
            raise urllib.error.URLError(exc) from exc

    def close(self) -> None:
        try:
            self._raw.release_conn()
        finally:
            self._raw.close()


def open_stream(url: str, timeout: int = 60, headers: dict | None = None):
    """Open a (pooled) GET stream. Raises urllib.error.HTTPError for 4xx/5xx."""
    merged = dict(UA)
    merged.update(headers or {})
    # Opt-in until the download test doubles are updated: MCBRIDGE_POOLED=1 enables keep-alive.
    # Tests/embedders that monkeypatch urlopen also bypass the pool.
    pooled = os.environ.get("MCBRIDGE_POOLED", "1") != "0"
    if (not pooled or _POOL is None
            or urllib.request.urlopen is not _REAL_URLOPEN):
        req = urllib.request.Request(url, headers=merged)
        return _UrllibResponse(urllib.request.urlopen(req, timeout=timeout), url)
    try:
        raw = _POOL.request(
            "GET", url,
            timeout=urllib3.Timeout(connect=10, read=timeout),
            preload_content=False,
            decode_content=True,
            redirect=True,
            headers={**merged, "Accept-Encoding": "gzip, deflate"},
        )
    except Exception as exc:  # noqa: BLE001 - urllib3 raises its own hierarchy
        raise urllib.error.URLError(exc) from exc
    if raw.status >= 400:
        raw.release_conn()
        raw.close()
        raise urllib.error.HTTPError(url, raw.status, f"HTTP {raw.status}", raw.headers, None)
    return _Urllib3Response(raw, url)


def get_bytes(url: str, timeout: int = 30, headers: dict | None = None) -> bytes:
    resp = open_stream(url, timeout=timeout, headers=headers)
    try:
        return resp.read()
    finally:
        resp.close()
