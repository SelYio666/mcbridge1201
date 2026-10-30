"""Ask Mod Menu for AppleSkin's Cloth Config screen on 1.21.1 and record what happens (p210).

The control and the fix differ in exactly one file: `appleskin-patched.jar` (its nested Cloth
Config 11.1.136 still reads the 1.21.1-removed `Screen.field_44669`) versus
`appleskin-cloth.jar` (same outer jar, one `getstatic` in the nested `ConfigBuilderImpl.<init>`
turned into a call to `ClothConfigBridge.defaultBackground`).

The probe does what `ModsScreen` does while initialising - `ModMenu.getConfigScreen("appleskin",
parent)` - so a green run means the path that used to throw is now walkable, not that a screen class
can be constructed by hand. Whatever the call throws is printed with its stack (`P210_CONFIG` /
`P210_STACK`), and the client log is kept so a swallowed error cannot pass as a pass.

Usage:
  python runs/p210-cloth-config/run.py --appleskin work/client/appleskin-cloth.jar \
      --out runs/p210-cloth-config/after
  python runs/p210-cloth-config/run.py --appleskin work/client/appleskin-patched.jar \
      --out runs/p210-cloth-config/before
"""
import argparse
import hashlib
import importlib.util
import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CLIENT = ROOT / "work" / "launcher-e2e"
CLIENT_MODS = CLIENT / "mods"
USER = "ClothUser"
FABRIC_API = ROOT / "work" / "instances" / "fabric-1.21.1-server" / "mods" / "fabric-api.jar"
PROBE = ROOT / "work" / "tmp" / "p210probe.jar"
MODMENU = ROOT / "work" / "client" / "modmenu-description.jar"

OTHER_MODS = [
    (ROOT / "work" / "corpus" / "deps" / "balm-fabric-1.21.1-21.0.66.jar", "balm.jar"),
    (ROOT / "work" / "client" / "shulker-patched2.jar", "shulker-patched2.jar"),
    (ROOT / "work" / "client" / "sbtpreview.jar", "sbtpreview.jar"),
    (ROOT / "work" / "client" / "ironchests-final.jar", "ironchests-final.jar"),
    (ROOT / "work" / "client" / "lithium-final.jar", "lithium-final.jar"),
    (ROOT / "work" / "client" / "trashslot-client-final.jar", "trashslot-client-final.jar"),
    (ROOT / "work" / "client" / "fallingtree-patched.jar", "fallingtree-patched.jar"),
]

CONFIG_LINE = re.compile(
    r"P210_CONFIG ok=(true|false) (?:screen=(\S+) micros=(\d+) title=\"(.*)\" widgets=(\S+)"
    r"|error=(.*))")
SCREEN_LINE = re.compile(r"P210_SCREEN switched=true screen=(\S+) title=\"(.*)\" widgets=(\S+)")
CONST_LINE = re.compile(r"P210_SCREEN_CONST field=(\S+) value=(\S+)")
DONE_LINE = re.compile(r"P210_DONE tick=(\d+) screen=(\S+) widgets=(\S+)")
TOGGLE_ROW_LINE = re.compile(r"P210_TOGGLE_ROW class=(\S+) before=(\S+) button=(\S+) box=\(([^)]*)\)")
CLICK_LINE = re.compile(r"P210_CLICK (handled=\S+ .*|error=.*)")
TOGGLE_LINE = re.compile(r"P210_TOGGLE row=(\S+) before=(\S+) after=(\S+) flipped=(true|false)"
                         r" direct_press=(true|false)")


def load_p204():
    path = ROOT / "runs" / "p204-wheel-input" / "run.py"
    spec = importlib.util.spec_from_file_location("p204harness", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


p204 = load_p204()
sys.path.insert(0, str(ROOT / "tools"))


def setup_mods(appleskin: Path) -> list[str]:
    CLIENT_MODS.mkdir(parents=True, exist_ok=True)
    for path in CLIENT_MODS.glob("*.jar"):
        path.unlink()
    shutil.copy2(FABRIC_API, CLIENT_MODS / "fabric-api.jar")
    installed = ["fabric-api.jar"]
    shutil.copy2(MODMENU, CLIENT_MODS / "modmenu.jar")
    installed.append("modmenu.jar")
    for src, name in OTHER_MODS:
        if not src.exists():
            raise SystemExit(f"missing mod jar: {src}")
        shutil.copy2(src, CLIENT_MODS / name)
        installed.append(name)
    if not appleskin.is_file():
        raise SystemExit(f"missing AppleSkin jar: {appleskin}")
    shutil.copy2(appleskin, CLIENT_MODS / "appleskin.jar")
    installed.append("appleskin.jar")
    if not PROBE.is_file():
        raise SystemExit(f"missing probe jar: {PROBE}; run build_probe.py first")
    shutil.copy2(PROBE, CLIENT_MODS / "p210probe.jar")
    installed.append("p210probe.jar")
    return installed


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--appleskin", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--timeout", type=int, default=300)
    ap.add_argument("--width", type=int, default=1280)
    ap.add_argument("--height", type=int, default=720)
    args = ap.parse_args()

    out = Path(args.out)
    if not out.is_absolute():
        out = ROOT / out
    out.mkdir(parents=True, exist_ok=True)
    jar = Path(args.appleskin)
    if not jar.is_absolute():
        jar = ROOT / jar

    installed = setup_mods(jar)
    log_lines: list[str] = []

    def say(line: str) -> None:
        print(line)
        log_lines.append(line)
        (out / "harness.log").write_text("\n".join(log_lines) + "\n", encoding="utf-8",
                                         newline="\n")

    client_log = out / "client.log"
    client_log.write_text("", encoding="utf-8")
    cmd, _, _ = p204.mclaunch.build_command(
        "fabric-loader-0.19.5-1.21.1", CLIENT, USER, "2G",
        extra_game=["--width", str(args.width), "--height", str(args.height)])
    say(f"WINDOW requested={args.width}x{args.height}")
    say("APPLESKIN " + str(jar) + " sha256=" + hashlib.sha256(jar.read_bytes()).hexdigest()
        + " size=" + str(jar.stat().st_size))
    say("MODMENU " + str(MODMENU) + " sha256="
        + hashlib.sha256(MODMENU.read_bytes()).hexdigest())
    say("mods: " + ", ".join(installed))

    result: dict = {
        "appleskin_jar": str(jar),
        "appleskin_sha256": hashlib.sha256(jar.read_bytes()).hexdigest(),
        "appleskin_size": jar.stat().st_size,
        "modmenu_jar": str(MODMENU),
        "modmenu_sha256": hashlib.sha256(MODMENU.read_bytes()).hexdigest(),
        "requested_window": [args.width, args.height],
        "mods": installed,
    }

    with client_log.open("w", encoding="utf-8", errors="replace") as cout:
        cout.write(" ".join(cmd) + "\n")
        cout.flush()
        client = subprocess.Popen(cmd, cwd=str(CLIENT), stdout=cout, stderr=subprocess.STDOUT)
        pid = client.pid
        shot_done = False
        toggle_shot_done = False
        try:
            deadline = time.time() + args.timeout
            while time.time() < deadline:
                text = p204.read_text(client_log)
                if not shot_done and "P210_SCREEN switched=true" in text:
                    time.sleep(1.5)
                    p204._grab_window(str(out / "config.png"), pid)
                    shot_done = True
                    say("SHOT config.png")
                if not toggle_shot_done and "P210_TOGGLE_SHOT" in text:
                    # The state after the click, so "the value flipped" can also be seen: the first
                    # toggle's button has to read OFF in this frame and ON in config.png.
                    time.sleep(1.5)
                    p204._grab_window(str(out / "toggle.png"), pid)
                    toggle_shot_done = True
                    say("SHOT toggle.png")
                if "P210_DONE" in text:
                    break
                if "P210_CONFIG ok=false" in text and not shot_done:
                    # Keep a picture of the failure too: an empty Mod Menu with the error in the
                    # log is the state p204 described, and it is the control run's evidence.
                    time.sleep(1.5)
                    p204._grab_window(str(out / "config.png"), pid)
                    shot_done = True
                    say("SHOT config.png (failure state)")
                if client.poll() is not None:
                    say("client exited early")
                    break
                time.sleep(0.5)
            else:
                say("timeout waiting for P210_DONE")
        finally:
            try:
                client.terminate()
                client.wait(timeout=20)
            except Exception:
                client.kill()

    text = p204.read_text(client_log)
    (out / "harness.log").write_text("\n".join(log_lines) + "\n", encoding="utf-8", newline="\n")

    m = CONFIG_LINE.search(text)
    if m:
        if m.group(1) == "true":
            result["config"] = {"ok": True, "screen": m.group(2),
                                "micros": int(m.group(3)),
                                "title": m.group(4), "widgets": m.group(5)}
        else:
            result["config"] = {"ok": False, "error": m.group(6)}
    s = SCREEN_LINE.search(text)
    if s:
        result["switched"] = {"screen": s.group(1), "title": s.group(2), "widgets": s.group(3)}
    result["screen_constants"] = [{"field": a, "value": b} for a, b in CONST_LINE.findall(text)]
    d = DONE_LINE.search(text)
    if d:
        result["done"] = {"tick": int(d.group(1)), "screen": d.group(2), "widgets": d.group(3)}
    result["stack"] = [line.strip() for line in text.splitlines() if "P210_STACK" in line]
    row_match = TOGGLE_ROW_LINE.search(text)
    if row_match:
        result["toggle_row"] = {"class": row_match.group(1), "before": row_match.group(2),
                                "button": row_match.group(3), "box": row_match.group(4)}
    click_match = CLICK_LINE.search(text)
    if click_match:
        result["toggle_click"] = click_match.group(1).strip()
    toggle = TOGGLE_LINE.search(text)
    if toggle:
        result["toggle"] = {"row": toggle.group(1), "before": toggle.group(2),
                            "after": toggle.group(3), "flipped": toggle.group(4) == "true",
                            "direct_press": toggle.group(5) == "true"}
    toggle_shot = out / "toggle.png"
    result["toggle_screenshot"] = str(toggle_shot) if toggle_shot.is_file() else None
    result["no_such_field"] = text.count("NoSuchFieldError")
    result["no_such_method"] = text.count("NoSuchMethodError")
    result["client_errors"] = sorted({line.strip() for line in text.splitlines()
                                      if "[Render thread/ERROR]" in line
                                      or "[main/ERROR]" in line})[:12]
    shot = out / "config.png"
    result["screenshot"] = str(shot) if shot.is_file() else None
    (out / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                                     encoding="utf-8", newline="\n")
    say("RESULT " + json.dumps({k: result.get(k) for k in
                                ("config", "switched", "done", "no_such_field",
                                 "no_such_method")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
