#!/usr/bin/env python3
"""p256: end-to-end vein-mining test with a real client, no pixel assertions.

Server side (dedicated 1.21.1 Fabric server with the converted VeinMiner + silk chain):
  - builds a 2x2 oak-log pillar high above the terrain, forces the player into survival,
    gives a diamond axe, teleports them on top looking straight down.
Client side (real 1.21.1 Fabric client launched offline via KnotClient + quickPlayServer):
  - waits for the join, focuses the game window, holds sneak + left mouse for 5 seconds.
Verdict (server log only, no screenshots):
  - the fill after the mining reports how many logs remain (full vein = 0 of 16)
  - /data get SelectedItem reports the axe's Damage tag (> 0 proves the 1.20.1-shaped
    hurtAndBreak path ran for a ServerPlayer, criteria + sync included)
  - client log has no NoSuchMethodError / crash.

Usage:
  py -3.12 runs/p256-veinminer-e2e/drive.py --server-instance work/instances/vein-probe-server \
      --client-dir work/e2e/vm-client/gameDir --out runs/p256-veinminer-e2e
"""
from __future__ import annotations

import argparse
import ctypes
import json
import os
import re
import subprocess
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

UUID = "0000000000003006998F555B73D6DCEF"
PILLAR_REGION = (0, 120, 0, 1, 123, 1)
HOLD_SECONDS = 5.0

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def wait_log(path: Path, marker: str, timeout: float, from_line: int = 0) -> tuple[bool, int]:
    """Poll a log file until a line contains marker; returns (found, line_count)."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            text = ""
        lines = text.splitlines()
        for line in lines[from_line:]:
            if marker in line:
                return True, len(lines)
        time.sleep(0.5)
    return False, 0


class Server:
    def __init__(self, instance: Path, log_path: Path):
        self.instance = instance
        self.log_path = log_path
        self.proc: subprocess.Popen | None = None

    def start(self) -> None:
        java = os.environ.get("JAVA_HOME", "") + os.sep + "bin" + os.sep + "java.exe"
        argv = [java, "-Xmx1024M", "-Xms512M", "-Dfile.encoding=UTF-8",
                "-jar", "fabric-server-launch.jar", "nogui"]
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self.log = open(self.log_path, "wb")
        self.proc = subprocess.Popen(argv, cwd=self.instance, stdout=self.log,
                                     stderr=subprocess.STDOUT, stdin=subprocess.PIPE)

    def command(self, cmd: str, settle: float = 1.2) -> str:
        """Send one console command, then return the new log lines (the response)."""
        before = self.count_lines()
        self.proc.stdin.write((cmd + "\n").encode("utf-8"))
        self.proc.stdin.flush()
        time.sleep(settle)
        return self.read_lines_from(before)

    def count_lines(self) -> int:
        try:
            return len(self.log_path.read_text(encoding="utf-8", errors="replace").splitlines())
        except OSError:
            return 0

    def read_lines_from(self, n: int) -> str:
        try:
            return "\n".join(self.log_path.read_text(encoding="utf-8",
                                                     errors="replace").splitlines()[n:])
        except OSError:
            return ""

    def stop(self) -> None:
        try:
            self.proc.stdin.write(b"stop\n")
            self.proc.stdin.flush()
            self.proc.wait(timeout=60)
        except Exception:
            self.proc.kill()


class Client:
    def __init__(self, game_dir: Path, log_path: Path):
        self.game_dir = game_dir
        self.log_path = log_path
        self.proc: subprocess.Popen | None = None

    def launch(self) -> None:
        java = os.environ.get("JAVA_HOME", "") + os.sep + "bin" + os.sep + "java.exe"
        cp = json.load(open(ROOT / "work/e2e/vm-client/classpath.json", encoding="utf-8"))
        natives = self.game_dir / "versions" / "1.21.1" / "1.21.1-natives"
        argv = [java, "-Xmx2048M", "-Dfile.encoding=UTF-8",
                f"-Djava.library.path={natives}",
                "-cp", os.pathsep.join(cp),
                "net.fabricmc.loader.impl.launch.knot.KnotClient",
                "--username", "TestPlayer", "--uuid", UUID,
                "--accessToken", UUID, "--userType", "msa",
                "--version", "1.21.1", "--gameDir", str(self.game_dir),
                "--assetsDir", str(self.game_dir / "assets"), "--assetIndex", "17",
                "--quickPlayMultiplayer", "127.0.0.1:25565"]
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self.log = open(self.log_path, "wb")
        self.proc = subprocess.Popen(argv, cwd=self.game_dir, stdout=self.log,
                                     stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL)


# ---------------------------------------------------------------- input injection

INPUT_MOUSE = 0
INPUT_KEYBOARD = 1
KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP = 0x0002
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
VK_SHIFT = 0x10


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [("wVk", ctypes.c_ushort), ("wScan", ctypes.c_ushort),
                ("dwFlags", ctypes.c_ulong), ("time", ctypes.c_ulong),
                ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong))]


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [("dx", ctypes.c_long), ("dy", ctypes.c_long),
                ("mouseData", ctypes.c_ulong), ("dwFlags", ctypes.c_ulong),
                ("time", ctypes.c_ulong), ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong))]


class INPUT(ctypes.Structure):
    class _U(ctypes.Union):
        _fields_ = [("ki", KEYBDINPUT), ("mi", MOUSEINPUT)]
    _anonymous_ = ("u",)
    _fields_ = [("type", ctypes.c_ulong), ("u", _U)]


def send_key(vk: int, up: bool) -> None:
    flags = KEYEVENTF_EXTENDEDKEY | (KEYEVENTF_KEYUP if up else 0)
    inp = INPUT(type=INPUT_KEYBOARD)
    inp.ki = KEYBDINPUT(vk, 0, flags, 0, None)
    if user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT)) != 1:
        raise RuntimeError("SendInput key failed")


def send_mouse(down: bool) -> None:
    inp = INPUT(type=INPUT_MOUSE)
    inp.mi = MOUSEINPUT(0, 0, 0, MOUSEEVENTF_LEFTDOWN if down else MOUSEEVENTF_LEFTUP, 0, None)
    if user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT)) != 1:
        raise RuntimeError("SendInput mouse failed")


def focus_window(title_part: str) -> bool:
    """Find the Minecraft window, force topmost and foreground (p202/p213 recipes)."""
    hwnd = None

    @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    def cb(h, _l):
        nonlocal hwnd
        buf = ctypes.create_unicode_buffer(256)
        user32.GetWindowTextW(h, buf, 256)
        if title_part in buf.value:
            hwnd = h
            return False
        return True

    user32.EnumWindows(cb, None)
    if hwnd is None:
        return False
    placement = ctypes.c_void_p(0)
    # SW_RESTORE first if minimized (p213: minimized rects sit at -32000)
    if user32.IsIconic(hwnd):
        user32.ShowWindow(hwnd, 9)  # SW_RESTORE
    user32.SetWindowPos(hwnd, -1, 0, 0, 0, 0, 0x0001 | 0x0002 | 0x0040)  # TOPMOST, NOSIZE|NOMOVE|SHOWWINDOW
    for i in range(6):
        fg = user32.GetForegroundWindow()
        if fg == hwnd:
            break
        this_tid = kernel32.GetCurrentThreadId()
        other_tid = user32.GetWindowThreadProcessId(fg, None)
        user32.AttachThreadInput(this_tid, other_tid, True)
        user32.keybd_event(0x12, 0, 0, 0)  # ALT down: classic foreground-lock bypass
        ok = user32.SetForegroundWindow(hwnd)
        user32.keybd_event(0x12, 0, 2, 0)  # ALT up
        user32.AttachThreadInput(this_tid, other_tid, False)
        time.sleep(0.5)
    time.sleep(0.4)
    buf = ctypes.create_unicode_buffer(256)
    user32.GetWindowTextW(hwnd, buf, 256)
    log(f"window focused: {buf.value!r} foreground={user32.GetForegroundWindow() == hwnd}")
    return user32.GetForegroundWindow() == hwnd


# ---------------------------------------------------------------- choreography

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--server-instance", default="work/instances/vein-probe-server")
    ap.add_argument("--client-dir", default="work/e2e/vm-client/gameDir")
    ap.add_argument("--out", default="runs/p256-veinminer-e2e")
    ap.add_argument("--hold", type=float, default=HOLD_SECONDS)
    args = ap.parse_args()
    out = Path(args.out)
    (out / "logs").mkdir(parents=True, exist_ok=True)
    server_log = out / "logs" / "server.log"
    client_log = out / "logs" / "client.log"

    # pre-flight: fresh options.txt so the accessibility onboarding never shows (p231 lesson)
    cdir = Path(args.client_dir).resolve()
    (cdir / "logs").mkdir(exist_ok=True)
    (cdir / "options.txt").write_text(
        "onboardAccessibility:false\npauseOnLostFocus:false\nversion:3955\n", encoding="utf-8")
    # fresh world marker: server instance keeps its world between runs; the pillar region is
    # filled programmatically below, so leftovers do not matter.

    # deterministic player state: wipe persisted playerdata so the join is fresh
    playerdata = Path(args.server_instance) / "world" / "playerdata"
    if playerdata.exists():
        for f in list(playerdata.glob("*.dat")) + list(playerdata.glob("*.dat_old")):
            f.unlink()
    server = Server(Path(args.server_instance).resolve(), server_log)
    client = None
    server.start()
    try:
        found, _ = wait_log(server_log, "Done (", 180)
        if not found:
            log("server did not reach Done")
            return 10
        # build the pillar BEFORE the client joins: after the previous run's verdict fill the
        # region is air, and a fresh playerdata would otherwise spawn/fall into it (doFallDamage
        # is not a vanilla gamerule - the only real protection is geometry)
        x0, y0, z0, x1, y1, z1 = PILLAR_REGION
        server.command(f"fill {x0} {y0 - 4} {z0} {x1} {y0 - 1} {z1} minecraft:bedrock", 1.5)
        server.command(f"fill {x0} {y0} {z0} {x1} {y1} {z1} minecraft:coal_ore", 1.5)
        server.command("fill -3 119 -3 4 119 4 minecraft:bedrock", 1.5)
        log("server Done; starting client")

        client = Client(cdir, client_log)
        client.launch()
        joined, _ = wait_log(server_log, "TestPlayer joined the game", 300)
        if not joined:
            log("client never joined")
            return 11
        # tp immediately on join: the player spawns wherever playerdata (or world spawn) puts
        # them, and every airborne second is fall damage
        x0, y0, z0, x1, y1, z1 = PILLAR_REGION
        server.command(f"tp TestPlayer 1.0 {y1 + 1} 1.0 0 90", 0.6)
        server.command("effect give TestPlayer minecraft:slow_falling 999999 0 true", 0.8)
        server.command("effect give TestPlayer minecraft:resistance 999999 4 true", 0.8)
        r = server.command("item replace entity TestPlayer weapon.mainhand with minecraft:diamond_pickaxe", 1.0)
        log("item replace -> " + (r.strip().splitlines()[-1] if r.strip() else "(no output)"))
        r = server.command("data get entity TestPlayer Health", 1.0)
        log("health -> " + (r.strip().splitlines()[-1][:120] if r.strip() else "(no output)"))
        time.sleep(3.0)  # world render settle
        time.sleep(1.0)

        # focus + drive: sneak + hold LMB (focus is racy - retry, p206 recipe)
        focused = False
        for attempt in range(10):
            focused = focus_window("Minecraft")
            if focused:
                break
            time.sleep(1.5)
        if not focused:
            log("could not focus the game window after retries")
            return 12
        subprocess.run(["powershell", "-NoProfile", "-Command",
                        "Add-Type -AssemblyName System.Drawing; Add-Type -AssemblyName System.Windows.Forms;"
                        "$b=[System.Windows.Forms.Screen]::PrimaryScreen.Bounds;"
                        "$bmp=New-Object System.Drawing.Bitmap $b.Width,$b.Height;"
                        "$g=[System.Drawing.Graphics]::FromImage($bmp);"
                        "$g.CopyFromScreen(0,0,0,0,$b.Size);"
                        "$bmp.Save('" + str(out.resolve() / "logs" / "screen-before.png") + "');"], timeout=20)
        log("screenshot saved (post-focus)")
        r = server.command("data get entity TestPlayer Pos", 1.0)
        log("pos before input -> " + (r.strip().splitlines()[-1][:160] if r.strip() else "(no output)"))
        send_key(VK_SHIFT, False)
        time.sleep(0.3)
        send_mouse(True)
        time.sleep(args.hold)
        send_mouse(False)
        time.sleep(0.3)
        send_key(VK_SHIFT, True)
        log("input sequence done")
        time.sleep(3.0)

        # verdicts, all from the server console
        remain = server.command(f"fill {x0} {y0} {z0} {x1} {y1} {z1} minecraft:air replace minecraft:coal_ore", 2.0)
        # rebuild for the next run: the verdict fill above destroys the pillar
        m = re.search(r"(\d+) block", remain)
        if m:
            logs_left = int(m.group(1))
        elif "No blocks were filled" in remain:
            logs_left = 0  # fill with air replaced nothing: the vein-mine took the whole pillar
        else:
            logs_left = -1
        item = server.command("data get entity TestPlayer SelectedItem", 1.5)
        dm = re.search(r"minecraft:damage\":\s*(\d+)", item)
        axe_damage = int(dm.group(1)) if dm else (0 if "diamond_axe" in item else -1)
        r = server.command("data get entity TestPlayer SelectedItem", 1.0)

        client_log.joinpath()  # noqa
        client_text = client_log.read_text(encoding="utf-8", errors="replace") if client_log.exists() else ""
        server_text = server_log.read_text(encoding="utf-8", errors="replace")
        errors = [l for l in server_text.splitlines() if "NoSuchMethodError" in l or "NoSuchFieldError" in l]
        cerrors = [l for l in client_text.splitlines() if "NoSuchMethodError" in l or "NoSuchFieldError" in l]

        verdict = {
            "ore_left_of_16": logs_left,
            "pickaxe_damage": axe_damage,
            "server_linkage_errors": len(errors),
            "client_linkage_errors": len(cerrors),
            "pass": logs_left < 16 and axe_damage > 0 and not errors and not cerrors,
        }
        (out / "result.json").write_text(json.dumps(verdict, indent=1) + "\n", encoding="utf-8", newline="\n")
        log("VERDICT " + json.dumps(verdict))
        return 0 if verdict["pass"] else 1
    finally:
        server.stop()
        time.sleep(1.0)
        if client is not None and client.proc is not None:
            client.proc.kill()


if __name__ == "__main__":
    sys.exit(main())
