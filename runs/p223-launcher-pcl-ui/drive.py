"""p223: drive the web launcher over CDP - select 1.20.6 + vanilla, switch 安装到 to PCL2, click install.

No selenium/websocket package is available, so this speaks just enough RFC6455 and CDP by hand.
Usage: python runs/p223-launcher-pcl-ui/drive.py
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUN = Path(__file__).resolve().parent
EDGE = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")
if not EDGE.exists():
    EDGE = Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe")
PORT = 9333
URL = "http://127.0.0.1:8765/"
profile = ROOT / "work/tmp/p223-edge-profile"
profile.mkdir(parents=True, exist_ok=True)


def http_json(path: str):
    with urllib.request.urlopen(f"http://127.0.0.1:{PORT}{path}", timeout=10) as r:
        return json.loads(r.read())


def new_tab(url: str) -> dict:
    req = urllib.request.Request(f"http://127.0.0.1:{PORT}/json/new?{url}", method="PUT")
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read())


class WS:
    def __init__(self, url: str):
        _, rest = url.split("://", 1)
        hostport, path = rest.split("/", 1)
        host, port = hostport.split(":")
        self.sock = socket.create_connection((host, int(port)), timeout=20)
        key = base64.b64encode(os.urandom(16)).decode()
        req = (f"GET /{path} HTTP/1.1\r\nHost: {hostport}\r\nUpgrade: websocket\r\n"
               f"Connection: Upgrade\r\nSec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n")
        self.sock.sendall(req.encode())
        buf = b""
        while b"\r\n\r\n" not in buf:
            buf += self.sock.recv(4096)
        assert b"101" in buf.split(b"\r\n")[0], buf[:200]
        self.buf = buf.split(b"\r\n\r\n", 1)[1]
        self.sid = 0

    def send(self, obj: dict) -> None:
        raw = json.dumps(obj).encode()
        mask = os.urandom(4)
        header = b"\x81"
        n = len(raw)
        if n < 126:
            header += bytes([0x80 | n])
        elif n < 65536:
            header += bytes([0x80 | 126]) + n.to_bytes(2, "big")
        else:
            header += bytes([0x80 | 127]) + n.to_bytes(8, "big")
        masked = bytes(b ^ mask[i % 4] for i, b in enumerate(raw))
        self.sock.sendall(header + mask + masked)

    def _read(self, n: int) -> bytes:
        while len(self.buf) < n:
            chunk = self.sock.recv(65536)
            if not chunk:
                raise ConnectionError("closed")
            self.buf += chunk
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

    def call(self, method: str, params: dict | None = None, timeout: float = 90.0) -> dict:
        self.sid += 1
        self.send({"id": self.sid, "method": method, "params": params or {}})
        end = time.time() + timeout
        while time.time() < end:
            msg = self.recv()
            if msg.get("id") == self.sid:
                return msg
        raise TimeoutError(method)


def main() -> int:
    proc = subprocess.Popen([str(EDGE), "--headless=new", "--disable-gpu", "--no-first-run",
                             f"--remote-debugging-port={PORT}", f"--user-data-dir={profile}",
                             "about:blank"],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(40):
            try:
                http_json("/json/version")
                break
            except Exception:
                time.sleep(0.5)
        tab = new_tab(URL)
        ws = WS(tab["webSocketDebuggerUrl"])
        ws.call("Page.enable")
        ws.call("Runtime.enable")
        ws.call("Emulation.setDeviceMetricsOverride",
                {"width": 1360, "height": 950, "deviceScaleFactor": 1, "mobile": False})
        time.sleep(2)

        expr = """(async () => {
          const opt = (id, v) => { const e = document.getElementById(id); e.value = v;
            e.dispatchEvent(new Event('change', {bubbles: true})); return e.value; };
          const has = (id, v) => !!document.querySelector('#' + id + ' option[value="' + v + '"]');
          for (let i = 0; i < 60 && !has('mcver', '1.20.6'); i++) await new Promise(r => setTimeout(r, 500));
          const mc = opt('mcver', '1.20.6');
          const loader = opt('loader', 'vanilla');
          const target = opt('target', 'pcl');
          await new Promise(r => setTimeout(r, 1200));
          const hint0 = document.getElementById('pclHint').textContent;
          document.getElementById('install').click();
          let msg = '';
          for (let i = 0; i < 180; i++) {
            await new Promise(r => setTimeout(r, 500));
            msg = document.getElementById('taskmsg').textContent || '';
            if (msg.indexOf('已装进 PCL2') >= 0 || msg.indexOf('错误') === 0) break;
          }
          return { mc, loader, target, hint0, msg,
                   button: document.getElementById('install').textContent };
        })()"""
        r = ws.call("Runtime.evaluate", {"expression": expr, "awaitPromise": True,
                                         "returnByValue": True, "timeout": 120000}, timeout=180)
        val = r.get("result", {}).get("result", {}).get("value") or {"error": r}
        print(json.dumps(val, ensure_ascii=False, indent=2))

        shot = ws.call("Page.captureScreenshot", {"format": "png"})
        data = shot.get("result", {}).get("data")
        if data:
            (RUN / "after-import.png").write_bytes(base64.b64decode(data))
            print("screenshot bytes", len(base64.b64decode(data)))
        ok = "已装进 PCL2" in str(val.get("msg", ""))
        (RUN / "ui-result.json").write_text(json.dumps(val, ensure_ascii=False, indent=2), encoding="utf-8")
        return 0 if ok else 1
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()


if __name__ == "__main__":
    sys.exit(main())
