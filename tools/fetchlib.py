"""Small, dependency-free HTTP/hash helper used by the P0 tooling.

Only Python's standard library is used because the host's PowerShell/git TLS
stack (schannel) is unusable in this sandbox; Python's OpenSSL stack works.
Every download records URL, size, SHA-256 and timestamp so manifests stay
reproducible.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

UA = "mcbridge1201-p0/0.1 (+local research; contact: local)"


class FetchError(RuntimeError):
    pass


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def http_get(url: str, timeout: int = 60, retries: int = 3, headers: dict | None = None) -> bytes:
    last = None
    for attempt in range(1, retries + 1):
        req = urllib.request.Request(url, headers={"User-Agent": UA, **(headers or {})})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            body = b""
            try:
                body = e.read()[:400]
            except Exception:
                pass
            last = FetchError(f"HTTP {e.code} for {url}: {body!r}")
            # 4xx other than 429 will not improve on retry
            if e.code not in (408, 429) and 400 <= e.code < 500:
                raise last
        except Exception as e:  # URLError, timeout, reset
            last = FetchError(f"{type(e).__name__} for {url}: {e}")
        time.sleep(min(2 ** attempt * 0.5, 8))
    raise last  # type: ignore[misc]


def http_json(url: str, **kw) -> dict:
    return json.loads(http_get(url, **kw).decode("utf-8"))


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def download(url: str, dest: str, expected_sha256: str | None = None,
             timeout: int = 120, retries: int = 3) -> dict:
    """Download to `dest` atomically; verify size/hash; return a provenance record."""
    os.makedirs(os.path.dirname(dest) or ".", exist_ok=True)
    if os.path.exists(dest):
        digest = sha256_file(dest)
        if expected_sha256 is None or digest.lower() == expected_sha256.lower():
            return {
                "url": url,
                "path": dest,
                "size": os.path.getsize(dest),
                "sha256": digest,
                "fetchedAt": now_iso(),
                "cached": True,
            }
        raise FetchError(f"cached file hash mismatch for {dest}: {digest} != {expected_sha256}")

    data = http_get(url, timeout=timeout, retries=retries)
    tmp = dest + ".part"
    with open(tmp, "wb") as f:
        f.write(data)
    digest = sha256_file(tmp)
    if expected_sha256 is not None and digest.lower() != expected_sha256.lower():
        os.unlink(tmp)
        raise FetchError(f"hash mismatch for {url}: {digest} != {expected_sha256}")
    os.replace(tmp, dest)
    return {
        "url": url,
        "path": dest,
        "size": os.path.getsize(dest),
        "sha256": digest,
        "fetchedAt": now_iso(),
        "cached": False,
    }


def write_json(path: str, obj) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2, sort_keys=False)
        f.write("\n")
    os.replace(tmp, path)


def read_json(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
