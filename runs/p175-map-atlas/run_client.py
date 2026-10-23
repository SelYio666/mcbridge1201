#!/usr/bin/env python3
"""Launch the Fabric 1.21.1 client in a map test world and capture evidence.

The runner waits for the integrated server join and the port's map-atlas markers, then grabs the
game window. It writes ``client.log``, ``latest.log``, ``result.json`` and ``world.png`` to
``--run-dir`` (default: this directory). ``--require-map`` makes it wait until that map id has a
``map-atlas bind map=map/<id>`` marker; repeat it to require several maps.

A non-zero exit means a required marker did not appear or the client crashed.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUN = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "launcher"))
sys.path.insert(0, str(ROOT / "tools"))
import mclaunch  # noqa: E402
from test_launcher_e2e import _grab_window  # noqa: E402

VERSION = "fabric-loader-0.19.5-1.21.1"
INSTANCE = ROOT / "work" / "launcher-e2e"
USERNAME = "IFMapUser"
WORLD = "ColdWorldMap"

BAD_MARKERS = [
    "ClassCastException",
    "InvalidInjectionException",
    "Mixin apply for mod immediatelyfast failed",
    "Mixin transformation of net.minecraft.class_330 failed",
    "java.lang.NoClassDefFoundError",
    "java.lang.NoSuchMethodError",
    "Game crashed",
    "Uncaught exception in thread",
    "Unreported exception thrown!",
    "Image is not allocated",
]


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except FileNotFoundError:
        return ""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--timeout", type=int, default=240)
    ap.add_argument("--settle", type=int, default=8, help="seconds to wait after the map marker")
    ap.add_argument("--username", default=USERNAME)
    ap.add_argument("--world", default=WORLD)
    ap.add_argument("--run-dir", default=str(RUN), help="directory for logs/result/screenshot")
    ap.add_argument("--require-map", action="append", type=int, default=[],
                    help="wait for map-atlas bind markers of this map id (repeatable)")
    ap.add_argument("--join-only", action="store_true",
                    help="capture after join + settle without requiring map-atlas markers")
    ap.add_argument("--require-log", action="append", default=[],
                    help="wait for this log substring before the screenshot (repeatable)")
    ap.add_argument("--exit-log", default="",
                    help="after the screenshot, wait for this log substring (normal world exit)")
    ap.add_argument("--keep", action="store_true")
    args = ap.parse_args()

    out_dir = Path(args.run_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    required = sorted(set(args.require_map))
    log = out_dir / "client.log"
    log.write_text("", encoding="utf-8")
    cmd, _, _ = mclaunch.build_command(
        VERSION, INSTANCE, args.username, "2G",
        extra_game=["--quickPlaySingleplayer", args.world, "--width", "1280", "--height", "720"])
    with log.open("w", encoding="utf-8", errors="replace") as out:
        out.write(" ".join(cmd) + "\n")
        out.flush()
        proc = subprocess.Popen(cmd, cwd=str(INSTANCE), stdout=out, stderr=subprocess.STDOUT)

    joined = False
    map_marker = False
    atlases: list[str] = []
    errors: list[str] = []
    deadline = time.time() + args.timeout
    started = time.time()
    shot_done = False
    required_ok = not required
    logs_ok = not args.require_log
    exit_seen = False
    state_shots: list[str] = []
    try:
        while time.time() < deadline:
            text = read_text(log)
            joined = joined or f"{args.username} joined the game" in text
            marker_lines = [line for line in text.splitlines() if "[mcbridge-port] map-atlas" in line]
            if marker_lines:
                map_marker = True
                atlases = marker_lines
            required_ok = all(
                any(f"map-atlas bind map=map/{mid} " in line for line in marker_lines)
                for mid in required) if required else True
            logs_ok = all(marker in text for marker in args.require_log)
            errors = [line for line in text.splitlines()
                      if any(marker in line for marker in BAD_MARKERS)]
            elapsed = int(time.time() - started)
            for at in (30, 60, 120):
                name = f"state-{at}.png"
                if elapsed >= at and name not in state_shots:
                    _grab_window(str(out_dir / name), proc.pid)
                    state_shots.append(name)
            if proc.poll() is not None:
                break
            if joined and (map_marker or args.join_only) and required_ok and logs_ok:
                time.sleep(args.settle)
                shot_done = bool(_grab_window(str(out_dir / "world.png"), proc.pid))
                if args.exit_log:
                    exit_deadline = time.time() + 90
                    while time.time() < exit_deadline:
                        if args.exit_log in read_text(log):
                            exit_seen = True
                            break
                        if proc.poll() is not None:
                            break
                        time.sleep(0.5)
                    time.sleep(2)
                break
            time.sleep(1)
    finally:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=15)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=10)

    time.sleep(1)
    text = read_text(log)
    latest = INSTANCE / "logs" / "latest.log"
    if latest.exists():
        shutil.copy2(latest, out_dir / "latest.log")
    crash = None
    for candidate in sorted((INSTANCE / "crash-reports").glob("crash-*-client.txt"), reverse=True):
        if candidate.stat().st_mtime >= log.stat().st_mtime - 5:
            crash = str(candidate)
            break
    # A Mixin apply error appears only in the rendered stack trace; scan the whole text too.
    crash_lines = [line for line in text.splitlines()
                   if "Mixin apply for mod immediatelyfast failed" in line
                   or "java.lang.ClassCastException" in line
                   or "Image is not allocated" in line
                   or "Unreported exception thrown!" in line]
    ok = bool(joined and (map_marker or args.join_only) and required_ok and logs_ok and shot_done
              and (exit_seen if args.exit_log else True)
              and not crash
              and not errors and not crash_lines)
    result = {
        "joined": joined,
        "join_only": args.join_only,
        "required_logs": args.require_log,
        "logs_ok": logs_ok,
        "exit_log": args.exit_log,
        "exit_seen": exit_seen,
        "map_marker": map_marker,
        "required_maps": required,
        "required_maps_ok": required_ok,
        "map_world_rendered": shot_done,
        "markers": atlases,
        "errors": errors,
        "crash": crash,
        "exit_code": proc.returncode,
        "world": args.world,
        "username": args.username,
        "screenshot": "world.png" if shot_done else None,
        "state_screenshots": state_shots,
    }
    (out_dir / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                                         encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not args.keep and not ok:
        print("FAILED: see client.log / latest.log", file=sys.stderr)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
