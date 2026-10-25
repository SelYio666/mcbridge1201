#!/usr/bin/env python3
"""p192: three clients - B actively drains its trash; A rejoins (upstream login reset).

All interactions are probe-driven on the real GLFW callback paths (p191 lesson): B's client
(started with -Dp192.actor=true) aims the in-game mouse at its trash slot and synthesizes a
right-click (take one) and a Delete (empty). A and C only seed their local trash UIs.

Flow: launch A (GridUser), B (TrashB, actor), C (TrashC) -> the server seeds 5/4/3 -> B drains
4 -> 3 (right click) -> empty (Delete) -> kill A (whose server trash is still diamondx5) and
relaunch it -> after rejoin A's server trash must be EMPTY (TrashSlot's own PlayerLoginEvent
reset, upstream design - p65), while C stayed diamondx3 throughout.
"""
from __future__ import annotations

import argparse
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
PROBE = ROOT / "work" / "tmp" / "p192active.jar"
PORT = "25566"
USERS = ("GridUser", "TrashB", "TrashC")

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
    backup = ROOT / "work" / "tmp" / "p192-mod-backup"
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
    shutil.copy2(PROBE, CLIENT_MODS / "p192active.jar")
    for name in ("trashslot-15.1.5+1.21.1.jar", "trashslot-client-empty.jar"):
        (SERVER_MODS / name).unlink(missing_ok=True)
    shutil.copy2(TRASH_JAR, SERVER_MODS / "trashslot-15.1.5+1.21.1.jar")
    for src in (FABRIC_API, BALM):
        dst = SERVER_MODS / src.name
        if src.resolve() != dst.resolve():
            shutil.copy2(src, dst)
    shutil.copy2(PROBE, SERVER_MODS / "p192active.jar")


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


def launch(user: str, log: Path, actor: bool) -> subprocess.Popen:
    cmd, _, _ = mclaunch.build_command(
        "fabric-loader-0.19.5-1.21.1", CLIENT, user, "2G",
        extra_game=["--quickPlayMultiplayer", f"127.0.0.1:{PORT}",
                    "--width", "1280", "--height", "720"])
    if actor:
        # JVM flag before the class: insert right after the memory args (build_command puts
        # -Xmx first). Simplest robust spot: prepend to the java command's tail via env-style
        # is not available; the launcher command starts with java -Xmx..., so inject after
        # the first token.
        idx = 1
        cmd = [cmd[0], "-Dp192.actor=true"] + cmd[idx:]
    with log.open("w", encoding="utf-8", errors="replace") as cout:
        cout.write(" ".join(cmd) + "\n")
        cout.flush()
    return subprocess.Popen(cmd, cwd=str(CLIENT), stdout=log.open("a", encoding="utf-8",
                                                                  errors="replace"),
                            stderr=subprocess.STDOUT)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--timeout", type=int, default=420)
    args = ap.parse_args()
    RUN.mkdir(parents=True, exist_ok=True)
    if not PROBE.exists():
        print(f"missing probe jar: {PROBE}; run build.py first", file=sys.stderr)
        return 2
    setup_mods()
    set_server_config()

    try:
        users = json.loads(read_text(SERVER / "usercache.json") or "[]")
    except ValueError:
        users = []
    for entry in users:
        if entry.get("name") not in USERS:
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
    logs = {u: RUN / f"client-{u.lower()}.log" for u in USERS}
    for log in logs.values():
        log.write_text("", encoding="utf-8")
    procs: dict[str, subprocess.Popen] = {}
    server = None
    try:
        with server_log.open("w", encoding="utf-8", errors="replace") as out:
            server = subprocess.Popen(
                [str(java), "-Xmx2G", "-jar", "fabric-server-launch.jar", "nogui"],
                cwd=str(SERVER), stdout=out, stderr=subprocess.STDOUT)
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

            # Launch A, then B (actor), then C.
            procs["GridUser"] = launch("GridUser", logs["GridUser"], actor=False)
            time.sleep(8)
            procs["TrashB"] = launch("TrashB", logs["TrashB"], actor=True)
            time.sleep(8)
            procs["TrashC"] = launch("TrashC", logs["TrashC"], actor=False)

            # Wait for the seed + B's full action sequence.
            deadline = time.time() + args.timeout
            while time.time() < deadline:
                ser = read_text(server_log)
                b_log = read_text(logs["TrashB"])
                if ("ACTIVE_SEED" in ser and "P192_DELETE" in b_log
                        and any("user=TrashB trash=empty" in line
                                for line in ser.splitlines())):
                    break
                if any(p.poll() is not None for p in procs.values()):
                    break
                time.sleep(2)
            _grab_window(str(RUN / "after-b-drain.png"), procs["TrashB"].pid)

            # A's pre-rejoin state must still be diamondx5.
            ser = read_text(server_log)
            a_before = [line for line in ser.splitlines() if "user=GridUser" in line]
            print("A before rejoin:", a_before[-1] if a_before else "-")

            # Kill and relaunch A (upstream login reset evidence).
            procs["GridUser"].terminate()
            try:
                procs["GridUser"].wait(timeout=10)
            except subprocess.TimeoutExpired:
                procs["GridUser"].kill()
            time.sleep(3)
            print("relaunching GridUser")
            procs["GridUser"] = launch("GridUser", logs["GridUser"], actor=False)
            deadline = time.time() + 120
            rejoined = False
            while time.time() < deadline:
                ser = read_text(server_log)
                joins = [line for line in ser.splitlines() if "ACTIVE_JOIN name=GridUser" in line]
                if len(joins) >= 2:
                    rejoined = True
                    # give the login-reset + a couple of state prints time
                    time.sleep(8)
                    break
                if procs["GridUser"].poll() is not None:
                    break
                time.sleep(2)

            ser = read_text(server_log)
            b_log = read_text(logs["TrashB"])
            c_log = read_text(logs["TrashC"])
            a_states = [line.split("ACTIVE_SERVER ", 1)[1] for line in ser.splitlines()
                        if "user=GridUser" in line]
            b_states = [line.split("ACTIVE_SERVER ", 1)[1] for line in ser.splitlines()
                        if "user=TrashB" in line]
            c_states = [line.split("ACTIVE_SERVER ", 1)[1] for line in ser.splitlines()
                        if "user=TrashC" in line]
            a_had_five = any("trash=minecraft:diamondx5" in s for s in a_states)
            a_reset_after_rejoin = (rejoined and a_states
                                    and all("trash=empty" in s
                                            for s in a_states[-2:]) and a_had_five)
            b_took_one = any("trash=minecraft:diamondx3" in s for s in b_states)
            b_emptied = b_states and "trash=empty" in b_states[-1]
            c_constant = bool(c_states) and all("trash=minecraft:diamondx3" in s
                                                for s in c_states)
            c_client_untouched = bool([l for l in c_log.splitlines()
                                       if "P192_TRASH" in l]) and all(
                "trash=minecraft:diamondx4" in l for l in c_log.splitlines()
                if "P192_TRASH" in l)
            result = {
                "a_states_tail": a_states[-6:],
                "b_states_tail": b_states[-8:],
                "c_states_tail": c_states[-4:],
                "a_had_five": a_had_five,
                "a_rejoined": rejoined,
                "a_reset_after_rejoin": a_reset_after_rejoin,
                "b_took_one": b_took_one,
                "b_emptied": b_emptied,
                "c_constant": c_constant,
                "c_client_untouched": c_client_untouched,
                "server_tail": ser.splitlines()[-14:],
                "b_client_tail": b_log.splitlines()[-12:],
                "c_client_tail": c_log.splitlines()[-10:],
            }
            (RUN / "result.json").write_text(
                json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(json.dumps({k: result[k] for k in
                              ("a_had_five", "a_rejoined", "a_reset_after_rejoin",
                               "b_took_one", "b_emptied", "c_constant",
                               "c_client_untouched")}, ensure_ascii=False))
            ok = (a_reset_after_rejoin and b_took_one and b_emptied and c_constant
                  and c_client_untouched)
            return 0 if ok else 1
    finally:
        for proc in procs.values():
            if proc.poll() is None:
                proc.terminate()
        if server and server.poll() is None:
            server.terminate()
            try:
                server.wait(timeout=15)
            except subprocess.TimeoutExpired:
                server.kill()


if __name__ == "__main__":
    sys.exit(main())
