#!/usr/bin/env python3
"""p203: two clients fire a trash operation in the same server tick.

p190/p192 proved that trash operations taken one after another stay isolated. What was never
tested is two of them landing on the server at the same moment, which is the only case where a
shared/static server-side trash state would show up as cross-talk.

Design notes:

* the measurement is taken SERVER side. "Concurrent" means "same server tick", and only the
  server can say that; wall-clock timestamps cannot, because 2 ms can straddle a tick boundary
  and 40 ms can sit inside one. probes/p203-trash-concurrent/mixin/PacketMixin stamps every
  serverbound custom payload with the probe's own tick counter.
* the two operations are deliberately different (A deletes 5 -> empty, B takes one 4 -> 3), so a
  leaked packet would move the wrong number to a wrong value instead of looking plausible.
* firing is armed by a file written only after BOTH clients report READY, and each client
  busy-spins the last 60 ms on its client thread, so the two firings sit milliseconds apart
  instead of a tick apart.
"""
from __future__ import annotations

import argparse
import json
import os
import re
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
PROBE = ROOT / "work" / "tmp" / "p203concurrent.jar"
FIRE_FILE = ROOT / "work" / "tmp" / "p203-fire.txt"
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
    backup = ROOT / "work" / "tmp" / "p203-mod-backup"
    backup.mkdir(parents=True, exist_ok=True)
    for path in SERVER_MODS.glob("*.jar"):
        shutil.copy2(path, backup / path.name)
    for path in CLIENT_MODS.glob("*.jar"):
        shutil.copy2(path, backup / f"client-{path.name}")
        path.unlink()
    shutil.copy2(FABRIC_API, CLIENT_MODS / FABRIC_API.name)
    shutil.copy2(BALM, CLIENT_MODS / BALM.name)
    shutil.copy2(TRASH_JAR, CLIENT_MODS / "trashslot-client-empty.jar")
    shutil.copy2(PROBE, CLIENT_MODS / PROBE.name)
    for name in ("trashslot-15.1.5+1.21.1.jar", "trashslot-client-empty.jar",
                 PROBE.name, "p192active.jar"):
        (SERVER_MODS / name).unlink(missing_ok=True)
    shutil.copy2(TRASH_JAR, SERVER_MODS / "trashslot-15.1.5+1.21.1.jar")
    for src in (FABRIC_API, BALM):
        dst = SERVER_MODS / src.name
        if src.resolve() != dst.resolve():
            shutil.copy2(src, dst)
    shutil.copy2(PROBE, SERVER_MODS / PROBE.name)


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


def launch(user: str, log: Path, role: str, seed: int, action: str) -> subprocess.Popen:
    cmd, _, _ = mclaunch.build_command(
        "fabric-loader-0.19.5-1.21.1", CLIENT, user, "2G",
        extra_game=["--quickPlayMultiplayer", f"127.0.0.1:{PORT}",
                    "--width", "1280", "--height", "720"])
    props = [f"-Dp203.role={role}", f"-Dp203.seed={seed}", f"-Dp203.action={action}",
             f"-Dp203.fireFile={FIRE_FILE}"]
    cmd = [cmd[0]] + props + cmd[1:]
    with log.open("w", encoding="utf-8", errors="replace") as cout:
        cout.write(" ".join(cmd) + "\n")
    return subprocess.Popen(cmd, cwd=str(CLIENT),
                            stdout=log.open("a", encoding="utf-8", errors="replace"),
                            stderr=subprocess.STDOUT)


SET = re.compile(r"P203_SET side=(?P<side>\S+) thread=(?P<thread>.+?) tick=(?P<tick>-?\d+) "
                 r"wall=(?P<wall>\d+) seeding=(?P<seeding>\w+) user=(?P<user>\S+) "
                 r"stack=(?P<stack>\S+)")
S2C = re.compile(r"P203_S2C thread=(?P<thread>.+?) tick=(?P<tick>-?\d+) wall=(?P<wall>\d+) "
                 r"message=(?P<message>\S+)")


def parse_mutations(text: str) -> list[dict]:
    """Server-side trash writes, excluding the probe's own seed."""
    out = []
    for line in text.splitlines():
        m = SET.search(line)
        if not m:
            continue
        item = m.groupdict()
        if item["side"] != "SERVER" or item["seeding"] == "true":
            continue
        item["tick"] = int(item["tick"])
        item["wall"] = int(item["wall"])
        out.append(item)
    return out


def parse_serverbound(text: str) -> list[dict]:
    out = []
    for line in text.splitlines():
        m = S2C.search(line)
        if m:
            item = m.groupdict()
            item["tick"] = int(item["tick"])
            item["wall"] = int(item["wall"])
            out.append(item)
    return out


def states(text: str, user: str) -> list[str]:
    return [line.split(f"user={user} ", 1)[1].strip() for line in text.splitlines()
            if "P203_SERVER " in line and f"user={user} " in line]


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
    FIRE_FILE.unlink(missing_ok=True)

    try:
        users = json.loads(read_text(SERVER / "usercache.json") or "[]")
    except ValueError:
        users = []
    for entry in users:
        if entry.get("name") not in (USER_A, USER_B):
            continue
        uid = entry.get("uuid")
        for sub, ext in (("playerdata", ".dat"), ("stats", ".json"), ("advancements", ".json")):
            path = SERVER / "world" / sub / f"{uid}{ext}"
            if path.exists():
                path.unlink()

    java_home = os.environ.get("JAVA_HOME") or str(ROOT.parent / ".toolchain" / "jdk")
    java = Path(java_home) / "bin" / ("java.exe" if os.name == "nt" else "java")
    server_log = RUN / "server.log"
    log_a = RUN / "client-a.log"
    log_b = RUN / "client-b.log"
    for path in (server_log, log_a, log_b):
        path.write_text("", encoding="utf-8")
    procs: dict[str, subprocess.Popen] = {}
    server = None
    try:
        with server_log.open("w", encoding="utf-8", errors="replace") as out:
            server = subprocess.Popen(
                [str(java), "-Xmx2G", "-jar", "fabric-server-launch.jar", "nogui"],
                cwd=str(SERVER), stdout=out, stderr=subprocess.STDOUT)
            deadline = time.time() + 120
            while time.time() < deadline:
                if server.poll() is not None or "Done (" in read_text(server_log):
                    break
                time.sleep(1)
            if "Done (" not in read_text(server_log):
                print("server did not start; tail:")
                print("\n".join(read_text(server_log).splitlines()[-12:]))
                return 2
            print("server ready")
            print("mods:", sorted(p.name for p in SERVER_MODS.glob("*.jar")))

            procs[USER_A] = launch(USER_A, log_a, "A", 5, "delete")
            time.sleep(8)
            procs[USER_B] = launch(USER_B, log_b, "B", 4, "take")

            # Both clients must be aimed and seeded before the instant is handed out.
            deadline = time.time() + args.timeout
            ready = False
            while time.time() < deadline:
                if "P203_READY" in read_text(log_a) and "P203_READY" in read_text(log_b):
                    ready = True
                    break
                if any(p.poll() is not None for p in procs.values()):
                    break
                time.sleep(2)
            print("both ready:", ready)
            if not ready:
                print("A tail:", read_text(log_a).splitlines()[-8:])
                print("B tail:", read_text(log_b).splitlines()[-8:])

            if ready:
                # Give the server seed + a settle margin, then hand out one shared instant.
                time.sleep(3)
                fires = int(time.time() * 1000) + 3000
                FIRE_FILE.write_text(str(fires) + "\n", encoding="utf-8")
                print("armed:", fires)
                deadline = time.time() + 90
                while time.time() < deadline:
                    if "P203_FIRE" in read_text(log_a) and "P203_FIRE" in read_text(log_b):
                        break
                    if any(p.poll() is not None for p in procs.values()):
                        break
                    time.sleep(1)
                time.sleep(5)
                try:
                    _grab_window(str(RUN / "after-concurrent.png"), procs[USER_A].pid)
                except Exception as exc:  # screenshot is a convenience, not the evidence
                    print("screenshot skipped:", exc)

            ser = read_text(server_log)
            a_log = read_text(log_a)
            b_log = read_text(log_b)
            mutations_all = parse_mutations(ser)
            serverbound_all = parse_serverbound(ser)
            # The first writes after a join are TrashSlot's own login reset (EMPTY, p65), not the
            # operation under test, so the window is opened at the fire instant handed to the
            # clients. Everything before it is reported separately instead of being silently used.
            fire_instant = (int(read_text(FIRE_FILE).strip())
                            if read_text(FIRE_FILE).strip() else 0)
            window = (fire_instant - 500, fire_instant + 5000)
            mutations = [m for m in mutations_all if window[0] <= m["wall"] <= window[1]]
            serverbound = [m for m in serverbound_all if window[0] <= m["wall"] <= window[1]]
            pre_fire = [m for m in mutations_all if m["wall"] < window[0]]
            mut_a = next((m for m in mutations if m["user"] == USER_A), None)
            mut_b = next((m for m in mutations if m["user"] == USER_B), None)
            same_tick = bool(mut_a and mut_b and mut_a["tick"] == mut_b["tick"])
            wall_delta = abs(mut_a["wall"] - mut_b["wall"]) if mut_a and mut_b else None
            s2c_tick = bool(len(serverbound) >= 2
                            and serverbound[0]["tick"] == serverbound[1]["tick"])
            a_write_empty = bool(mut_a and mut_a["stack"] == "empty")
            b_write_three = bool(mut_b and mut_b["stack"] == "minecraft:diamondx3")

            a_states = states(ser, USER_A)
            b_states = states(ser, USER_B)
            a_seeded = any("trash=minecraft:diamondx5" in s for s in a_states)
            b_seeded = any("trash=minecraft:diamondx4" in s for s in b_states)
            a_after = a_states[-1] if a_states else ""
            b_after = b_states[-1] if b_states else ""
            a_emptied = a_after.endswith("trash=empty")
            b_took_one = b_after.endswith("trash=minecraft:diamondx3")
            a_client_moved = any("P203_TRASH role=A" in line and "trash=empty" in line
                                 for line in a_log.splitlines())
            b_client_moved = any("P203_TRASH role=B" in line and "trash=minecraft:diamondx3" in line
                                 for line in b_log.splitlines())
            b_carried = any("carried=minecraft:diamondx1" in line for line in b_log.splitlines()
                            if "P203_TRASH role=B" in line)
            fire_a = [line for line in a_log.splitlines() if "P203_FIRE" in line]
            fire_b = [line for line in b_log.splitlines() if "P203_FIRE" in line]
            # Both writes must be taken on the server thread, not on a netty worker.
            on_server_thread = bool(mut_a and mut_b
                                    and mut_a["thread"].startswith("Server thread")
                                    and mut_b["thread"].startswith("Server thread"))

            checks = {
                "both_ready": ready,
                "both_fired": bool(fire_a and fire_b),
                "server_saw_both_writes": bool(mut_a and mut_b),
                "a_write_is_empty": a_write_empty,
                "b_write_is_three": b_write_three,
                "same_server_tick": same_tick,
                "packet_and_write_same_tick": s2c_tick and same_tick,
                "writes_on_server_thread": on_server_thread,
                "a_seeded_five": a_seeded,
                "b_seeded_four": b_seeded,
                "a_emptied": a_emptied,
                "b_took_exactly_one": b_took_one,
                "a_client_shows_empty": a_client_moved,
                "b_client_shows_three": b_client_moved,
                "b_cursor_holds_one": b_carried,
            }
            result = {
                "fire_instant_ms": fire_instant or None,
                "window_ms": window,
                "fire_lines_a": fire_a[:2],
                "fire_lines_b": fire_b[:2],
                "mutation_a": mut_a,
                "mutation_b": mut_b,
                "mutations_after_fire": mutations,
                "mutations_before_fire": pre_fire,
                "same_server_tick": same_tick,
                "wall_delta_ms": wall_delta,
                "serverbound_stamps": serverbound,
                "serverbound_same_tick": s2c_tick if serverbound else None,
                "a_states_tail": a_states[-4:],
                "b_states_tail": b_states[-4:],
                "checks": checks,
                "server_tail": ser.splitlines()[-16:],
                "a_tail": a_log.splitlines()[-10:],
                "b_tail": b_log.splitlines()[-10:],
            }
            (RUN / "result.json").write_text(
                json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(json.dumps({"same_server_tick": same_tick, "wall_delta_ms": wall_delta,
                              "mutation_a": mut_a, "mutation_b": mut_b},
                             ensure_ascii=False))
            print(json.dumps(checks, ensure_ascii=False, indent=2))
            return 0 if all(checks.values()) else 1
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
