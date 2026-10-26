#!/usr/bin/env python3
"""p197: Shulker preview-key rebinding - rebind preview/full-preview keys in the mod config.

p196 wrote its key under configuration.preview (a category with no such field) and concluded
"the mod ignores the config". The mod's bytecode polls
InputConstants.isKeyDown(window, config.controls.<key>.get().getCode()); the defaults are
previewKey=340 (LEFT_ALT), fullPreviewKey=342 (RIGHT_SHIFT). This harness writes the correct
schema and drives only the rebound codes:

    preview.enable = true, preview.alwaysOn = false
    controls.previewKey     = key.keyboard.j  (74)
    controls.fullPreviewKey = key.keyboard.k  (75)

J/K have no vanilla binding, so the synthetic presses cannot also swap the offhand (F did that in
this run's first attempt and silently removed the hover). The flow runs in ONE survival inventory
with a real server-provided 27-item shulker box in slot 10:

    J only        -> COMPACT   (screenshot)
    J + K         -> FULL      (screenshot, 27-item grid)
    release K     -> COMPACT   (screenshot)
    release J     -> NO_PREVIEW

The probe's poll mixin only reports 74/75 as held (never 340/342), so any COMPACT/FULL render
proves the mod polled the rebound codes; P197_CONFIG logs the decoded config and P197_KEYS /
P197_TYPE log the mod's own state machine.
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
CLIENT_MODS = CLIENT / "mods"
FABRIC_API = ROOT / "work" / "instances" / "fabric-1.21.1-server" / "mods" / "fabric-api.jar"
BALM = ROOT / "work" / "corpus" / "deps" / "balm-fabric-1.21.1-21.0.66.jar"
SHULKER = ROOT / "work" / "client" / "shulker-patched2.jar"
SBT = ROOT / "work" / "client" / "sbtpreview.jar"
PROBE = ROOT / "work" / "tmp" / "p197probe.jar"
PORT = "25566"
USER = "GridUser"

ITEM_IDS = ["diamond", "emerald", "iron_ingot", "gold_ingot", "coal", "redstone",
            "lapis_lazuli", "quartz", "copper_ingot", "amethyst_shard", "stick", "string",
            "feather", "flint", "gunpowder", "wheat", "apple", "bread", "carrot", "potato",
            "beetroot", "sugar", "paper", "book", "arrow", "bone", "slime_ball"]

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
    for path in CLIENT_MODS.glob("*.jar"):
        path.unlink()
    shutil.copy2(FABRIC_API, CLIENT_MODS / FABRIC_API.name)
    shutil.copy2(BALM, CLIENT_MODS / BALM.name)
    shutil.copy2(SHULKER, CLIENT_MODS / "shulker-patched2.jar")
    shutil.copy2(SBT, CLIENT_MODS / "sbtpreview.jar")
    shutil.copy2(PROBE, CLIENT_MODS / "p197probe.jar")


def write_config() -> None:
    config_dir = CLIENT / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "shulkerboxtooltip.json5").write_text(
        "{\n"
        "  \"preview\": {\n"
        "    \"enable\": true,\n"
        "    \"alwaysOn\": false\n"
        "  },\n"
        "  \"controls\": {\n"
        "    \"previewKey\": \"key.keyboard.j\",\n"
        "    \"fullPreviewKey\": \"key.keyboard.k\"\n"
        "  }\n"
        "}\n",
        encoding="utf-8")


def box_command() -> str:
    entries = ",".join(f'{{slot:{i},item:{{id:"minecraft:{item}",count:{(i % 3) + 1}}}}}'
                       for i, item in enumerate(ITEM_IDS))
    return (f"item replace entity {USER} container.10 with "
            f"minecraft:shulker_box[minecraft:container=[{entries}]]")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--timeout", type=int, default=300)
    args = ap.parse_args()
    RUN.mkdir(parents=True, exist_ok=True)
    if not PROBE.exists():
        print(f"missing probe jar: {PROBE}; run build.py first", file=sys.stderr)
        return 2
    setup_mods()
    write_config()

    props = SERVER / "server.properties"
    backup = RUN / "server.properties.before"
    if props.exists():
        shutil.copy2(props, backup)
    settings = {"server-port": PORT, "difficulty": "peaceful", "gamemode": "survival",
                "force-gamemode": "true", "spawn-monsters": "false"}
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

    try:
        users = json.loads(read_text(SERVER / "usercache.json") or "[]")
    except ValueError:
        users = []
    for entry in users:
        if entry.get("name") != USER:
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
    with server_log.open("w", encoding="utf-8", errors="replace") as out:
        server = subprocess.Popen([str(java), "-Xmx2G", "-jar", "fabric-server-launch.jar", "nogui"],
                                  cwd=str(SERVER), stdout=out, stderr=subprocess.STDOUT,
                                  stdin=subprocess.PIPE)
        try:
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

            client_log = RUN / "client.log"
            client_log.write_text("", encoding="utf-8")
            cmd, _, _ = mclaunch.build_command(
                "fabric-loader-0.19.5-1.21.1", CLIENT, USER, "2G",
                extra_game=["--quickPlayMultiplayer", f"127.0.0.1:{PORT}",
                            "--width", "1280", "--height", "720"])
            with client_log.open("w", encoding="utf-8", errors="replace") as cout:
                cout.write(" ".join(cmd) + "\n")
                cout.flush()
                client = subprocess.Popen(cmd, cwd=str(CLIENT), stdout=cout,
                                          stderr=subprocess.STDOUT)
                try:
                    deadline = time.time() + args.timeout
                    joined = False
                    full_seen = False
                    release_seen = False
                    polls_seen = False
                    while time.time() < deadline:
                        if not joined and "joined the game" in read_text(server_log):
                            joined = True
                            server.stdin.write((box_command() + "\n").encode("utf-8"))
                            server.stdin.write(
                                (f"data get entity {USER} Inventory[{{Slot:10b}}]\n").encode())
                            server.stdin.flush()
                            print("server placed the 27-item box in slot 10")
                        text = read_text(client_log)
                        if not full_seen and "P197_FULL_REQUEST" in text:
                            full_seen = True
                            time.sleep(3)
                            _grab_window(str(RUN / "after-full.png"), client.pid)
                            print("FULL screenshot taken")
                        if not release_seen and "P197_FULL_RELEASE" in text:
                            release_seen = True
                            time.sleep(2)
                            _grab_window(str(RUN / "after-compact.png"), client.pid)
                            print("post-release COMPACT screenshot taken")
                        if "P197_POLLS " in text:
                            polls_seen = True
                            break
                        if client.poll() is not None:
                            break
                        time.sleep(1)
                    if not full_seen or not release_seen or not polls_seen:
                        print(f"incomplete phases: full={full_seen} release={release_seen} "
                              f"polls={polls_seen}; client tail:")
                        print("\n".join(read_text(client_log).splitlines()[-12:]))
                        return 1
                    time.sleep(1)

                    text = read_text(client_log)
                    ser = read_text(server_log)

                    def between(start_marker: str, end_marker: str | None) -> str:
                        start = text.find(start_marker)
                        if start < 0:
                            return ""
                        if end_marker is None:
                            return text[start:]
                        end = text.find(end_marker, start + len(start_marker))
                        return text[start:] if end < 0 else text[start:end]

                    drawitems = [line.split("GRID_DRAWITEMS ", 1)[1].strip()
                                 for line in text.splitlines() if "GRID_DRAWITEMS " in line]
                    poll_codes = sorted({int(line.split("P197_POLL code=", 1)[1].split()[0])
                                         for line in text.splitlines() if "P197_POLL code=" in line})
                    polls_line = next((line for line in reversed(text.splitlines())
                                       if "P197_POLLS " in line), "")
                    config_line = next((line for line in text.splitlines()
                                        if "P197_CONFIG " in line), "")
                    keys_logs = [line.split("P197_KEYS ", 1)[1].strip()
                                 for line in text.splitlines() if "P197_KEYS " in line]
                    type_logs = [line.split("P197_TYPE ", 1)[1].strip()
                                 for line in text.splitlines() if "P197_TYPE " in line]
                    compact_phase = between("P197_COMPACT_REQUEST", "P197_FULL_REQUEST")
                    full_phase = between("P197_FULL_REQUEST", "P197_FULL_RELEASE")
                    restored_phase = between("P197_FULL_RELEASE", "P197_RELEASE_ALL")
                    released_phase = between("P197_RELEASE_ALL", None)

                    def has(phase: str, preview_type: str, items: str | None = None) -> bool:
                        for line in phase.splitlines():
                            if "GRID_DRAWITEMS " not in line:
                                continue
                            if f"type={preview_type}" not in line:
                                continue
                            if items is not None and items not in line:
                                continue
                            return True
                        return False

                    keys_text = " | ".join(keys_logs)
                    config_ok = ("previewCode=74" in config_line and "fullCode=75" in config_line
                                 and "alwaysOn=false" in config_line)
                    keys_ok = ("preview=true full=false" in keys_text
                               and "preview=true full=true" in keys_text
                               and "preview=false full=false" in keys_text)
                    compact_on_j = has(compact_phase, "COMPACT", "items=27")
                    full_on_jk = has(full_phase, "FULL", "items=27")
                    compact_after_k = has(restored_phase, "COMPACT", "items=27")
                    no_preview_after_release = (not has(released_phase, "COMPACT")
                                                and not has(released_phase, "FULL")
                                                and any("NO_PREVIEW" in t for t in type_logs))
                    real_hover = any("DRAWTOOLTIP" in line and "data=com.misterpemodder" in line
                                     for line in text.splitlines())
                    result = {
                        "config_line": config_line,
                        "poll_codes": poll_codes,
                        "polls_line": polls_line,
                        "keys_logs": keys_logs[:16],
                        "type_logs": type_logs[:16],
                        "config_rebound": config_ok,
                        "keys_transitions": keys_ok,
                        "compact_on_j": compact_on_j,
                        "full_on_jk": full_on_jk,
                        "compact_after_k": compact_after_k,
                        "no_preview_after_release": no_preview_after_release,
                        "real_hover_path": real_hover,
                        "drawitems_sample": drawitems[:12],
                        "client_tail": text.splitlines()[-16:],
                        "server_tail": ser.splitlines()[-8:],
                    }
                    (RUN / "result.json").write_text(
                        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                    keys = ("config_rebound", "keys_transitions", "compact_on_j", "full_on_jk",
                            "compact_after_k", "no_preview_after_release", "real_hover_path")
                    print(json.dumps({k: result[k] for k in keys}, ensure_ascii=False))
                    return 0 if all(result[k] for k in keys) else 1
                finally:
                    if client.poll() is None:
                        client.terminate()
                        try:
                            client.wait(timeout=10)
                        except subprocess.TimeoutExpired:
                            client.kill()
        finally:
            if server.poll() is None:
                server.terminate()
                try:
                    server.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    server.kill()
            if backup.exists():
                shutil.copy2(backup, props)


if __name__ == "__main__":
    sys.exit(main())
