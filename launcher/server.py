#!/usr/bin/env python3
"""Tiny local web server for the mcbridge launcher GUI."""
from __future__ import annotations

import json
import os
import re
import sys
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from mclaunch import (Progress, find_java, install_fabric, install_forge, install_neoforge,
                      install_vanilla, install_vanilla_launcher_profile, launch, version_manifest)

HERE = Path(__file__).resolve().parent
WEB = HERE / "web"
CONFIG = HERE / "config.json"
TASK = Progress()
TASK_LOCK = threading.Lock()
LAUNCHES = []


def default_root() -> str:
    cands = [
        Path(os.environ.get("APPDATA", "")) / ".minecraft",
        Path(r"D:\我的世界\.minecraft"),
        Path.home() / ".minecraft",
    ]
    for c in cands:
        try:
            if c.exists() and (c / "versions").exists():
                return str(c)
        except OSError:
            continue
    return str(Path.home() / ".mcbridge" / "mc")


def load_config():
    if CONFIG.exists():
        return json.loads(CONFIG.read_text(encoding="utf-8"))
    return {"root": default_root(), "username": "Player", "mem": "2G"}


def save_config(cfg):
    CONFIG.write_text(json.dumps(cfg, indent=2), encoding="utf-8")


MC_ID = re.compile(r"^(?:\d+\.\d+(?:\.\d+)?(?:[-_].*)?|fabric-loader-.+|neoforge-.+|forge-.+)$")


def is_mc_version(name: str) -> bool:
    """Keep real game versions and loader profiles; hide user instances/modpacks."""
    return bool(MC_ID.match(name))


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
            vid = install_fabric(mc, root, TASK)
        elif loader in ("forge", "neoforge"):
            import backend
            if not backend.AVAILABLE:
                raise RuntimeError("Forge/NeoForge 需要 minecraft-launcher-lib：pip install minecraft-launcher-lib")
            install_vanilla_launcher_profile(mc, root)
            java = backend.pick_java(mc) or find_java()
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
            cfg["java"] = find_java()
            return self._send(200, cfg)
        if path == "/api/status":
            cfg = load_config()
            return self._send(200, {"root": cfg["root"], "versions": installed_versions(Path(cfg["root"])),
                                    "java": find_java()})
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
        if path.startswith("/log/"):
            log_path = Path(path[len("/log/"):])
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
            save_config(cfg)
            return self._send(200, cfg)
        if path == "/api/install":
            mc = str(body.get("mc", "")).strip()
            loader = str(body.get("loader", "vanilla"))
            version = body.get("version")
            if not mc:
                return self._send(400, {"error": "mc required"})
            if TASK.snapshot()["phase"] in ("start", "download"):
                return self._send(409, {"error": "a task is running"})
            threading.Thread(target=run_install, args=(mc, loader, version), daemon=True).start()
            return self._send(200, {"started": True})
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
    print(f"launcher root: {cfg['root']}")
    print(f"launcher UI:   http://127.0.0.1:{port}/")
    srv = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    if os.environ.get("LAUNCHER_OPEN", "1") == "1":
        threading.Thread(target=lambda: (time.sleep(0.6), webbrowser.open(f"http://127.0.0.1:{port}/")),
                         daemon=True).start()
    srv.serve_forever()


if __name__ == "__main__":
    main()
