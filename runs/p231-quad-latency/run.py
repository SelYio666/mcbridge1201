#!/usr/bin/env python3
"""p231: four clients, four independent game directories, one latency proxy, one shared instant.

p190/p192/p203 ran two or three clients out of ONE shared game directory (work/launcher-e2e), and
p203's loopback measurement (fire -> server write = 4 ms) is the latency baseline. What this round
adds, still on one machine:

* four clients, each in its own game directory (junctions to the shared assets/libraries/versions/
  .fabric blobs, own mods/saves/logs) - the "real double-launch" shape the handover asked for;
* every client connects through latency_proxy.py, which delays each direction by --delay-ms
  (default 50), so the client-server path is no longer bare loopback. This is synthetic latency;
  it is NOT a second machine, and the README says so;
* four operations fired at one shared epoch through p203's file-armed spin mechanism, with four
  distinct outcomes (A deletes 5 -> empty, B takes one from 4 -> 3, C takes one from 3 -> 2,
  D takes one from 2 -> 1), so a leaked packet writes a wrong value or leaves a user without
  its write instead of looking plausible.

Cross-machine latency on real hardware stays open; this closes what one machine can close.
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
SERVER_MODS = SERVER / "mods"
BASE_CLIENT = ROOT / "work" / "launcher-e2e"
FABRIC_API = ROOT / "work" / "instances" / "fabric-1.21.1-server" / "mods" / "fabric-api.jar"
BALM = SERVER_MODS / "balm-fabric-1.21.1.jar"
TRASH_JAR = ROOT / "work" / "client" / "trashslot-client-empty.jar"
PROBE = ROOT / "work" / "tmp" / "p231quad.jar"
FIRE_FILE = ROOT / "work" / "tmp" / "p231-fire.txt"
PORT_SERVER = 25566
PORT_PROXY = 23110
SHARED_DIRS = (".fabric", "assets", "libraries", "versions")

# user, role label, local+server seed, action, expected server write after the op
PLAYERS = [
    ("GridUser", "A", 5, "delete", "empty"),
    ("TrashB", "B", 4, "take", "minecraft:diamondx3"),
    ("TrashC", "C", 3, "take", "minecraft:diamondx2"),
    ("TrashD", "D", 2, "take", "minecraft:diamondx1"),
]

sys.path.insert(0, str(ROOT / "launcher"))
sys.path.insert(0, str(ROOT / "tools"))
import mclaunch  # noqa: E402

SET = re.compile(r"P231_SET side=(?P<side>\S+) thread=(?P<thread>.+?) tick=(?P<tick>-?\d+) "
                 r"wall=(?P<wall>\d+) seeding=(?P<seeding>\w+) user=(?P<user>\S+) "
                 r"stack=(?P<stack>\S+)")
S2C = re.compile(r"P231_S2C thread=(?P<thread>.+?) tick=(?P<tick>-?\d+) wall=(?P<wall>\d+) "
                 r"message=(?P<message>\S+)")
PROXY_CONN = re.compile(r"P231_PROXY conn=(\d+) close upBytes=(\d+) downBytes=(\d+)")
PROXY_TRAFFIC = re.compile(r"P231_PROXY conn=(\d+) traffic dir=(\w+) bytes=(\d+)")
PROXY_OPEN = re.compile(r"P231_PROXY listening=(\S+)")


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except FileNotFoundError:
        return ""


def make_junction(link: Path, target: Path) -> None:
    subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(target)],
                   check=True, capture_output=True)


def make_game_dirs() -> dict[str, Path]:
    dirs: dict[str, Path] = {}
    for _, role, _, _, _ in PLAYERS:
        gd = ROOT / "work" / "tmp" / f"p231-gamedir-{role.lower()}"
        if gd.exists():
            shutil.rmtree(gd)
        gd.mkdir(parents=True)
        for share in SHARED_DIRS:
            src = BASE_CLIENT / share
            if not src.exists():
                raise RuntimeError(f"shared client dir missing: {src}")
            make_junction(gd / share, src)
        (gd / "mods").mkdir()
        for jar in (FABRIC_API, BALM, TRASH_JAR, PROBE):
            shutil.copy2(jar, gd / "mods" / jar.name)
        # A fresh gameDir shows the accessibility-onboarding screen on first boot, and quickplay
        # will not connect behind it (second attempt stalled exactly before "Connecting to").
        # The shared install's options.txt already carries onboardAccessibility:false.
        options = BASE_CLIENT / "options.txt"
        if options.exists():
            shutil.copy2(options, gd / "options.txt")
        dirs[role] = gd
    return dirs


def setup_server_mods() -> Path:
    backup = ROOT / "work" / "tmp" / "p231-mod-backup"
    # The backup keeps the FIRST-SEEN state, not the current one: a killed run leaves the probe
    # jar in place, and re-backing up on every attempt would replace the original set with the
    # polluted one.
    if not backup.exists():
        backup.mkdir(parents=True, exist_ok=True)
        for path in SERVER_MODS.glob("*.jar"):
            shutil.copy2(path, backup / path.name)
    for name in ("trashslot-15.1.5+1.21.1.jar", "trashslot-client-empty.jar",
                 "p203concurrent.jar", "p231quad.jar", "p192active.jar"):
        (SERVER_MODS / name).unlink(missing_ok=True)
    for src in (FABRIC_API, BALM):
        dst = SERVER_MODS / src.name
        if src.resolve() != dst.resolve():
            shutil.copy2(src, dst)
    shutil.copy2(TRASH_JAR, SERVER_MODS / "trashslot-15.1.5+1.21.1.jar")
    shutil.copy2(PROBE, SERVER_MODS / PROBE.name)
    return backup


def restore_server_mods(backup: Path) -> None:
    if not backup.exists():
        return
    for path in list(SERVER_MODS.glob("*.jar")):
        if not (backup / path.name).exists():
            path.unlink(missing_ok=True)
    for path in backup.glob("*.jar"):
        dst = SERVER_MODS / path.name
        if not dst.exists() or dst.read_bytes() != path.read_bytes():
            shutil.copy2(path, dst)


def set_server_config() -> None:
    props = SERVER / "server.properties"
    if props.exists() and not (RUN / "server.properties.before").exists():
        shutil.copy2(props, RUN / "server.properties.before")
    settings = {
        "server-port": str(PORT_SERVER),
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


def restore_server_config() -> None:
    backup = RUN / "server.properties.before"
    props = SERVER / "server.properties"
    if backup.exists() and props.exists():
        shutil.copy2(backup, props)


def launch_client(user: str, role: str, seed: int, action: str, gd: Path,
                  log: Path, mem: str) -> subprocess.Popen:
    # Four clients share the box with whatever the user is running: small heap, SerialGC (no G1
    # region overhead) and C1-only JIT keep the resident set near the heap and give the join
    # phase room even when free physical memory is under 1 GB.
    cmd, _, _ = mclaunch.build_command(
        "fabric-loader-0.19.5-1.21.1", gd, user, mem,
        extra_jvm=["-XX:+UseSerialGC", "-XX:TieredStopAtLevel=1"],
        extra_game=["--quickPlayMultiplayer", f"127.0.0.1:{PORT_PROXY}",
                    "--width", "1280", "--height", "720"])
    props = [f"-Dp231.role={role}", f"-Dp231.seed={seed}", f"-Dp231.action={action}",
             f"-Dp231.fireFile={FIRE_FILE}"]
    cmd = [cmd[0]] + props + cmd[1:]
    with log.open("w", encoding="utf-8", errors="replace") as cout:
        cout.write(" ".join(cmd) + "\n")
    return subprocess.Popen(cmd, cwd=str(gd),
                            stdout=log.open("a", encoding="utf-8", errors="replace"),
                            stderr=subprocess.STDOUT)


def parse_mutations(text: str) -> list[dict]:
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
            if "P231_SERVER " in line and f"user={user} " in line]


def wait_for_listening(proxy_log: Path, deadline_s: float = 15) -> bool:
    deadline = time.time() + deadline_s
    while time.time() < deadline:
        if f"P231_PROXY listening=127.0.0.1:{PORT_PROXY}" in read_text(proxy_log):
            return True
        time.sleep(0.3)
    return False


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Four clients in four game dirs through a delaying proxy, one shared instant.")
    parser.add_argument("--timeout", type=int, default=900)
    parser.add_argument("--delay-ms", type=int, default=50,
                        help="per-direction proxy delay in milliseconds")
    parser.add_argument("--client-mem", default="768M",
                        help="client heap; the first 2G attempt paged the box into a stall")
    parser.add_argument("--server-mem", default="512M")
    args = parser.parse_args()
    RUN.mkdir(parents=True, exist_ok=True)
    if not PROBE.exists():
        print(f"missing probe jar: {PROBE}; run build.py first", file=sys.stderr)
        return 2
    if not BASE_CLIENT.exists():
        print(f"missing base client install: {BASE_CLIENT}", file=sys.stderr)
        return 2

    backup = setup_server_mods()
    set_server_config()
    FIRE_FILE.unlink(missing_ok=True)
    try:
        users = json.loads(read_text(SERVER / "usercache.json") or "[]")
    except ValueError:
        users = []
    names = [p[0] for p in PLAYERS]
    for entry in users:
        if entry.get("name") not in names:
            continue
        uid = entry.get("uuid")
        for sub, ext in (("playerdata", ".dat"), ("stats", ".json"), ("advancements", ".json")):
            path = SERVER / "world" / sub / f"{uid}{ext}"
            if path.exists():
                path.unlink()

    game_dirs = make_game_dirs()
    proxy_log = RUN / "proxy.log"
    proxy_log.write_text("", encoding="utf-8")
    proxy = subprocess.Popen(
        [sys.executable, str(RUN / "latency_proxy.py"),
         "--listen", f"127.0.0.1:{PORT_PROXY}",
         "--target", f"127.0.0.1:{PORT_SERVER}",
         "--delay-ms", str(args.delay_ms), "--log", str(proxy_log)],
        stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    if not wait_for_listening(proxy_log):
        print("proxy did not start; tail:")
        print(read_text(proxy_log))
        proxy.terminate()
        return 2
    print(f"proxy listening on 127.0.0.1:{PORT_PROXY}, delay {args.delay_ms} ms each direction")

    java_home = os.environ.get("JAVA_HOME") or str(ROOT.parent / ".toolchain" / "jdk")
    java = Path(java_home) / "bin" / ("java.exe" if os.name == "nt" else "java")
    server_log = RUN / "server.log"
    client_logs = {role: RUN / f"client-{role.lower()}.log" for _, role, _, _, _ in PLAYERS}
    server_log.write_text("", encoding="utf-8")
    for path in client_logs.values():
        path.write_text("", encoding="utf-8")

    procs: dict[str, subprocess.Popen] = {}
    server = None
    all_checks: dict[str, bool] = {}
    result: dict = {}
    try:
        with server_log.open("w", encoding="utf-8", errors="replace") as out:
            server = subprocess.Popen(
                [str(java), f"-Xmx{args.server_mem}", "-XX:+UseSerialGC",
                 "-XX:TieredStopAtLevel=1", "-jar", "fabric-server-launch.jar",
                 "nogui"],
                cwd=str(SERVER), stdout=out, stderr=subprocess.STDOUT)
            deadline = time.time() + 180
            while time.time() < deadline:
                if server.poll() is not None or "Done (" in read_text(server_log):
                    break
                time.sleep(1)
            if "Done (" not in read_text(server_log):
                print("server did not start; tail:")
                print("\n".join(read_text(server_log).splitlines()[-12:]))
                return 2
            print("server ready; mods:", sorted(p.name for p in SERVER_MODS.glob("*.jar")))

            for user, role, seed, action, _ in PLAYERS:
                procs[user] = launch_client(user, role, seed, action,
                                            game_dirs[role], client_logs[role],
                                            args.client_mem)
                time.sleep(15)

            deadline = time.time() + args.timeout
            ready = False
            while time.time() < deadline:
                texts = {role: read_text(path) for role, path in client_logs.items()}
                if all(f"P231_READY role={role}" in texts[role] for role in texts):
                    ready = True
                    break
                if any(p.poll() is not None for p in procs.values()):
                    break
                time.sleep(2)
            print("all four ready:", ready)

            if ready:
                time.sleep(3)
                fires = int(time.time() * 1000) + 3000
                FIRE_FILE.write_text(str(fires) + "\n", encoding="utf-8")
                print("armed:", fires)
                deadline = time.time() + 120
                while time.time() < deadline:
                    texts = [read_text(path) for path in client_logs.values()]
                    if all("P231_FIRE" in text for text in texts):
                        break
                    if any(p.poll() is not None for p in procs.values()):
                        break
                    time.sleep(1)
                time.sleep(6)
                try:
                    from test_launcher_e2e import _grab_window
                    _grab_window(str(RUN / "after-quad.png"), procs[PLAYERS[0][0]].pid)
                except Exception as exc:
                    print("screenshot skipped:", exc)
                # Stop the clients BEFORE the analysis: the proxy writes its close lines when the
                # connections drop, and the verdict reads those lines. An abrupt proxy kill (the
                # first attempt) leaves the log with opens but no closes.
                for proc in procs.values():
                    if proc.poll() is None:
                        proc.terminate()
                time.sleep(10)

            ser = read_text(server_log)
            client_texts = {role: read_text(path) for role, path in client_logs.items()}
            mutations_all = parse_mutations(ser)
            serverbound_all = parse_serverbound(ser)
            fire_instant = (int(read_text(FIRE_FILE).strip())
                            if read_text(FIRE_FILE).strip() else 0)
            window = (fire_instant - 500, fire_instant + 5000)
            mutations = [m for m in mutations_all if window[0] <= m["wall"] <= window[1]]
            serverbound = [m for m in serverbound_all if window[0] <= m["wall"] <= window[1]]
            pre_fire = [m for m in mutations_all if m["wall"] < window[0]]

            per_user = {}
            for user, role, seed, action, expected in PLAYERS:
                mut = next((m for m in mutations if m["user"] == user), None)
                fire_lines = [line for line in client_texts[role].splitlines()
                              if "P231_FIRE" in line]
                epoch = None
                if fire_lines:
                    m = re.search(r"epochMs=(\d+)", fire_lines[-1])
                    if m:
                        epoch = int(m.group(1))
                delta = (mut["wall"] - epoch) if (mut and epoch is not None) else None
                trash_lines = [line for line in client_texts[role].splitlines()
                               if "P231_TRASH role=" in line]
                final_trash = trash_lines[-1] if trash_lines else ""
                per_user[role] = {
                    "user": user, "seed": seed, "action": action,
                    "expected_stack": expected,
                    "fire_lines": fire_lines[:2],
                    "fire_epoch_ms": epoch,
                    "mutation": mut,
                    "one_way_ms": delta,
                    "client_final_line": final_trash,
                }

            ticks_seen = sorted({p["mutation"]["tick"] for p in per_user.values()
                                 if p["mutation"]})
            walls_seen = [p["mutation"]["wall"] for p in per_user.values() if p["mutation"]]
            wall_spread = (max(walls_seen) - min(walls_seen)) if len(walls_seen) == 4 else None
            deltas = [p["one_way_ms"] for p in per_user.values() if p["one_way_ms"] is not None]
            proxy_text = read_text(proxy_log)
            conns = [(int(m.group(1)), int(m.group(2)), int(m.group(3)))
                     for m in PROXY_CONN.finditer(proxy_text)]
            # Byte evidence prefers traffic lines (written while alive); close lines back it up
            # when the client shut down gracefully.
            traffic_down = {}
            for m in PROXY_TRAFFIC.finditer(proxy_text):
                if m.group(2) == "down":
                    traffic_down[int(m.group(1))] = max(traffic_down.get(int(m.group(1)), 0),
                                                        int(m.group(3)))
            for conn_id, _, down in conns:
                traffic_down[conn_id] = max(traffic_down.get(conn_id, 0), down)
            heavy = [c for c, b in traffic_down.items() if b > 50000]

            seeded_states = {}
            finals = {}
            for user, role, seed, action, expected in PLAYERS:
                st = states(ser, user)
                seeded_states[role] = any(f"trash=minecraft:diamondx{seed}" in s for s in st)
                finals[role] = st[-1] if st else ""

            all_checks = {
                "four_ready": ready,
                "four_fired": all(p["fire_lines"] for p in per_user.values()),
                "server_saw_four_writes": all(p["mutation"] for p in per_user.values()),
                "writes_match_expectations": all(
                    p["mutation"] and p["mutation"]["stack"] == p["expected_stack"]
                    for p in per_user.values()),
                "writes_on_server_thread": all(
                    p["mutation"] and p["mutation"]["thread"].startswith("Server thread")
                    for p in per_user.values()),
                "writes_clustered_in_time": (wall_spread is not None and wall_spread <= 250),
                "four_distinct_game_dirs": (len({str(g.resolve()) for g in game_dirs.values()})
                                            == 4),
                "client_logs_written_in_game_dirs": all(
                    (game_dirs[role] / "logs" / "latest.log").exists()
                    for role in game_dirs),
                "seeded_states_visible": all(seeded_states.values()),
                "client_finals_match": (
                    "trash=empty" in per_user["A"]["client_final_line"]
                    and "trash=minecraft:diamondx3" in per_user["B"]["client_final_line"]
                    and "carried=minecraft:diamondx1" in per_user["B"]["client_final_line"]
                    and "trash=minecraft:diamondx2" in per_user["C"]["client_final_line"]
                    and "trash=minecraft:diamondx1" in per_user["D"]["client_final_line"]),
                "balm_messages_in_window": len(serverbound) >= 4,
                "proxy_connections_at_least_four": len(traffic_down) >= 4,
                "proxy_carried_game_traffic": len(heavy) >= 4,
                "latency_at_least_injected": bool(deltas)
                                             and min(deltas) >= max(args.delay_ms - 10, 1),
                "latency_bounded": bool(deltas) and max(deltas) <= 400,
            }
            result = {
                "injected_delay_ms_per_direction": args.delay_ms,
                "loopback_baseline_note": "p203 loopback fire->write was 4 ms (runs/p203)",
                "fire_instant_ms": fire_instant or None,
                "window_ms": list(window),
                "game_dirs": {role: str(path) for role, path in game_dirs.items()},
                "junctions": list(SHARED_DIRS),
                "proxy_connections": conns,
                "players": per_user,
                "server_write_ticks": ticks_seen,
                "write_wall_spread_ms": wall_spread,
                "one_way_ms_all": deltas,
                "one_way_ms_min": min(deltas) if deltas else None,
                "one_way_ms_median": sorted(deltas)[len(deltas) // 2] if deltas else None,
                "seeded_states_visible": seeded_states,
                "server_final_states": finals,
                "mutations_before_fire": pre_fire,
                "serverbound_stamps": serverbound,
                "checks": all_checks,
                "server_tail": ser.splitlines()[-16:],
            }
            (RUN / "result.json").write_text(
                json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(json.dumps({"ticks": ticks_seen, "one_way_ms": deltas,
                              "proxy_conns_with_traffic": len(traffic_down)},
                             ensure_ascii=False))
            print(json.dumps(all_checks, ensure_ascii=False, indent=2))
            return 0 if all(all_checks.values()) else 1
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
        if proxy and proxy.poll() is None:
            proxy.terminate()
        restore_server_mods(backup)
        restore_server_config()


if __name__ == "__main__":
    sys.exit(main())
