#!/usr/bin/env python3
"""Tiny local web server for the mcbridge launcher GUI."""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import threading
import time
import webbrowser
from urllib.parse import parse_qs, unquote, urlparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import mclaunch
from mclaunch import (Progress, find_java, install_fabric, install_forge, install_neoforge,
                      install_vanilla, install_vanilla_launcher_profile, launch, version_manifest)

HERE = Path(__file__).resolve().parent
WEB = HERE / "web"
CONFIG = HERE / "config.json"
TASK = Progress()
_JVM_CACHE = {"ts": 0.0, "data": None}
TASK_LOCK = threading.Lock()
LAUNCHES = []
SOURCE_CHECK = {"running": False, "started": None, "result": None, "error": None}


def summarize_canary(data: dict) -> dict:
    """Condense runs/.../canary.json into what the GUI needs (pure, unit-testable)."""
    def failures(bucket: str) -> list[str]:
        return [str(r.get("label")) for r in data.get(bucket, []) if not r.get("ok")]

    return {
        "ok": bool(data.get("ok")),
        "core_ok": bool(data.get("core_ok", data.get("ok"))),
        "mirrors_ok": bool(data.get("mirrors_ok", False)),
        "neoforge_ok": bool(data.get("neoforge_ok", False)),
        "generated": data.get("generated"),
        "core_failures": failures("required"),
        "mirror_failures": failures("mirrors"),
        "neoforge_failures": failures("neoforge"),
        "expected_misses": len(data.get("expected_misses", [])),
    }


def run_source_check(root: Path) -> None:
    """Run the canary tool into <root>/.mcbridge/canary (never touches repo evidence)."""
    script = HERE.parent / "tools" / "check_download_sources.py"
    out_dir = Path(root) / ".mcbridge" / "canary"
    try:
        proc = subprocess.run([sys.executable, "-B", str(script), "--out", str(out_dir)],
                              cwd=str(HERE.parent), capture_output=True, text=True, timeout=300)
        data = json.loads((out_dir / "canary.json").read_text(encoding="utf-8"))
        summary = summarize_canary(data)
        health_file = out_dir / "health.json"
        applied = 0
        if health_file.exists():
            hosts = (json.loads(health_file.read_text(encoding="utf-8")) or {}).get("hosts") or {}
            mclaunch.merge_source_health(hosts)
            applied = len(hosts)
        summary["exit"] = proc.returncode
        summary["health_hosts"] = applied
        SOURCE_CHECK.update(running=False, error=None, result=summary)
    except Exception as exc:  # noqa: BLE001 - surface the error in the GUI
        SOURCE_CHECK.update(running=False, error=str(exc))


def default_root() -> str:
    cands = []
    # APPDATA is absent on POSIX; Path("") is ".", so an unguarded candidate
    # would silently adopt whatever directory the launcher was started in.
    appdata = os.environ.get("APPDATA")
    if appdata:
        cands.append(Path(appdata) / ".minecraft")
    if os.name == "nt":
        cands.append(Path(r"D:\我的世界\.minecraft"))
    cands.append(Path.home() / ".minecraft")
    if os.name != "nt":
        cands.append(Path.home() / ".local" / "share" / "minecraft")
    for c in cands:
        try:
            if c.exists() and (c / "versions").exists():
                return str(c)
        except OSError:
            continue
    return str(Path.home() / ".mcbridge" / "mc")


def load_config():
    if CONFIG.exists():
        cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
        cfg.setdefault("download_source", "auto")
        return cfg
    return {"root": default_root(), "username": "Player", "mem": "2G", "download_source": "auto"}


def save_config(cfg):
    CONFIG.write_text(json.dumps(cfg, indent=2), encoding="utf-8")


def apply_download_config(cfg):
    """Push the configured source mode + persisted host health into the download core."""
    mode = mclaunch.set_source_mode(cfg.get("download_source"))
    try:
        root = Path(cfg["root"])
        mclaunch.load_source_health(root / ".mcbridge" / "source-health.json")
    except Exception:  # noqa: BLE001 - a broken/missing health file must not block startup
        pass
    return mode


MC_ID = re.compile(
    r"^(?:"
    r"\d+\.\d+(?:\.\d+)?(?:-(?:pre|rc)\d+)?"
    r"|\d{2}w\d{2}[a-z]"
    r"|[ab]\d+\.\d+(?:\.\d+)?[a-z]?"
    r"|inf-\d+|rd-\d+|c\d+\.\d+.*"
    r"|fabric-loader-.+|neoforge-.+|forge-.+|\d+\.\d+(?:\.\d+)?-forge-.+"
    r")$"
)
_MANIFEST_IDS = None


def manifest_ids() -> set[str]:
    """Best-effort cache of official version ids; empty when offline."""
    global _MANIFEST_IDS
    if _MANIFEST_IDS is not None:
        return _MANIFEST_IDS
    try:
        versions, _latest = version_manifest()
        _MANIFEST_IDS = {v["id"] for v in versions}
    except Exception:  # noqa: BLE001 - offline is fine, regex still applies
        _MANIFEST_IDS = set()
    return _MANIFEST_IDS


def is_mc_version(name: str) -> bool:
    """Keep real game versions (release/snapshot/old) and loader profiles; hide modpack instances."""
    return name in manifest_ids() or bool(MC_ID.match(name))


def installed_versions(root: Path):
    out = []
    vroot = Path(root) / "versions"
    if not vroot.exists():
        return out
    for d in sorted(vroot.iterdir(), key=lambda p: p.name.lower()):
        if not (d / f"{d.name}.json").exists():
            continue
        if not is_mc_version(d.name):
            continue
        try:
            data = json.loads((d / f"{d.name}.json").read_text(encoding="utf-8"))
        except Exception:
            continue
        out.append({"id": d.name, "inherits": data.get("inheritsFrom"),
                    "type": data.get("type", "release"), "main": data.get("mainClass")})
    return out


DIR_TARGETS = ("root", "mods", "versions", "version", "logs", "saves", "assets", "screenshots")


def dir_target(root, target: str, version_id: str = ""):
    """Resolve one of the fixed folders inside the game root (never an arbitrary path)."""
    root = Path(root).resolve()
    target = str(target or "").strip().lower()
    if target not in DIR_TARGETS:
        raise ValueError(f"unknown directory target {target!r}")
    if target == "version":
        vid = str(version_id or "").strip()
        if not vid or vid in (".", "..") or "/" in vid or "\\" in vid or ":" in vid:
            raise ValueError("invalid version id")
        path = root / "versions" / vid
    elif target == "root":
        path = root
    else:
        path = root / target
    resolved = path.resolve()
    if resolved != root and root not in resolved.parents:
        raise ValueError("path escapes the game root")
    return path


def open_in_explorer(path, platform: str | None = None) -> bool:
    """Open a folder in the OS file manager.

    Windows uses os.startfile, macOS `open`, everything else `xdg-open`. Returns
    False when no opener is available instead of raising: a missing xdg-open
    should not turn the HTTP request that asked for it into a 500.
    """
    path = Path(path)
    platform = platform or sys.platform
    try:
        if platform.startswith("win"):
            os.startfile(str(path))  # noqa: S606 - local launcher opening a fixed folder
            return True
        subprocess.Popen(["open" if platform == "darwin" else "xdg-open", str(path)])  # noqa: S603
        return True
    except (OSError, AttributeError):
        return False


def sync_profiles(root) -> list[str]:
    """Give every installed version a launcher_profiles.json entry.

    PCL/HMCL scan versions/ directly and do not need this, but the official launcher
    only lists profiles, and modpack launchers read profile metadata.
    """
    root = Path(root)
    path = root / "launcher_profiles.json"
    data = {}
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001 - a broken profile file is replaced below
            data = {}
    known = {p.get("lastVersionId") for p in (data.get("profiles") or {}).values()
             if isinstance(p, dict)}
    added = []
    for version in installed_versions(root):
        if version["id"] not in known:
            mclaunch.ensure_profile(version["id"], root)
            added.append(version["id"])
    return added


def run_install(mc, loader, version):
    with TASK_LOCK:
        TASK.__init__()
    cfg = load_config()
    root = Path(cfg["root"])
    try:
        TASK.set(phase="start", message=f"{loader} {mc}")
        if loader == "vanilla":
            vid = install_vanilla(mc, root, TASK)
        elif loader == "fabric":
            install_vanilla_launcher_profile(mc, root)
            vid = install_fabric(mc, root, TASK, version)
        elif loader in ("forge", "neoforge"):
            import backend
            install_vanilla_launcher_profile(mc, root)
            java = backend.pick_java(mc) or find_java()
            if loader == "neoforge":
                try:
                    vid = backend.install_neoforge_direct(mc, root, version, java, TASK)
                except Exception as exc:  # noqa: BLE001
                    if not backend.AVAILABLE:
                        raise
                    TASK.set(message=f"neoforge direct failed ({exc}); trying library")
                    vid = backend.install(loader, mc, root, version, java, TASK)
            else:
                if not backend.AVAILABLE:
                    raise RuntimeError("Forge 需要 minecraft-launcher-lib：pip install minecraft-launcher-lib")
                vid = backend.install(loader, mc, root, version, java, TASK)
        else:
            raise RuntimeError("unknown loader " + loader)
        TASK.set(phase="done", message=vid)
    except Exception as exc:  # noqa: BLE001
        TASK.set(phase="error", error=str(exc))


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def _send(self, code, body, ctype="application/json"):
        raw = body if isinstance(body, bytes) else json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _read_json(self):
        n = int(self.headers.get("Content-Length", 0))
        return json.loads(self.rfile.read(n) or b"{}")

    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/api/config":
            cfg = load_config()
            try:
                cfg["java"] = find_java()
                cfg["java_error"] = None
            except Exception as exc:  # noqa: BLE001 - report, do not drop the connection
                cfg["java"] = None
                cfg["java_error"] = str(exc)
            return self._send(200, cfg)
        if path == "/api/status":
            cfg = load_config()
            try:
                java = find_java()
                java_error = None
            except Exception as exc:  # noqa: BLE001
                java = None
                java_error = str(exc)
            return self._send(200, {"root": cfg["root"], "versions": installed_versions(Path(cfg["root"])),
                                    "java": java, "java_error": java_error})
        if path == "/api/mrpacks":
            cfg = load_config()
            qs = parse_qs(urlparse(self.path).query)
            roots = []
            if qs.get("dir", [""])[0]:
                roots = [Path(qs["dir"][0])]
            else:
                roots = [Path(cfg["root"]) / "packs", Path.home() / "Downloads"]
            packs = []
            for d in roots:
                if not d.is_dir():
                    continue
                for pack in sorted(d.glob("*.mrpack"))[:50]:
                    entry = {"path": str(pack), "name": pack.stem, "version": "", "minecraft": ""}
                    try:
                        import zipfile
                        with zipfile.ZipFile(pack) as z:
                            idx = json.loads(z.read("modrinth.index.json"))
                        entry["name"] = idx.get("name") or pack.stem
                        entry["version"] = idx.get("versionId") or ""
                        entry["minecraft"] = (idx.get("dependencies") or {}).get("minecraft", "")
                    except Exception:  # noqa: BLE001 - unreadable pack is still listed
                        entry["error"] = "unreadable modrinth.index.json"
                    packs.append(entry)
            return self._send(200, {"dirs": [str(d) for d in roots], "packs": packs})

        if path == "/api/dirs":
            cfg = load_config()
            qs = parse_qs(urlparse(self.path).query)
            vid = (qs.get("version", [""])[0] or "").strip()
            root = Path(cfg["root"])
            try:
                dirs = {name: str(dir_target(root, name, vid)) for name in DIR_TARGETS}
            except ValueError as exc:
                return self._send(400, {"error": str(exc)})
            return self._send(200, {"root": str(root), "dirs": dirs,
                                    "exists": {name: Path(p).is_dir() for name, p in dirs.items()}})

        if path == "/api/mods":
            cfg = load_config()
            mods_dir = Path(cfg["root"]) / "mods"
            mods = []
            if mods_dir.is_dir():
                for f in sorted(mods_dir.iterdir()):
                    if not f.is_file() or f.suffix.lower() not in (".jar", ".disabled"):
                        continue
                    mods.append({"name": f.name, "size": f.stat().st_size,
                                 "enabled": f.suffix.lower() == ".jar"})
            return self._send(200, {"dir": str(mods_dir), "mods": mods})

        if path == "/api/jvm":
            cfg = load_config()
            import backend
            now = time.time()
            if _JVM_CACHE["data"] and now - _JVM_CACHE["ts"] < 300:
                data = dict(_JVM_CACHE["data"])
            else:
                try:
                    backend._install_network_shims()
                    available = backend.jvm_runtimes()
                    err = None
                except Exception as exc:  # noqa: BLE001
                    available = []
                    err = str(exc)
                data = {"available": available, "error": err}
                if available:
                    _JVM_CACHE.update(ts=now, data=data)
            data["installed"] = backend.installed_runtimes(Path(cfg["root"]))
            return self._send(200, data)

        if path == "/api/loader-versions":
            qs = parse_qs(urlparse(self.path).query)
            loader = (qs.get("loader", ["fabric"])[0] or "fabric").lower()
            mc = qs.get("mc", [""])[0]
            if not mc:
                return self._send(400, {"error": "mc required"})
            try:
                if loader == "fabric":
                    data = mclaunch.http_json(f"{mclaunch.FABRIC_META}/versions/loader/{mc}")
                    versions = [x["loader"]["version"] for x in data]
                elif loader in ("forge", "neoforge"):
                    import backend
                    versions = backend.loader_versions(loader, mc)
                else:
                    return self._send(400, {"error": "unsupported loader "})
                return self._send(200, {"loader": loader, "mc": mc, "versions": versions})
            except Exception as exc:  # noqa: BLE001
                return self._send(200, {"loader": loader, "mc": mc, "versions": [], "error": str(exc)})

        if path == "/api/versions":
            try:
                versions, latest = version_manifest()
                return self._send(200, {"latest": latest, "versions": versions})
            except Exception as exc:  # noqa: BLE001
                return self._send(500, {"error": str(exc)})
        if path == "/api/task":
            return self._send(200, TASK.snapshot())
        if path == "/api/launches":
            return self._send(200, LAUNCHES[-20:])
        if path == "/api/downloads":
            qs = parse_qs(urlparse(self.path).query)
            try:
                limit = min(int(qs.get("limit", ["50"])[0] or 50), 200)
            except ValueError:
                limit = 50
            return self._send(200, {"events": list(mclaunch.DOWNLOAD_EVENTS)[-limit:]})
        if path == "/api/source-health":
            health = [{"host": k, **v} for k, v in sorted(mclaunch.SOURCE_HEALTH.items())]
            return self._send(200, {"mode": mclaunch.SOURCE_MODE, "health": health,
                                    "health_path": str(mclaunch.SOURCE_HEALTH_PATH or ""),
                                    "check": SOURCE_CHECK})
        if path == "/api/check-sources":
            return self._send(200, SOURCE_CHECK)
        if path == "/guide":
            guide = HERE.parent / "docs" / "guide.md"
            if not guide.exists():
                return self._send(404, b"guide not found", "text/plain; charset=utf-8")
            return self._send(200, guide.read_bytes(), "text/plain; charset=utf-8")
        if path.startswith("/log/"):
            log_path = Path(unquote(path[len("/log/"):]))
            offset = 0
            if "offset=" in self.path:
                offset = int(self.path.split("offset=")[1].split("&")[0])
            if not log_path.exists():
                return self._send(404, {"error": "no log"})
            data = log_path.read_bytes()
            chunk = data[offset:]
            return self._send(200, {"offset": offset + len(chunk),
                                    "text": chunk.decode("utf-8", "replace")})
        # static
        rel = path.lstrip("/") or "index.html"
        file = (WEB / rel).resolve()
        if not str(file).startswith(str(WEB.resolve())) or not file.exists():
            return self._send(404, b"not found", "text/plain")
        ctype = {".html": "text/html; charset=utf-8", ".js": "application/javascript",
                 ".css": "text/css", ".png": "image/png"}.get(file.suffix, "application/octet-stream")
        return self._send(200, file.read_bytes(), ctype)

    def do_POST(self):
        path = self.path.split("?")[0]
        try:
            body = self._read_json()
        except Exception:
            return self._send(400, {"error": "bad json"})
        if path == "/api/config":
            cfg = load_config()
            cfg.update({k: body[k] for k in ("root", "username", "mem") if k in body})
            if "download_source" in body:
                cfg["download_source"] = mclaunch.set_source_mode(body["download_source"])
            save_config(cfg)
            apply_download_config(cfg)
            return self._send(200, cfg)
        if path == "/api/check-sources":
            cfg = load_config()
            if SOURCE_CHECK["running"]:
                return self._send(409, {"error": "a source check is already running"})
            SOURCE_CHECK.update(running=True, started=time.strftime("%H:%M:%S"),
                                result=None, error=None)
            threading.Thread(target=run_source_check, args=(Path(cfg["root"]),),
                             daemon=True).start()
            return self._send(200, {"started": True})
        if path == "/api/open-dir":
            cfg = load_config()
            target = str(body.get("target", "")).strip()
            vid = str(body.get("version", "")).strip()
            try:
                folder = dir_target(Path(cfg["root"]), target, vid)
            except ValueError as exc:
                return self._send(400, {"error": str(exc)})
            try:
                if target in ("mods", "saves", "logs", "screenshots"):
                    folder.mkdir(parents=True, exist_ok=True)
            except OSError as exc:
                return self._send(500, {"error": str(exc), "path": str(folder)})
            if not folder.is_dir():
                return self._send(404, {"error": "folder does not exist", "path": str(folder)})
            try:
                open_in_explorer(folder)
            except Exception as exc:  # noqa: BLE001
                return self._send(500, {"error": str(exc), "path": str(folder)})
            return self._send(200, {"opened": str(folder)})

        if path == "/api/sync-profiles":
            cfg = load_config()
            try:
                added = sync_profiles(Path(cfg["root"]))
            except Exception as exc:  # noqa: BLE001
                return self._send(500, {"error": str(exc)})
            return self._send(200, {"added": added, "count": len(added)})

        if path == "/api/install-mrpack":
            cfg = load_config()
            pack = str(body.get("path", "")).strip()
            if not pack:
                return self._send(400, {"error": "path required"})
            pack_path = Path(pack)
            if not pack_path.exists() or pack_path.suffix.lower() != ".mrpack":
                return self._send(400, {"error": "not a .mrpack file"})
            if TASK.snapshot()["phase"] in ("start", "download"):
                return self._send(409, {"error": "a task is running"})

            def run_mrpack():
                with TASK_LOCK:
                    TASK.__init__()
                try:
                    import backend
                    TASK.set(phase="download", message=f"mrpack {pack_path.name}")
                    info = backend.install_mrpack(pack_path, Path(cfg["root"]), TASK)
                    label = f"{info['name']} {info['version']}"
                    if info.get("launch"):
                        label += "|" + info["launch"]
                    TASK.set(phase="done", message=label)
                except Exception as exc:  # noqa: BLE001
                    TASK.set(phase="error", error=str(exc))

            threading.Thread(target=run_mrpack, daemon=True).start()
            return self._send(200, {"started": True})

        if path == "/api/install-jvm":
            cfg = load_config()
            jvm_id = str(body.get("id", "")).strip()
            if not jvm_id:
                return self._send(400, {"error": "id required"})
            if TASK.snapshot()["phase"] in ("start", "download"):
                return self._send(409, {"error": "a task is running"})

            def run_jvm():
                with TASK_LOCK:
                    TASK.__init__()
                try:
                    import backend
                    TASK.set(phase="download", message=f"java {jvm_id}")
                    backend.install_jvm(Path(cfg["root"]), jvm_id, TASK)
                    TASK.set(phase="done", message=jvm_id)
                except Exception as exc:  # noqa: BLE001
                    TASK.set(phase="error", error=str(exc))

            threading.Thread(target=run_jvm, daemon=True).start()
            return self._send(200, {"started": True})

        if path == "/api/install":
            mc = str(body.get("mc", "")).strip()
            loader = str(body.get("loader", "vanilla"))
            version = body.get("loader_version") or body.get("version")
            if not mc:
                return self._send(400, {"error": "mc required"})
            if TASK.snapshot()["phase"] in ("start", "download"):
                return self._send(409, {"error": "a task is running"})
            threading.Thread(target=run_install, args=(mc, loader, version), daemon=True).start()
            return self._send(200, {"started": True})
        if path == "/api/toggle-mod":
            cfg = load_config()
            name = str(body.get("name", "")).strip()
            if not name:
                return self._send(400, {"error": "name required"})
            mods_dir = (Path(cfg["root"]) / "mods").resolve()
            src = (mods_dir / name).resolve()
            try:
                src.relative_to(mods_dir)
            except Exception:  # noqa: BLE001
                return self._send(400, {"error": "invalid name"})
            if not src.is_file() or src.suffix.lower() not in (".jar", ".disabled"):
                return self._send(404, {"error": "not a mod jar"})
            if src.suffix.lower() == ".jar":
                dst = src.with_name(src.name + ".disabled")
            else:
                dst = src.with_name(src.name[: -len(".disabled")])
            if dst.exists():
                return self._send(409, {"error": "target already exists"})
            src.rename(dst)
            return self._send(200, {"name": dst.name, "enabled": dst.suffix.lower() == ".jar"})

        if path == "/api/delete-version":
            cfg = load_config()
            vid = str(body.get("id", "")).strip()
            if not vid:
                return self._send(400, {"error": "id required"})
            import shutil
            vroot = Path(cfg["root"]) / "versions"
            target = vroot / vid
            try:
                target.resolve().relative_to(vroot.resolve())
            except Exception:  # noqa: BLE001
                return self._send(400, {"error": "invalid version id"})
            if not target.is_dir():
                return self._send(404, {"error": "not installed"})
            size = sum(f.stat().st_size for f in target.rglob("*") if f.is_file())
            shutil.rmtree(target)
            return self._send(200, {"deleted": vid, "freed_bytes": size})

        if path == "/api/launch":
            vid = str(body.get("version_id", "")).strip()
            cfg = load_config()
            if not vid:
                return self._send(400, {"error": "version_id required"})
            user = str(body.get("username") or cfg["username"])
            try:
                proc, log = launch(vid, Path(cfg["root"]), user, max_mem=cfg.get("mem", "2G"))
            except Exception as exc:  # noqa: BLE001
                return self._send(500, {"error": str(exc)})
            entry = {"pid": proc.pid, "version": vid, "user": user, "log": str(log),
                     "started": time.strftime("%H:%M:%S")}
            LAUNCHES.append(entry)
            return self._send(200, entry)
        return self._send(404, {"error": "unknown endpoint"})


def main():
    port = int(os.environ.get("LAUNCHER_PORT", "8765"))
    cfg = load_config()
    apply_download_config(cfg)
    print(f"launcher root: {cfg['root']}")
    print(f"launcher UI:   http://127.0.0.1:{port}/")
    print(f"download src:  {cfg.get('download_source', 'auto')}")
    srv = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    if os.environ.get("LAUNCHER_OPEN", "1") == "1":
        threading.Thread(target=lambda: (time.sleep(0.6), webbrowser.open(f"http://127.0.0.1:{port}/")),
                         daemon=True).start()
    srv.serve_forever()


if __name__ == "__main__":
    main()
