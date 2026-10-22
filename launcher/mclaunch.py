#!/usr/bin/env python3
"""mcbridge launcher core: install Minecraft versions from official sources and launch offline.

Design rules:
- never bundle game files; everything is downloaded from Mojang / Fabric / Forge / NeoForge meta;
- offline mode only: singleplayer and LAN, no Mojang authentication;
- one game root (like .minecraft), shared libraries/assets, per-version folders.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

import fetch as _fetch
import uuid
import zipfile
from collections import deque
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, as_completed, wait
from pathlib import Path

UA = {"User-Agent": "mcbridge-launcher/0.1 (offline, local)"}
MANIFEST_URL = "https://piston-meta.mojang.com/mc/game/version_manifest_v2.json"
FABRIC_META = "https://meta.fabricmc.net/v2"
FORGE_PROMOS = "https://files.minecraftforge.net/net/minecraftforge/forge/promotions_slim.json"
NEOFORGE_VERSIONS = "https://maven.neoforged.net/api/maven/versions/releases/net/neoforged/neoforge"
ASSET_BASE = "https://resources.download.minecraft.net"
JAVA_FALLBACK = r"C:\Program Files\Java\jdk-21\bin\java.exe"


class Progress:
    def __init__(self):
        self.phase = "idle"
        self.total = 0
        self.done = 0
        self.message = ""
        self.error = None
        self.bytes_done = 0
        self.bytes_total = 0
        self.speed = 0.0
        self.source = ""
        self._last_t = time.time()
        self._last_b = 0
        self.lock = threading.Lock()

    def set(self, phase=None, message=None, total=None, done=None, error=None, source=None):
        with self.lock:
            if phase is not None:
                self.phase = phase
            if message is not None:
                self.message = message
            if total is not None:
                self.total = total
            if done is not None:
                self.done = done
            if error is not None:
                self.error = error
            if source is not None:
                self.source = source

    def inc(self):
        with self.lock:
            self.done += 1

    def add_bytes(self, n: int, total: int | None = None, source: str | None = None) -> None:
        """Account streamed bytes and a smoothed transfer speed (bytes/s)."""
        with self.lock:
            self.bytes_done += n
            if total:
                self.bytes_total = total
            if source:
                self.source = source
            now = time.time()
            dt = now - self._last_t
            if dt >= 0.5:
                instant = (self.bytes_done - self._last_b) / dt
                self.speed = instant if self.speed <= 0 else self.speed * 0.6 + instant * 0.4
                self._last_t = now
                self._last_b = self.bytes_done

    def snapshot(self):
        with self.lock:
            return {"phase": self.phase, "total": self.total, "done": self.done,
                    "message": self.message, "error": self.error,
                    "bytes_done": self.bytes_done, "bytes_total": self.bytes_total,
                    "speed": round(self.speed, 1), "source": self.source}


_JSON_CACHE: dict[str, tuple[float, bytes]] = {}
_SIDECAR_CACHE: dict[str, tuple[float, str]] = {}
METADATA_TTL = 900  # 15 minutes, per the download review: listings rarely change that fast


def _fetch_json(candidate: str, timeout: int) -> bytes:
    return _fetch.get_bytes(candidate, timeout=timeout)


def http_json(url: str, retries: int = 1, timeout: int = 20, max_age: int = METADATA_TTL,
              hedge_delay: float = 3.0):
    """Fetch JSON metadata with a hedged request over the verified candidates.

    The 2026-10-21 benchmark (runs/p117) showed a flaky meta host burning 61.9 s
    before the mirror was tried at all, and a plain short timeout then failed when
    both hosts stalled. So: start the official request, and if it has not answered
    after `hedge_delay` seconds, start the mirror too; the first valid JSON wins.
    Successful responses are cached in-process for `max_age` seconds (0 = bypass);
    raw bytes are re-parsed per call so callers may mutate the returned dict.
    """
    if max_age > 0:
        cached = _JSON_CACHE.get(url)
        if cached and time.time() - cached[0] < max_age:
            try:
                return json.loads(cached[1])
            except Exception:  # noqa: BLE001 - never serve a broken cache entry
                _JSON_CACHE.pop(url, None)

    candidates = ordered_candidates(url)
    last: Exception | None = None

    def store(raw: bytes):
        if max_age > 0:
            _JSON_CACHE[url] = (time.time(), raw)

    def failed_health(exc: Exception, candidate: str) -> None:
        if isinstance(exc, urllib.error.HTTPError) and exc.code in (403, 404, 410):
            return
        _record_health(candidate, False)

    if len(candidates) == 1:
        for attempt in range(max(1, retries)):
            try:
                raw = _fetch_json(candidates[0], timeout)
                data = json.loads(raw)
                store(raw)
                _record_health(candidates[0], True)
                return data
            except Exception as exc:  # noqa: BLE001
                last = exc
                failed_health(exc, candidates[0])
                time.sleep(1.0 + attempt)
        raise RuntimeError(f"GET {url} failed: {last}")

    pool = ThreadPoolExecutor(max_workers=len(candidates))
    pending: dict = {}
    started = 0
    last = None

    def start_next() -> None:
        nonlocal started
        candidate = candidates[started]
        pending[pool.submit(_fetch_json, candidate, timeout)] = candidate
        started += 1

    try:
        start_next()
        deadline = time.time() + hedge_delay
        while pending or started < len(candidates):
            if not pending:
                start_next()
                deadline = time.time() + hedge_delay
                continue
            wait_for = 0.5
            if started < len(candidates):
                wait_for = max(0.05, min(0.5, deadline - time.time()))
            done, _ = wait(set(pending), timeout=wait_for, return_when=FIRST_COMPLETED)
            for fut in done:
                source = pending.pop(fut)
                try:
                    raw = fut.result()
                    data = json.loads(raw)
                    store(raw)
                    _record_health(source, True)
                    return data
                except Exception as exc:  # noqa: BLE001
                    last = exc
                    failed_health(exc, source)
            if time.time() >= deadline and started < len(candidates):
                start_next()
                deadline = float("inf")
        raise RuntimeError(f"GET {url} failed: {last}")
    finally:
        pool.shutdown(wait=False, cancel_futures=True)


def sha1_of(path: Path) -> str:
    h = hashlib.sha1()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


MIRRORS: list[tuple[str, list[str]]] = [
    ("https://resources.download.minecraft.net/", ["https://bmclapi2.bangbang93.com/assets/"]),
    ("https://libraries.minecraft.net/", ["https://bmclapi2.bangbang93.com/maven/"]),
    ("https://piston-data.mojang.com/", ["https://bmclapi2.bangbang93.com/"]),
    ("https://piston-meta.mojang.com/", ["https://bmclapi2.bangbang93.com/"]),
    ("https://launchermeta.mojang.com/", ["https://bmclapi2.bangbang93.com/"]),
    ("https://meta.fabricmc.net/v2/", ["https://bmclapi2.bangbang93.com/fabric-meta/v2/"]),
    # Verified 2026-10-21: the BMCL maven proxy serves fabric-loader jars (HTTP 200, full file).
    # fabric-api is still 404 there, so the mapping is path-scoped: do not blanket-replace
    # maven.fabricmc.net (that would turn working URLs into 404s).
    ("https://maven.fabricmc.net/net/fabricmc/fabric-loader/",
     ["https://bmclapi2.bangbang93.com/maven/net/fabricmc/fabric-loader/"]),
    # Verified 2026-10-22 by tools/check_download_sources.py: BMCL's maven proxy serves
    # intermediary too (206 range). fabric-api is still 404 there, so it stays official.
    ("https://maven.fabricmc.net/net/fabricmc/intermediary/",
     ["https://bmclapi2.bangbang93.com/maven/net/fabricmc/intermediary/"]),
]


def mirror_urls(url: str) -> list[str]:
    """Official URL first, then only the mirrors verified for that exact path prefix."""
    mirrors = []
    for official, candidates in MIRRORS:
        if url.startswith(official):
            for prefix in candidates:
                mirrors.append(prefix + url[len(official):])
    return [url] + mirrors


SOURCE_MODES = ("auto", "official", "mirror")
SOURCE_MODE = "auto"  # "auto" = official first; "official" = no mirrors; "mirror" = mirrors first
SOURCE_HEALTH: dict[str, dict] = {}
SOURCE_HEALTH_PATH: Path | None = None
_HEALTH_LOCK = threading.Lock()
HEALTH_TTL = 600  # a host with >=2 recent failures is deprioritised for 10 minutes


def set_source_mode(mode: str | None) -> str:
    global SOURCE_MODE
    mode = (mode or "auto").strip().lower()
    SOURCE_MODE = mode if mode in SOURCE_MODES else "auto"
    return SOURCE_MODE


def load_source_health(path: Path) -> int:
    """Load the persisted host health map (best effort; a broken file is ignored)."""
    global SOURCE_HEALTH_PATH
    SOURCE_HEALTH_PATH = Path(path)
    try:
        data = json.loads(SOURCE_HEALTH_PATH.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            with _HEALTH_LOCK:
                SOURCE_HEALTH.clear()
                SOURCE_HEALTH.update({str(k): v for k, v in data.items() if isinstance(v, dict)})
            return len(SOURCE_HEALTH)
    except Exception:  # noqa: BLE001 - missing/corrupt cache is fine
        pass
    return 0


def save_source_health() -> None:
    if SOURCE_HEALTH_PATH is None:
        return
    try:
        SOURCE_HEALTH_PATH.parent.mkdir(parents=True, exist_ok=True)
        with _HEALTH_LOCK:
            snapshot = {k: dict(v) for k, v in SOURCE_HEALTH.items()}
        SOURCE_HEALTH_PATH.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")
    except OSError:
        pass


def merge_source_health(entries: dict) -> None:
    """Apply external health observations (e.g. a canary run) to the persisted map."""
    if not isinstance(entries, dict):
        return
    changed = False
    with _HEALTH_LOCK:
        for host, info in entries.items():
            if not isinstance(info, dict):
                continue
            host = str(host).lower()
            cur = SOURCE_HEALTH.setdefault(host, {"fails": 0})
            if info.get("ok"):
                cur["fails"] = 0
                cur["last_ok"] = time.time()
            else:
                cur["fails"] = int(cur.get("fails", 0)) + 1
                cur["last_fail"] = time.time()
            changed = True
    if changed:
        save_source_health()


def _host(url: str) -> str:
    return urllib.parse.urlsplit(url).netloc.lower()


def _record_health(url: str, ok: bool) -> None:
    host = _host(url)
    if not host:
        return
    changed = False
    with _HEALTH_LOCK:
        entry = SOURCE_HEALTH.setdefault(host, {"fails": 0})
        if ok:
            if entry.get("fails", 0) or "last_ok" not in entry:
                entry["fails"] = 0
                entry["last_ok"] = time.time()
                changed = True
        else:
            entry["fails"] = int(entry.get("fails", 0)) + 1
            entry["last_fail"] = time.time()
            changed = True
    # persist failures and recoveries, not every successful asset
    if changed:
        save_source_health()


def _health_rank(url: str) -> int:
    with _HEALTH_LOCK:
        entry = SOURCE_HEALTH.get(_host(url))
        if not entry:
            return 1  # unknown: keep after known-good, before known-bad
        if int(entry.get("fails", 0)) >= 2 and time.time() - float(entry.get("last_fail", 0)) < HEALTH_TTL:
            return 2  # recently failing
        return 0  # recently healthy


def ordered_candidates(url: str) -> list[str]:
    """Candidate order for the current source mode, with recent-failure hosts last."""
    candidates = mirror_urls(url)
    if SOURCE_MODE == "official":
        return [url]
    if SOURCE_MODE == "mirror":
        candidates = candidates[1:] + [url]
    # stable sort: healthy/unknown keep their mode order, recently failing go last
    ranked = sorted(enumerate(candidates), key=lambda pair: (_health_rank(pair[1]), pair[0]))
    return [c for _i, c in ranked]


DOWNLOAD_EVENTS: deque = deque(maxlen=5000)  # a full vanilla install is ~3,900 assets + libs
_DOWNLOAD_LOCK = threading.Lock()
_DOWNLOAD_SEQ = 0


def _record_download(**event) -> None:
    global _DOWNLOAD_SEQ
    event["time"] = time.strftime("%Y-%m-%d %H:%M:%S")
    with _DOWNLOAD_LOCK:
        _DOWNLOAD_SEQ += 1
        event["seq"] = _DOWNLOAD_SEQ
        DOWNLOAD_EVENTS.append(event)


def download(url: str, dest: Path, sha1: str | None = None, retries: int = 3,
             progress: Progress | None = None) -> str:
    """Download a file, trying verified mirrors; returns the URL that actually served it.

    Retries are per candidate and only for transient problems (timeout, TLS, 5xx).
    HTTP 403/404/410 mean "not on this source" and move on immediately; a checksum
    mismatch is retried on the same source before moving on. The final URL and the
    failure reason of every attempt are recorded in DOWNLOAD_EVENTS so the launcher
    can show where a file really came from. When a Progress is given, streamed bytes
    and the current source are reported to it (no fake remaining-time estimates).
    """
    dest = Path(dest)
    if dest.exists() and (sha1 is None or sha1_of(dest) == sha1):
        return url
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    last = None
    for candidate in ordered_candidates(url):
        is_mirror = candidate != url
        for attempt in range(1, max(1, retries) + 1):
            try:
                progress and progress.set(source=candidate)
                resp = _fetch.open_stream(candidate, timeout=60)
                digest = hashlib.sha1() if sha1 else None
                try:
                    final_url = resp.url or candidate
                    headers = resp.headers or {}
                    total = None
                    try:
                        total = int(headers.get("Content-Length") or 0) or None
                    except (TypeError, ValueError):
                        total = None
                    with tmp.open("wb") as f:
                        while True:
                            chunk = resp.read(1 << 20)
                            if not chunk:
                                break
                            f.write(chunk)
                            if digest is not None:
                                digest.update(chunk)
                            progress and progress.add_bytes(len(chunk), total=total,
                                                            source=final_url or candidate)
                finally:
                    resp.close()
                size = tmp.stat().st_size
                if sha1 and (digest.hexdigest() if digest else sha1_of(tmp)) != sha1:
                    tmp.unlink(missing_ok=True)
                    raise RuntimeError("sha1 mismatch")
                tmp.replace(dest)
                _record_health(candidate, True)
                _record_download(file=dest.name, url=candidate, final=final_url,
                                 mirror=is_mirror, redirected=final_url != candidate,
                                 bytes=size, attempts=attempt, error=None)
                return final_url
            except urllib.error.HTTPError as exc:  # noqa: PERF203 - per-source policy
                tmp.unlink(missing_ok=True)
                last = exc
                if exc.code not in (403, 404, 410):
                    _record_health(candidate, False)
                _record_download(file=dest.name, url=candidate, mirror=is_mirror,
                                 bytes=0, attempts=attempt, error=f"http {exc.code}")
                if exc.code in (403, 404, 410):
                    break
                time.sleep(1.5 * attempt)
            except Exception as exc:  # noqa: BLE001 - timeout/TLS/sha1/disk
                tmp.unlink(missing_ok=True)
                last = exc
                _record_health(candidate, False)
                _record_download(file=dest.name, url=candidate, mirror=is_mirror,
                                 bytes=0, attempts=attempt, error=str(exc)[:160])
                time.sleep(1.5 * attempt)
    tmp.unlink(missing_ok=True)
    raise RuntimeError(f"download {url} failed: {last}")


def sha1_sidecar(url: str, timeout: int = 6) -> str | None:
    """Fetch a maven artifact's `.sha1` sidecar, if the repository publishes one."""
    cached = _SIDECAR_CACHE.get(url)
    if cached and time.time() - cached[0] < METADATA_TTL:
        return cached[1]
    candidates = [url + ".sha1"]
    if url.startswith("https://maven.fabricmc.net/"):
        candidates.append(
            "https://bmclapi2.bangbang93.com/maven/" + url[len("https://maven.fabricmc.net/"):] + ".sha1")
    for candidate in candidates:
        try:
            req = urllib.request.Request(candidate, headers=UA)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                text = r.read().decode("ascii", "ignore").strip().split()
            if text and len(text[0]) == 40 and all(c in "0123456789abcdefABCDEF" for c in text[0]):
                digest = text[0].lower()
                _SIDECAR_CACHE[url] = (time.time(), digest)
                return digest
        except Exception:  # noqa: BLE001 - sidecar is best-effort
            continue
    return None


def download_maven(url: str, dest: Path, retries: int = 3,
                   progress: Progress | None = None) -> str:
    """Download a maven artifact and verify it against the repository's sha1 sidecar.

    The digest is remembered in a `<jar>.sha1` file next to the artifact, so a cached
    install does not re-fetch every sidecar over the network (the review's hot-path
    latency: 8 fabric libraries used to mean 8 extra maven requests).
    """
    dest = Path(dest)
    sidecar = dest.with_suffix(dest.suffix + ".sha1")
    local = dest.with_suffix(dest.suffix + ".local.sha1")
    digest = None
    for candidate in (sidecar, local):
        if digest is not None or not candidate.exists():
            continue
        try:
            parts = candidate.read_text(encoding="ascii", errors="ignore").strip().split()
            if parts and len(parts[0]) == 40 and all(c in "0123456789abcdefABCDEF" for c in parts[0]):
                digest = parts[0].lower()
        except OSError:
            digest = None
    if digest is None:
        digest = sha1_sidecar(url)
        if digest:
            try:
                sidecar.write_text(digest + "\n", encoding="ascii")
            except OSError:
                pass
    final = download(url, dest, digest, retries=retries, progress=progress)
    if digest is None and dest.exists():
        # no repository sidecar available: remember our own digest so the next run can
        # stay offline (this is an integrity check, not proof of upstream authenticity)
        try:
            local.write_text(sha1_of(dest) + "\n", encoding="ascii")
        except OSError:
            pass
    return final


def eval_rules(rules, features=None) -> bool:
    """Evaluate Mojang rule lists for Windows with an empty feature set."""
    if not rules:
        return True
    features = features or {}
    ok = False
    for rule in rules:
        applies = True
        os_name = (rule.get("os") or {}).get("name")
        if os_name and os_name != "windows":
            applies = False
        feats = rule.get("features")
        if feats:
            for key, want in feats.items():
                if bool(features.get(key, False)) != bool(want):
                    applies = False
        if applies:
            ok = rule.get("action") == "allow"
    return ok


def allowed_win(lib: dict) -> bool:
    return eval_rules(lib.get("rules"))


def version_manifest():
    data = http_json(MANIFEST_URL)
    return data["versions"], data["latest"]


def find_version(version_id: str):
    versions, _ = version_manifest()
    for v in versions:
        if v["id"] == version_id:
            return v
    raise RuntimeError(f"unknown version {version_id}")



def ensure_profile(version_id: str, root: Path, name: str | None = None) -> None:
    """Write a launcher_profiles.json entry so other launchers list this version."""
    import json as _json
    import time as _time

    root = Path(root)
    path = root / "launcher_profiles.json"
    data = {}
    if path.exists():
        try:
            data = _json.loads(path.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            data = {}
    profiles = data.setdefault("profiles", {})
    if version_id not in profiles:
        now = _time.strftime("%Y-%m-%dT%H:%M:%S.000Z", _time.gmtime())
        profiles[version_id] = {
            "name": name or version_id,
            "type": "custom",
            "created": now,
            "lastUsed": now,
            "icon": "Furnace",
            "lastVersionId": version_id,
            "gameDir": str(root),
        }
        data.setdefault("settings", {})
        data.setdefault("version", 3)
        path.write_text(_json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def install_vanilla(mc: str, root: Path, progress: Progress | None = None) -> str:
    root = Path(root)
    v = find_version(mc)
    progress and progress.set(phase="download", message=f"version json {mc}")
    meta = http_json(v["url"])
    vdir = root / "versions" / mc
    vdir.mkdir(parents=True, exist_ok=True)
    (vdir / f"{mc}.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")

    # client jar
    jar = meta.get("downloads", {}).get("client")
    if jar:
        progress and progress.set(message="client jar")
        download(jar["url"], vdir / f"{mc}.jar", jar.get("sha1"), progress=progress)

    # libraries + natives
    libs = [lib for lib in meta.get("libraries", []) if allowed_win(lib)]
    natives_dir = vdir / "natives"
    natives_dir.mkdir(parents=True, exist_ok=True)

    def get_lib(lib):
        dl = lib.get("downloads", {})
        art = dl.get("artifact")
        if art:
            download(art["url"], root / "libraries" / art["path"], art.get("sha1"),
                     progress=progress)
        native_key = (lib.get("natives") or {}).get("windows")
        if native_key:
            cls = dl.get("classifiers", {}).get(native_key.replace("${arch}", "64"))
            if cls:
                jar_path = root / "libraries" / cls["path"]
                download(cls["url"], jar_path, cls.get("sha1"), progress=progress)
                with zipfile.ZipFile(jar_path) as z:
                    for name in z.namelist():
                        if name.endswith((".dll", ".so", ".dylib")):
                            target = natives_dir / Path(name).name
                            if not target.exists():
                                target.write_bytes(z.read(name))

    progress and progress.set(total=len(libs), done=0, message="libraries")
    with ThreadPoolExecutor(max_workers=8) as pool:
        futs = [pool.submit(get_lib, lib) for lib in libs]
        for f in as_completed(futs):
            f.result()
            progress and progress.inc()

    # asset index + objects
    idx = meta.get("assetIndex")
    if idx:
        idx_path = root / "assets" / "indexes" / f"{idx['id']}.json"
        download(idx["url"], idx_path, idx.get("sha1"), progress=progress)
        index = json.loads(idx_path.read_text(encoding="utf-8"))
        objects = list(index.get("objects", {}).items())
        progress and progress.set(total=len(objects), done=0, message="assets")
        pending = []

        def get_obj(item):
            name, obj = item
            dest = root / "assets" / "objects" / obj["hash"][:2] / obj["hash"]
            # always go through download(): it re-verifies the SHA-1, so a truncated file
            # with the expected size cannot be trusted just because it exists
            download(f"{ASSET_BASE}/{obj['hash'][:2]}/{obj['hash']}", dest, obj["hash"],
                     progress=progress)

        with ThreadPoolExecutor(max_workers=24) as pool:
            futs = [pool.submit(get_obj, it) for it in objects]
            for f in as_completed(futs):
                f.result()
                progress and progress.inc()
    ensure_natives(mc, root)
    ensure_profile(mc, root)
    return mc


def install_fabric(mc: str, root: Path, progress: Progress | None = None,
                   loader_version: str | None = None) -> str:
    root = Path(root)
    loaders = http_json(f"{FABRIC_META}/versions/loader/{mc}")
    if loader_version:
        match = [x for x in loaders if x.get("loader", {}).get("version") == loader_version]
        if not match:
            raise RuntimeError(f"fabric loader {loader_version} is not available for {mc}")
        loader = match[0]
    else:
        loader = next((x for x in loaders if x.get("loader", {}).get("stable")), loaders[0])
    loader_ver = loader["loader"]["version"]
    vid = f"fabric-loader-{loader_ver}-{mc}"
    progress and progress.set(phase="download", message=f"fabric {vid}")
    profile = http_json(f"{FABRIC_META}/versions/loader/{mc}/{loader_ver}/profile/json")
    profile["id"] = vid
    vdir = root / "versions" / vid
    vdir.mkdir(parents=True, exist_ok=True)
    (vdir / f"{vid}.json").write_text(json.dumps(profile, indent=2), encoding="utf-8")
    libs = profile.get("libraries", [])
    progress and progress.set(total=len(libs), done=0, message="fabric libraries")

    def get_lib(lib):
        name = lib["name"]
        parts = name.split(":")
        group, artifact, ver = parts[0], parts[1], parts[2]
        classifier = parts[3] if len(parts) > 3 else None
        rel = f"{group.replace('.', '/')}/{artifact}/{ver}/{artifact}-{ver}" + (
            f"-{classifier}" if classifier else "") + ".jar"
        base = (lib.get("url") or "https://maven.fabricmc.net/").rstrip("/") + "/"
        download_maven(base + rel, root / "libraries" / rel, progress=progress)

    with ThreadPoolExecutor(max_workers=8) as pool:
        futs = [pool.submit(get_lib, lib) for lib in libs]
        for f in as_completed(futs):
            f.result()
            progress and progress.inc()
    ensure_profile(vid, root)
    return vid


def ensure_natives(mc: str, root: Path) -> None:
    """Extract the Windows natives of an installed version into versions/<mc>/natives."""
    root = Path(root)
    meta_path = root / "versions" / mc / f"{mc}.json"
    if not meta_path.exists():
        return
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    natives_dir = root / "versions" / mc / "natives"
    natives_dir.mkdir(parents=True, exist_ok=True)
    jars = []
    for lib in meta.get("libraries", []):
        if not allowed_win(lib):
            continue
        dl = lib.get("downloads", {})
        key = (lib.get("natives") or {}).get("windows")
        if key:
            cls = dl.get("classifiers", {}).get(key.replace("${arch}", "64"))
            if cls:
                jars.append((cls["path"], cls["url"], cls.get("sha1")))
            continue
        name = lib.get("name", "")
        parts = name.split(":")
        if len(parts) >= 4 and "natives-windows" in parts[3]:
            art = dl.get("artifact")
            if art:
                jars.append((art["path"], art["url"], art.get("sha1")))
    for rel, url, sha1 in jars:
        jar = root / "libraries" / rel
        if not jar.exists():
            download(url, jar, sha1)
        with zipfile.ZipFile(jar) as z:
            for name in z.namelist():
                if name.endswith((".dll", ".so", ".dylib")):
                    target = natives_dir / Path(name).name
                    if not target.exists():
                        target.write_bytes(z.read(name))


def install_vanilla_launcher_profile(mc: str, root: Path) -> None:
    """Ensure the vanilla version folder exists (needed before fabric inherits it)."""
    if not (Path(root) / "versions" / mc / f"{mc}.json").exists():
        install_vanilla(mc, root)
    ensure_natives(mc, root)


NEOFORGE_MAVEN = "https://maven.neoforged.net/releases/"


def prepare_installer_libraries(installer: Path, root: Path, progress: Progress | None = None) -> int:
    """Pre-download every library an official Forge/NeoForge installer needs.

    The installers fetch their libraries with Java's own HTTP stack, which times out on
    some networks even when Python downloads fine. Seeding the files here keeps the
    official processors (jarsplitter / renaming / binarypatcher) as the source of truth
    for the install, but lets them run offline.
    """
    root = Path(root)
    wanted: dict[str, tuple[str, str | None]] = {}
    with zipfile.ZipFile(installer) as jar:
        for entry in ("install_profile.json", "version.json"):
            try:
                data = json.loads(jar.read(entry).decode("utf-8"))
            except KeyError:
                continue
            for lib in data.get("libraries", []):
                art = (lib.get("downloads") or {}).get("artifact") or {}
                path = art.get("path")
                if not path:
                    continue
                wanted[path] = (art.get("url") or NEOFORGE_MAVEN + path, art.get("sha1"))
    total = len(wanted)
    downloaded = 0
    progress and progress.set(phase="download", message=f"loader libraries {total}", total=total, done=0)
    for i, (rel, (url, digest)) in enumerate(sorted(wanted.items()), 1):
        dest = root / "libraries" / rel
        if not (dest.exists() and digest and sha1_of(dest) == digest):
            download(url, dest, digest, progress=progress)
            downloaded += 1
        progress and progress.set(done=i)
    return downloaded


def loader_artifacts(version_id: str, root: Path) -> dict[str, bool]:
    """Game artifacts a loader profile must provide before it can boot.

    NeoForge 1.21.1 (FancyModLoader 4) builds the *minecraft* mod file from
    libraries/net/minecraft/client/<neoform>/client-...-{srg,extra}.jar plus
    libraries/net/neoforged/neoforge/<version>/neoforge-<version>-client.jar, and the
    *neoforge* mod file from neoforge-<version>-universal.jar. A profile JSON plus a
    renamed vanilla jar is NOT an install: without these files the client dies in
    DisplayWindow.updateModuleReads looking for the "neoforge" module.
    """
    root = Path(root)
    libs = root / "libraries"
    items: dict[str, bool] = {}
    if version_id.startswith("neoforge-"):
        ver = version_id.split("-", 1)[1]
        base = libs / "net" / "neoforged" / "neoforge" / ver
        items["neoforge_client"] = (base / f"neoforge-{ver}-client.jar").exists()
        items["neoforge_universal"] = (base / f"neoforge-{ver}-universal.jar").exists()
    client_dir = libs / "net" / "minecraft" / "client"
    if client_dir.exists():
        items["minecraft_srg"] = bool(list(client_dir.glob("*/client-*-srg.jar")))
        items["minecraft_extra"] = bool(list(client_dir.glob("*/client-*-extra.jar")))
    return items


def _run_installer(jar: Path, root: Path, log_path: Path) -> int:
    java = find_java()
    # the installer runs with cwd=<root>, so both paths must be absolute
    jar = Path(jar).resolve()
    root = Path(root).resolve()
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("w", encoding="utf-8", errors="replace") as log:
        log.write(f"$ {java} -jar {jar} --installClient {root}\n")
        log.flush()
        proc = subprocess.run([java, "-jar", str(jar), "--installClient", str(root)],
                              cwd=str(root), stdout=log, stderr=subprocess.STDOUT)
    return proc.returncode


def install_forge(mc: str, root: Path, progress: Progress | None = None, version: str | None = None) -> str:
    root = Path(root)
    # the Forge profile inheritsFrom the vanilla version; without its json/jar/asset index
    # build_command() fails with "version 1.20.1 not installed"
    install_vanilla_launcher_profile(mc, root)
    promos = http_json(FORGE_PROMOS)["promos"]
    version = version or promos.get(f"{mc}-recommended") or promos.get(f"{mc}-latest")
    if not version:
        raise RuntimeError(f"no forge promotion for {mc}")
    forge_ver = f"{mc}-{version}"
    vid = f"{mc}-forge-{version}"
    vdir = root / "versions" / vid
    if (vdir / f"{vid}.json").exists():
        return vid
    progress and progress.set(phase="download", message=f"forge installer {forge_ver}")
    installer = root / "installers" / f"forge-{forge_ver}-installer.jar"
    url = f"https://maven.minecraftforge.net/net/minecraftforge/forge/{forge_ver}/forge-{forge_ver}-installer.jar"
    download_maven(url, installer, progress=progress)
    prepare_installer_libraries(installer, root, progress)
    progress and progress.set(message="running forge installer")
    rc = _run_installer(installer, root, root / "installers" / f"forge-{forge_ver}.log")
    if rc != 0 or not (vdir / f"{vid}.json").exists():
        found = sorted((root / "versions").glob(f"{mc}-forge-*"))
        if found:
            return found[-1].name
        raise RuntimeError(f"forge installer failed rc={rc}")
    return vid


def _version_key(v: str):
    """Sort loader version strings numerically ("21.1.9" < "21.1.264")."""
    return [int(x) if x.isdigit() else x for x in v.replace("-", ".").split(".")]


def install_neoforge(mc: str, root: Path, progress: Progress | None = None, version: str | None = None) -> str:
    root = Path(root)
    # same inheritance requirement as Forge
    install_vanilla_launcher_profile(mc, root)
    data = http_json(NEOFORGE_VERSIONS)
    all_versions = data.get("versions", [])
    prefix = ".".join(mc.split(".")[1:]) + "."  # 1.21.1 -> "21.1."
    cands = [v for v in all_versions if v.startswith(prefix)]
    if not cands:
        raise RuntimeError(f"no neoforge build matched {mc}")
    version = version or sorted(cands, key=_version_key)[-1]
    vid = f"neoforge-{version}"
    vdir = root / "versions" / vid
    if (vdir / f"{vid}.json").exists() and all(loader_artifacts(vid, root).values()):
        return vid
    progress and progress.set(phase="download", message=f"neoforge installer {version}")
    installer = root / "installers" / f"neoforge-{version}-installer.jar"
    url = f"{NEOFORGE_MAVEN}net/neoforged/neoforge/{version}/neoforge-{version}-installer.jar"
    download_maven(url, installer, progress=progress)
    prepare_installer_libraries(installer, root, progress)
    progress and progress.set(message="running neoforge installer")
    log_path = root / "installers" / f"neoforge-{version}.log"
    rc = _run_installer(installer, root, log_path)
    missing = [name for name, present in loader_artifacts(vid, root).items() if not present]
    if rc != 0 or not (vdir / f"{vid}.json").exists() or missing:
        raise RuntimeError(
            f"neoforge installer incomplete (rc={rc}, missing: {', '.join(missing) or 'profile json'}); "
            f"see {log_path}")
    return vid



def verify_install(version_id: str, root: Path) -> dict:
    """Check an installed version: json, client jar, libraries, natives, assets."""
    root = Path(root)
    vdir = root / "versions" / version_id
    report = {"version": version_id, "root": str(root), "ok": True, "items": {}}

    meta_path = vdir / f"{version_id}.json"
    report["items"]["version_json"] = meta_path.exists()
    if not meta_path.exists():
        report["ok"] = False
        return report
    data = json.loads(meta_path.read_text(encoding="utf-8"))
    base_id = data.get("inheritsFrom") or version_id
    base_dir = root / "versions" / base_id
    base_data = data if base_id == version_id else json.loads(
        (base_dir / f"{base_id}.json").read_text(encoding="utf-8"))

    jar = base_dir / f"{base_id}.jar"
    report["items"]["client_jar"] = {
        "ok": jar.exists(),
        "path": str(jar),
        "size": jar.stat().st_size if jar.exists() else 0,
    }
    if not jar.exists():
        report["ok"] = False

    if version_id.startswith("neoforge-"):
        artifacts = loader_artifacts(version_id, root)
        report["items"]["loader_artifacts"] = artifacts
        if not all(artifacts.values()):
            report["ok"] = False

    libs = []
    lib_missing = []
    all_libs = list(data.get("libraries", []))
    if base_id != version_id:
        all_libs += list(base_data.get("libraries", []))
    for lib in all_libs:
        if not allowed_win(lib):
            continue
        art = lib.get("downloads", {}).get("artifact")
        if not art:
            continue
        libs.append(art["path"])
        if not (root / "libraries" / art["path"]).exists():
            lib_missing.append(art["path"])
    report["items"]["libraries"] = {"total": len(libs), "missing": len(lib_missing),
                                    "missing_sample": lib_missing[:5]}
    if lib_missing:
        report["ok"] = False

    natives_dir = base_dir / "natives"
    dlls = sorted(p.name for p in natives_dir.glob("*.dll")) if natives_dir.exists() else []
    report["items"]["natives"] = {"dir": str(natives_dir), "dll": len(dlls), "sample": dlls[:4]}

    idx = base_data.get("assetIndex") or {}
    idx_path = root / "assets" / "indexes" / f"{idx.get('id', 'legacy')}.json"
    report["items"]["asset_index"] = {"ok": idx_path.exists(), "path": str(idx_path)}
    if idx_path.exists():
        index = json.loads(idx_path.read_text(encoding="utf-8"))
        total = 0
        missing = 0
        for _name, obj in index.get("objects", {}).items():
            total += 1
            dest = root / "assets" / "objects" / obj["hash"][:2] / obj["hash"]
            if not dest.exists():
                missing += 1
        report["items"]["assets"] = {"total": total, "missing": missing}
        if missing:
            report["ok"] = False
    else:
        report["ok"] = False
    return report


def print_report(report: dict) -> None:
    print(f"version: {report['version']}")
    print(f"root:    {report['root']}")
    items = report["items"]
    print(f"  version json : {'ok' if items.get('version_json') else 'MISSING'}")
    jar = items.get("client_jar", {})
    print(f"  client jar   : {'ok' if jar.get('ok') else 'MISSING'} ({jar.get('size', 0)} bytes)")
    lib = items.get("libraries", {})
    print(f"  libraries    : {lib.get('total', 0) - lib.get('missing', 0)}/{lib.get('total', 0)} present")
    if lib.get("missing_sample"):
        print(f"    missing e.g.: {', '.join(lib['missing_sample'])}")
    loader = items.get("loader_artifacts")
    if loader:
        print("  loader files : " + ", ".join(
            f"{name}={'ok' if present else 'MISSING'}" for name, present in loader.items()))
    nat = items.get("natives", {})
    print(f"  natives      : {nat.get('dll', 0)} dll {nat.get('sample', [])}")
    assets = items.get("assets", {})
    print(f"  assets       : {assets.get('total', 0) - assets.get('missing', 0)}/{assets.get('total', 0)} present")
    print("RESULT:", "OK" if report["ok"] else "INCOMPLETE")



def ensure_version_jar(version_id: str, root: Path) -> None:
    """Forge/NeoForge inherit the vanilla jar but the library expects <id>.jar; copy it."""
    root = Path(root)
    vdir = root / "versions" / version_id
    path = vdir / f"{version_id}.json"
    if not path.exists():
        return
    target = vdir / f"{version_id}.jar"
    if target.exists():
        return
    data = json.loads(path.read_text(encoding="utf-8"))
    base = data.get("inheritsFrom")
    if not base:
        return
    source = root / "versions" / base / f"{base}.jar"
    if source.exists():
        shutil.copy2(source, target)


def ensure_version_libraries(version_id: str, root: Path, progress: Progress | None = None) -> int:
    """Download every library the version profile references (Forge/NeoForge profiles need this)."""
    root = Path(root)
    vdir = root / "versions" / version_id
    path = vdir / f"{version_id}.json"
    if not path.exists():
        return 0
    data = json.loads(path.read_text(encoding="utf-8"))
    libs = [lib for lib in data.get("libraries", []) if allowed_win(lib)]
    done = 0
    for lib in libs:
        art = lib.get("downloads", {}).get("artifact")
        if art:
            download(art["url"], root / "libraries" / art["path"], art.get("sha1"),
                     progress=progress)
            done += 1
            continue
        name = lib.get("name", "")
        parts = name.split(":")
        if len(parts) >= 3 and lib.get("url"):
            group, artifact, ver = parts[0], parts[1], parts[2]
            classifier = parts[3] if len(parts) > 3 else None
            rel = f"{group.replace('.', '/')}/{artifact}/{ver}/{artifact}-{ver}" + (
                f"-{classifier}" if classifier else "") + ".jar"
            download(lib["url"].rstrip("/") + "/" + rel, root / "libraries" / rel,
                     progress=progress)
            done += 1
    return done


def find_runtime_java(root: Path) -> str | None:
    """A Java runtime installed under <root>/runtime by the launcher, if any."""
    matches = sorted((Path(root) / "runtime").glob("**/bin/java.exe"))
    return str(matches[0]) if matches else None


def find_java() -> str:
    env = os.environ.get("MC_JAVA") or os.environ.get("JAVA_HOME")
    if env:
        p = Path(env) / "bin" / "java.exe"
        if p.exists():
            return str(p)
        if Path(env).exists() and Path(env).suffix == ".exe":
            return str(env)
    java = shutil.which("java")
    if java:
        return java
    candidates = []
    local = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local")))
    for pkg in local.glob("Packages/Microsoft.4297127D64EC6_*/LocalCache/Local/runtime/**/bin/java.exe"):
        candidates.append(pkg)
    minecraft_roots = [Path.home() / ".minecraft", Path(r"D:\我的世界\.minecraft")]
    for mc in minecraft_roots:
        candidates += list(mc.glob("runtime/**/bin/java.exe"))
        candidates += list(mc.glob("versions/**/runtime/bin/java.exe"))
    candidates += list(Path(r"C:\Program Files\Java").glob("jdk*/bin/java.exe"))
    candidates += list(Path(r"C:\Program Files\Eclipse Adoptium").glob("jdk*/bin/java.exe"))
    if candidates:
        return str(sorted(candidates)[-1])
    roots = [Path(__file__).resolve().parent.parent, Path(__file__).resolve().parent.parent.parent]
    for root in roots:
        for cand in root.glob(".toolchain/jdk/bin/java.exe"):
            return str(cand)
    raise RuntimeError("Java not found: set JAVA_HOME or MC_JAVA")
def load_version(version_id: str, root: Path) -> dict:
    root = Path(root)
    vdir = root / "versions" / version_id
    path = vdir / f"{version_id}.json"
    if not path.exists():
        raise RuntimeError(f"version {version_id} not installed ({path})")
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("inheritsFrom"):
        base = load_version(data["inheritsFrom"], root)
        merged = dict(base)
        merged["id"] = version_id
        merged["inheritsFrom"] = data["inheritsFrom"]
        merged["libraries"] = data.get("libraries", []) + base.get("libraries", [])
        merged["arguments"] = {
            "game": data.get("arguments", {}).get("game", []) + base.get("arguments", {}).get("game", []),
            "jvm": base.get("arguments", {}).get("jvm", []) + data.get("arguments", {}).get("jvm", []),
        }
        merged["mainClass"] = data.get("mainClass") or base.get("mainClass")
        merged["_dir"] = str(vdir)
        merged["_base_dir"] = base.get("_dir")
        return merged
    data["_dir"] = str(vdir)
    return data


def _resolve_args(items, values):
    out = []
    for item in items:
        if isinstance(item, str):
            out.append(item)
        elif isinstance(item, dict):
            if eval_rules(item.get("rules")):
                val = item.get("value")
                if isinstance(val, list):
                    out.extend(val)
                elif val is not None:
                    out.append(val)
    safe = {"quickPlayPath": "", "quickPlaySingleplayer": "", "quickPlayMultiplayer": "",
            "resolution_width": "854", "resolution_height": "480", "auth_session": "0",
            "game_assets": values.get("assets_root", "")}
    safe.update(values)
    resolved = []
    for a in out:
        if "${" in a:
            try:
                a = a.replace("${", "{").format_map(safe)
            except Exception:
                pass
        elif "{" in a:
            try:
                a = a.format_map(safe)
            except Exception:
                pass
        resolved.append(a)
    return resolved


def offline_uuid(name: str) -> str:
    return str(uuid.UUID(bytes=hashlib.md5(("OfflinePlayer:" + name).encode()).digest(), version=3))


def build_command(version_id: str, root: Path, username: str, max_mem="2G",
                  extra_jvm=None, extra_game=None) -> tuple[list[str], Path, Path]:
    if version_id.startswith("neoforge-"):
        missing = [name for name, present in loader_artifacts(version_id, Path(root)).items()
                   if not present]
        if missing:
            raise RuntimeError(
                f"neoforge install is incomplete ({', '.join(missing)}); reinstall it — "
                "a profile json plus a renamed vanilla jar cannot boot (earlydisplay needs the module)")
    try:
        import backend
        if backend.AVAILABLE and ("-forge-" in version_id or version_id.startswith("neoforge")):
            ensure_version_jar(version_id, root)
            ensure_version_libraries(version_id, root)
            cmd = backend.command(version_id, root, username) or []
            if cmd:
                cmd = [cmd[0], f"-Xmx{max_mem}"] + cmd[1:]
                if extra_game:
                    cmd += extra_game
                log = root / "logs" / f"launch-{time.strftime('%Y%m%d-%H%M%S')}.log"
                return cmd, log, root
    except Exception:
        pass
    root = Path(root).resolve()
    data = load_version(version_id, root)
    libs = [lib for lib in data.get("libraries", []) if allowed_win(lib)]
    cp = []
    for lib in libs:
        art = lib.get("downloads", {}).get("artifact")
        if art:
            cp.append(str(root / "libraries" / art["path"]))
            continue
        name = lib.get("name", "")
        parts = name.split(":")
        if len(parts) >= 3:
            group, artifact, ver = parts[0], parts[1], parts[2]
            classifier = parts[3] if len(parts) > 3 else None
            rel = f"{group.replace('.', '/')}/{artifact}/{ver}/{artifact}-{ver}" + (
                f"-{classifier}" if classifier else "") + ".jar"
            cp.append(str(root / "libraries" / rel))
    vdir = Path(data["_dir"])
    jar = vdir / f"{version_id}.jar"
    if not jar.exists():
        base_name = data.get("inheritsFrom") or version_id
        base_dir = Path(data["_base_dir"]) if data.get("_base_dir") else vdir
        jar = base_dir / f"{base_name}.jar"
    cp.append(str(jar))

    assets_root = str(root / "assets")
    asset_index = (data.get("assetIndex") or {}).get("id", "legacy")
    natives_dir = vdir / "natives"
    if data.get("inheritsFrom"):
        base_natives = root / "versions" / data["inheritsFrom"] / "natives"
        if base_natives.exists() and any(base_natives.iterdir()):
            natives_dir = base_natives
        elif not natives_dir.exists():
            natives_dir.mkdir(parents=True, exist_ok=True)
    natives = str(natives_dir)
    uid = offline_uuid(username)
    values = {
        "auth_player_name": username,
        "version_name": version_id,
        "game_directory": str(root),
        "assets_root": assets_root,
        "assets_index_name": asset_index,
        "auth_uuid": uid,
        "auth_access_token": "0",
        "clientid": "0",
        "auth_xuid": "0",
        "user_type": "msa",
        "version_type": data.get("type", "release"),
        "natives_directory": natives,
        "launcher_name": "mcbridge-launcher",
        "launcher_version": "0.1",
        "classpath": ";".join(cp),
        "library_directory": str(root / "libraries"),
        "classpath_separator": ";",
    }
    args_blob = data.get("arguments") or {}
    jvm_args = _resolve_args(args_blob.get("jvm") or [], values)
    game_args = _resolve_args(args_blob.get("game") or [], values)
    if not jvm_args:
        jvm_args = ["-Djava.library.path=" + natives, "-cp", ";".join(cp)]
    main_class = data.get("mainClass", "net.minecraft.client.main.Main")
    legacy = main_class.startswith(("cpw.mods", "net.neoforged"))
    if legacy:
        jvm_args = [a for a in jvm_args if a not in ("-cp", "-classpath")]
        jvm_args.append("-DlegacyClassPath=" + ";".join(cp))
    elif "-cp" not in jvm_args and "-classpath" not in jvm_args:
        jvm_args += ["-cp", ";".join(cp)]
    if not any(a.startswith("-Djava.library.path=") for a in jvm_args):
        jvm_args.insert(0, "-Djava.library.path=" + natives)

    def ensure(flag, value):
        if flag not in game_args:
            game_args.extend([flag, value])

    ensure("--username", username)
    ensure("--version", version_id)
    ensure("--gameDir", str(root))
    ensure("--assetsDir", assets_root)
    ensure("--assetIndex", asset_index)
    ensure("--uuid", uid)
    ensure("--accessToken", "0")
    ensure("--userType", "msa")
    ensure("--versionType", data.get("type", "release"))
    java = find_runtime_java(root) or find_java()
    cmd = [java, f"-Xmx{max_mem}"] + jvm_args + [main_class] + game_args
    if extra_game:
        cmd += extra_game
    log = root / "logs" / f"launch-{time.strftime('%Y%m%d-%H%M%S')}.log"
    return cmd, log, root


def launch(version_id: str, root: Path, username: str, log_path: Path | None = None,
           max_mem="2G", extra_game=None):
    cmd, log, root = build_command(version_id, root, username, max_mem, extra_game=extra_game)
    log.parent.mkdir(parents=True, exist_ok=True)
    log_path = log_path or log
    f = open(log_path, "w", encoding="utf-8", errors="replace")
    f.write(" ".join(cmd) + "\n")
    f.flush()
    proc = subprocess.Popen(cmd, cwd=str(root), stdout=f, stderr=subprocess.STDOUT)
    return proc, log_path


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: mclaunch.py install <mc> <root> [fabric|vanilla|forge|neoforge]")
        print("       mclaunch.py launch <version_id> <root> <username>")
        print("       mclaunch.py verify <version_id> <root>")
        sys.exit(1)
    cmd = sys.argv[1]
    if cmd == "install":
        mc, root = sys.argv[2], Path(sys.argv[3])
        loader = sys.argv[4] if len(sys.argv) > 4 else "vanilla"
        p = Progress()
        if loader == "vanilla":
            print(install_vanilla(mc, root, p))
        elif loader == "fabric":
            install_vanilla_launcher_profile(mc, root)
            print(install_fabric(mc, root, p))
        elif loader == "forge":
            print(install_forge(mc, root, p))
        elif loader == "neoforge":
            print(install_neoforge(mc, root, p))
        else:
            raise SystemExit("unknown loader")
        print(p.snapshot())
    elif cmd == "verify":
        rep = verify_install(sys.argv[2], Path(sys.argv[3]))
        print_report(rep)
        sys.exit(0 if rep["ok"] else 3)
    elif cmd == "launch":
        proc, log = launch(sys.argv[2], Path(sys.argv[3]), sys.argv[4])
        print("pid", proc.pid, "log", log)
    else:
        print("unknown command")
        sys.exit(1)
