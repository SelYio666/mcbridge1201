"""p227: acceptance of the shipped launcher (dist zip) for the PCL import path.

Starts the packaged launcher on port 8772, then drives the shipped UI over CDP:
select 1.20.6 + vanilla + 安装到 PCL2, click, wait for the 已装进 PCL2 message.
"""
from __future__ import annotations

import base64
import json
import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUN = Path(__file__).resolve().parent
DIST = ROOT / "dist" / "mcbridge-launcher-0.5.10.zip"
PKG = ROOT / "work" / "tmp" / "p227-pkg"
PORT = 8772
EDGE = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")
if not EDGE.exists():
    EDGE = Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe")
URL = f"http://127.0.0.1:{PORT}/"


def get_json(url: str):
    with urllib.request.urlopen(url, timeout=10) as r:
        return json.loads(r.read())


class WS:
    def __init__(self, url: str):
        _, rest = url.split("://", 1)
        hostport, path = rest.split("/", 1)
        host, port = hostport.split(":")
        self.sock = socket.create_connection((host, int(port)), timeout=30)
        key = base64.b64encode(os.urandom(16)).decode()
        req = (f"GET /{path} HTTP/1.1\r\nHost: {hostport}\r\nUpgrade: websocket\r\n"
               f"Connection: Upgrade\r\nSec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n")
        self.sock.sendall(req.encode())
        buf = b""
        while b"\r\n\r\n" not in buf:
            buf += self.sock.recv(4096)
        assert b"101" in buf.split(b"\r\n")[0], buf[:160]
        self.buf = buf.split(b"\r\n\r\n", 1)[1]
        self.sid = 0

    def send(self, obj: dict) -> None:
        raw = json.dumps(obj).encode()
        mask = os.urandom(4)
        head = b"\x81"
        n = len(raw)
        if n < 126:
            head += bytes([0x80 | n])
        elif n < 65536:
            head += bytes([0x80 | 126]) + n.to_bytes(2, "big")
        else:
            head += bytes([0x80 | 127]) + n.to_bytes(8, "big")
        self.sock.sendall(head + mask + bytes(b ^ mask[i % 4] for i, b in enumerate(raw)))

    def _read(self, n: int) -> bytes:
        while len(self.buf) < n:
            self.buf += self.sock.recv(65536)
        out, self.buf = self.buf[:n], self.buf[n:]
        return out

    def recv(self) -> dict:
        while True:
            b0, b1 = self._read(2)
            n = b1 & 0x7F
            if n == 126:
                n = int.from_bytes(self._read(2), "big")
            elif n == 127:
                n = int.from_bytes(self._read(8), "big")
            payload = self._read(n)
            if b0 & 0x0F == 1:
                return json.loads(payload)

    def call(self, method: str, params: dict | None = None, timeout: float = 120.0) -> dict:
        self.sid += 1
        self.send({"id": self.sid, "method": method, "params": params or {}})
        end = time.time() + timeout
        while time.time() < end:
            msg = self.recv()
            if msg.get("id") == self.sid:
                return msg
        raise TimeoutError(method)


def main() -> int:
    if PKG.exists():
        shutil.rmtree(PKG)
    PKG.mkdir(parents=True)
    with zipfile.ZipFile(DIST) as z:
        z.extractall(PKG)
    root = next(PKG.iterdir())
    print("ships:", DIST.name, "->", root.name, flush=True)

    env = dict(os.environ)
    env["LAUNCHER_PORT"] = str(PORT)
    env["LAUNCHER_OPEN"] = "0"
    server = subprocess.Popen([str(root / "python" / "python.exe"), "bootstrap.py"],
                              cwd=str(root), env=env,
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    edge = None
    try:
        for _ in range(40):
            time.sleep(0.5)
            try:
                status = get_json(URL + "api/status")
                break
            except Exception:
                status = None
        print("api/status root:", status and status.get("root"), flush=True)
        pcl = get_json(URL + "api/pcl")
        print("api/pcl:", json.dumps(pcl, ensure_ascii=False), flush=True)

        profile = ROOT / "work/tmp/p227-edge-profile"
        profile.mkdir(parents=True, exist_ok=True)
        edge = subprocess.Popen([str(EDGE), "--headless=new", "--disable-gpu", "--no-first-run",
                                 "--remote-debugging-port=9333", f"--user-data-dir={profile}",
                                 "about:blank"],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(40):
            try:
                get_json("http://127.0.0.1:9333/json/version")
                break
            except Exception:
                time.sleep(0.5)
        req = urllib.request.Request(f"http://127.0.0.1:9333/json/new?{URL}", method="PUT")
        with urllib.request.urlopen(req, timeout=10) as r:
            tab = json.loads(r.read())
        ws = WS(tab["webSocketDebuggerUrl"])
        ws.call("Page.enable")
        ws.call("Runtime.enable")
        ws.call("Emulation.setDeviceMetricsOverride",
                {"width": 1360, "height": 950, "deviceScaleFactor": 1, "mobile": False})
        time.sleep(2)

        expr = """(async () => {
          const has = (id, v) => !!document.querySelector('#' + id + ' option[value="' + v + '"]');
          for (let i = 0; i < 60 && !has('mcver', '1.20.6'); i++) await new Promise(r => setTimeout(r, 500));
          const opt = (id, v) => { const e = document.getElementById(id); e.value = v;
            e.dispatchEvent(new Event('change', {bubbles: true})); return e.value; };
          const rec = { mc: opt('mcver', '1.20.6'), loader: opt('loader', 'vanilla'),
                        target: opt('target', 'pcl') };
          await new Promise(r => setTimeout(r, 1200));
          rec.hint = document.getElementById('pclHint').textContent;
          document.getElementById('install').click();
          rec.msg = '';
          for (let i = 0; i < 180; i++) {
            await new Promise(r => setTimeout(r, 500));
            rec.msg = document.getElementById('taskmsg').textContent || '';
            if (rec.msg.indexOf('已装进 PCL2') >= 0 || rec.msg.indexOf('错误') === 0) break;
          }
          rec.button = document.getElementById('install').textContent;
          return rec;
        })()"""
        res = ws.call("Runtime.evaluate", {"expression": expr, "awaitPromise": True,
                                           "returnByValue": True}, timeout=180)
        val = res.get("result", {}).get("result", {}).get("value") or {"error": res}
        print(json.dumps(val, ensure_ascii=False, indent=2), flush=True)
        shot = ws.call("Page.captureScreenshot", {"format": "png"})
        data = shot.get("result", {}).get("data")
        if data:
            (RUN / "packaged-after-import.png").write_bytes(base64.b64decode(data))
        out = {"package": DIST.name, "api_status_root": status and status.get("root"),
               "api_pcl": pcl, "ui": val}
        (RUN / "packaged-result.json").write_text(json.dumps(out, ensure_ascii=False, indent=2),
                                                 encoding="utf-8")
        ok = ("已装进 PCL2" in str(val.get("msg", ""))
              and bool(pcl.get("dir")))
        return 0 if ok else 1
    finally:
        if edge and edge.poll() is None:
            edge.terminate()
        if server.poll() is None:
            server.terminate()
            try:
                server.wait(timeout=10)
            except subprocess.TimeoutExpired:
                server.kill()


if __name__ == "__main__":
    sys.exit(main())
