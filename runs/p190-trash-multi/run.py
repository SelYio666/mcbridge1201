#!/usr/bin/env python3
"""p190: two clients on one dedicated server - per-player TrashSlot isolation.

Server: fabric-1.21.1-server-trashslot (survival) with the patched TrashSlot and the p190 probe,
which seeds the FIRST joiner (GridUser) with 5 diamonds in the trash and the SECOND (TrashB) with
3 diamonds, then reports BOTH players' server-side trash every 2 s.

Clients: GridUser joins first and opens the survival inventory (trash slot visible); TrashB joins
second and does the same. Player A then right-clicks the trash slot (take one, leave four - the
p185 semantics verified for the single-client case) and presses Delete over the trash (p183
semantics: empty). The gate: A's server-side trash follows 5 -> 4 -> 0 while B's server-side and
client-side trash stays at 3 the whole time (per-player isolation, no cross-talk, no broadcast).
"""
from __future__ import annotations

import argparse
import ctypes
import ctypes.wintypes
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUN = Path(__file__).resolve().parent
SERVER = ROOT / "work" / "instances" / "fabric-1.21.1-server-trashslot"
CLIENT = ROOT / "work" / "launcher-e2e"
SERVER_MODS = SERVER / "mods"
CLIENT_MODS = CLIENT / "mods"
FABRIC_API = ROOT / "work" / "instances" / "fabric-1.21.1-server" / "mods" / "fabric-api.jar"
BALM = SERVER_MODS / "balm-fabric-1.21.1.jar"
TRASH_JAR = ROOT / "work" / "client" / "trashslot-client-empty.jar"
PROBE = ROOT / "work" / "tmp" / "trashmulti.jar"
PORT = "25566"
USER_A = "GridUser"
USER_B = "TrashB"

sys.path.insert(0, str(ROOT / "launcher"))
sys.path.insert(0, str(ROOT / "tools"))
import mclaunch  # noqa: E402
from test_launcher_e2e import _grab_window  # noqa: E402


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except FileNotFoundError:
        return ""


def setup_mods() -> None:
    backup = ROOT / "work" / "tmp" / "p190-mod-backup"
    backup.mkdir(parents=True, exist_ok=True)
    for path in SERVER_MODS.glob("*.jar"):
        shutil.copy2(path, backup / path.name)
    for path in CLIENT_MODS.glob("*.jar"):
        shutil.copy2(path, backup / f"client-{path.name}")
    for path in CLIENT_MODS.glob("*.jar"):
        path.unlink()
    shutil.copy2(FABRIC_API, CLIENT_MODS / FABRIC_API.name)
    shutil.copy2(BALM, CLIENT_MODS / BALM.name)
    shutil.copy2(TRASH_JAR, CLIENT_MODS / "trashslot-client-empty.jar")
    shutil.copy2(PROBE, CLIENT_MODS / "trashmulti.jar")
    for name in ("trashslot-15.1.5+1.21.1.jar", "trashslot-client-empty.jar"):
        (SERVER_MODS / name).unlink(missing_ok=True)
    shutil.copy2(TRASH_JAR, SERVER_MODS / "trashslot-15.1.5+1.21.1.jar")
    for src in (FABRIC_API, BALM):
        dst = SERVER_MODS / src.name
        if src.resolve() != dst.resolve():
            shutil.copy2(src, dst)
    shutil.copy2(PROBE, SERVER_MODS / "trashmulti.jar")


def set_server_config() -> None:
    props = SERVER / "server.properties"
    if props.exists():
        shutil.copy2(props, RUN / "server.properties.before")
    settings = {
        "server-port": PORT,
        "difficulty": "normal",
        "gamemode": "survival",
        "force-gamemode": "true",
        "online-mode": "false",
    }
    text = props.read_text(encoding="utf-8", errors="replace") if props.exists() else ""
    lines, seen = [], set()
    for line in text.splitlines():
        key = line.split("=", 1)[0] if "=" in line else ""
        if key in settings:
            lines.append(f"{key}={settings[key]}")
            seen.add(key)
        else:
            lines.append(line)
    for key, value in settings.items():
        if key not in seen:
            lines.append(f"{key}={value}")
    props.write_text("\n".join(lines) + "\n", encoding="utf-8")


def find_window(pid: int) -> int | None:
    user32 = ctypes.windll.user32
    found: list[int] = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    def _enum(hwnd, _lparam):
        if not user32.IsWindowVisible(hwnd):
            return True
        owner = ctypes.c_ulong()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(owner))
        if owner.value == pid:
            found.append(hwnd)
        return True

    user32.EnumWindows(_enum, 0)
    return found[0] if found else None


def focus_until(hwnd: int) -> bool:
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    for _ in range(4):
        flags = 0x0001 | 0x0002 | 0x0040
        user32.SetWindowPos(hwnd, -1, 0, 0, 0, 0, flags)
        user32.ShowWindow(hwnd, 9)
        user32.BringWindowToTop(hwnd)
        fg = user32.GetForegroundWindow()
        fg_thread = user32.GetWindowThreadProcessId(fg, None)
        my_thread = kernel32.GetCurrentThreadId()
        user32.AttachThreadInput(my_thread, fg_thread, True)
        user32.SetForegroundWindow(hwnd)
        user32.AttachThreadInput(my_thread, fg_thread, False)
        if user32.GetForegroundWindow() == hwnd:
            return True
        time.sleep(0.8)
    return False


def right_click() -> None:
    user32 = ctypes.windll.user32
    user32.mouse_event(0x0008, 0, 0, 0, 0)  # RIGHTDOWN
    time.sleep(0.12)
    user32.mouse_event(0x0010, 0, 0, 0, 0)  # RIGHTUP
    time.sleep(0.5)


def press_delete() -> None:
    user32 = ctypes.windll.user32
    extended = 0x0001
    keyup = 0x0002
    user32.keybd_event(0x2E, 0x53, extended, 0)
    time.sleep(0.15)
    user32.keybd_event(0x2E, 0x53, extended | keyup, 0)
    time.sleep(0.5)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--timeout", type=int, default=300)
    args = ap.parse_args()
    RUN.mkdir(parents=True, exist_ok=True)
    if not PROBE.exists():
        print(f"missing probe jar: {PROBE}; run build.py first", file=sys.stderr)
        return 2
    setup_mods()
    set_server_config()

    # Wipe both players so the survival gamemode and the login trash reset apply cleanly.
    try:
        users = json.loads(read_text(SERVER / "usercache.json") or "[]")
    except ValueError:
        users = []
    wanted = {USER_A, USER_B}
    for entry in users:
        if entry.get("name") not in wanted:
            continue
        uid = entry.get("uuid")
        for sub, ext in (("playerdata", ".dat"), ("stats", ".json"), ("advancements", ".json")):
            path = SERVER / "world" / sub / f"{uid}{ext}"
            if path.exists():
                path.unlink()

    java_home = os.environ.get("JAVA_HOME") or str(ROOT.parent / ".toolchain" / "jdk")
    java = Path(java_home) / "bin" / ("java.exe" if os.name == "nt" else "java")
    server_log = RUN / "server.log"
    server_log.write_text("", encoding="utf-8")
    client_a_log = RUN / "client-a.log"
    client_b_log = RUN / "client-b.log"
    for log in (client_a_log, client_b_log):
        log.write_text("", encoding="utf-8")
    client = None
    server = None
    try:
        with server_log.open("w", encoding="utf-8", errors="replace") as out:
            server = subprocess.Popen(
                [str(java), "-Xmx2G", "-jar", "fabric-server-launch.jar", "nogui"],
                cwd=str(SERVER), stdout=out, stderr=subprocess.STDOUT, stdin=subprocess.PIPE)
            deadline = time.time() + 120
            while time.time() < deadline:
                if server.poll() is not None:
                    break
                if "Done (" in read_text(server_log):
                    break
                time.sleep(1)
            if "Done (" not in read_text(server_log):
                print("server did not start; tail:")
                print("\n".join(read_text(server_log).splitlines()[-12:]))
                return 2
            print("server ready")

            def launch(user: str, log: Path) -> subprocess.Popen:
                cmd, _, _ = mclaunch.build_command(
                    "fabric-loader-0.19.5-1.21.1", CLIENT, user, "2G",
                    extra_game=["--quickPlayMultiplayer", f"127.0.0.1:{PORT}",
                                "--width", "1280", "--height", "720"])
                with log.open("w", encoding="utf-8", errors="replace") as cout:
                    cout.write(" ".join(cmd) + "\n")
                    cout.flush()
                return subprocess.Popen(cmd, cwd=str(CLIENT), stdout=log.open("a", encoding="utf-8",
                                                                            errors="replace"),
                                        stderr=subprocess.STDOUT)

            print("launching client A (GridUser)")
            client = launch(USER_A, client_a_log)
            deadline = time.time() + args.timeout
            while time.time() < deadline:
                if "MULTI_JOIN name=GridUser" in read_text(server_log):
                    break
                if client.poll() is not None:
                    break
                time.sleep(1)
            time.sleep(4)
            print("launching client B (TrashB)")
            client_b = launch(USER_B, client_b_log)
            deadline = time.time() + args.timeout
            while time.time() < deadline:
                if "MULTI_JOIN name=TrashB" in read_text(server_log):
                    break
                if client_b.poll() is not None:
                    break
                time.sleep(1)
            # wait for BOTH clients' local trash seed (A and B each show diamondx5)
            deadline = time.time() + args.timeout
            while time.time() < deadline:
                ta = read_text(client_a_log)
                tb = read_text(client_b_log)
                if ("MULTI_CLIENT_SEED" in ta and "trash=minecraft:diamondx5" in ta
                        and "MULTI_CLIENT_SEED" in tb and "trash=minecraft:diamondx5" in tb):
                    break
                time.sleep(1)

            hwnd_a = find_window(client.pid)
            if not hwnd_a:
                print("no client A window", file=sys.stderr)
                return 1
            text_a = read_text(client_a_log)
            geom = None
            for line in text_a.splitlines():
                if "TRASH_CLIENT" in line and "trash=minecraft:diamondx5" in line and "MULTI_CLIENT_SEED" not in line:
                    geom = line
            if not geom:
                print("client A never showed trash=diamondx5; tail:")
                print("\n".join(text_a.splitlines()[-14:]))
                return 1
            print("client A trash state:", geom.split("TRASH_CLIENT ", 1)[1])

            # Player A: right-click the trash (take 1, leave 4 - p185 semantics), then Delete
            # over the trash (empty - p183 semantics). Player B stays untouched the whole time.
            if not focus_until(hwnd_a):
                print("could not focus client A", file=sys.stderr)
                return 1
            # Position the cursor on A's trash slot from the logged geometry.
            geom_line = None
            for line in read_text(client_a_log).splitlines():
                if "TRASH_CLIENT" in line and "trashX=" in line:
                    geom_line = line
            if not geom_line:
                print("no TRASH_CLIENT geometry line", file=sys.stderr)
                return 1
            fields = {}
            for part in geom_line.split("TRASH_CLIENT ", 1)[1].split():
                if "=" in part:
                    k, v = part.split("=", 1)
                    fields[k] = v
            user32 = ctypes.windll.user32
            origin = ctypes.wintypes.POINT(0, 0)
            user32.ClientToScreen(hwnd_a, ctypes.byref(origin))
            gscale = float(fields.get("scale", "2"))
            gx = float(fields["left"]) + float(fields["trashX"]) + 8
            gy = float(fields["top"]) + float(fields["trashY"]) + 8
            trash_px = origin.x + int(gx * gscale)
            trash_py = origin.y + int(gy * gscale)
            print(f"hovering A trash slot at physical=({trash_px},{trash_py})")
            user32.SetCursorPos(trash_px, trash_py)
            time.sleep(1)
            print("right-clicking trash (take one, leave four)")
            right_click()
            time.sleep(3)
            print("pressing Delete over the trash (empty)")
            press_delete()
            time.sleep(3)
            _grab_window(str(RUN / "after.png"), client.pid)

            time.sleep(2.5)  # let the server print the final per-player states
            text_a = read_text(client_a_log)
            text_b = read_text(client_b_log)
            ser = read_text(server_log)
            a_states = [line.split("MULTI_SERVER ", 1)[1] for line in ser.splitlines()
                        if "MULTI_SERVER user=GridUser" in line]
            b_states = [line.split("MULTI_SERVER ", 1)[1] for line in ser.splitlines()
                        if "MULTI_SERVER user=TrashB" in line]
            b_client_states = [line.split("TRASH_CLIENT ", 1)[1]
                               for line in text_b.splitlines() if "TRASH_CLIENT " in line
                               and "MULTI_CLIENT_SEED" not in line]
            a_final = a_states[-1] if a_states else ""
            b_final = b_states[-1] if b_states else ""
            took_one = any("trash=minecraft:diamondx4" in s for s in a_states)
            emptied = bool(a_states) and "trash=empty" in a_states[-1]
            b_constant = all("trash=minecraft:diamondx3" in s for s in b_states)
            b_client_constant = bool(b_client_states) and all(
                "trash=minecraft:diamondx5" in s for s in b_client_states)
            result = {
                "a_server_states": a_states[-8:],
                "b_server_states": b_states[-8:],
                "b_client_states": b_client_states[-6:],
                "a_took_one": took_one,
                "a_emptied": emptied,
                "b_server_constant_diamondx3": b_constant,
                "b_client_constant_diamondx3": b_client_constant,
                "client_tail_a": text_a.splitlines()[-16:],
                "client_tail_b": text_b.splitlines()[-16:],
                "server_tail": ser.splitlines()[-14:],
            }
            (RUN / "result.json").write_text(
                json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(json.dumps({k: result[k] for k in
                              ("a_took_one", "a_emptied", "b_server_constant_diamondx3",
                               "b_client_constant_diamondx3")},
                             ensure_ascii=False))
            return 0 if (took_one and emptied and b_constant and b_client_constant) else 1
    finally:
        for proc in (client, server):
            if proc and proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    proc.kill()


if __name__ == "__main__":
    sys.exit(main())
