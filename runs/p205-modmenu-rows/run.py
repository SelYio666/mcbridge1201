"""Open Mod Menu with a given patched jar, move the real cursor onto the list, scroll twice, shoot.

The point of this harness is not the scroll (p204 already proved that): it is whether the list draws
rows at all. So it takes one screenshot before and one after two real wheel notches - a 36 px shift -
with everything else held constant. The p204 Win32 helpers are reused as-is rather than rewritten, so
this run uses the same raise-window + foreground path that p204 validated.

Usage:
  python runs/p205-modmenu-rows/run.py --modmenu work/client/modmenu-patched.jar --out runs/p205-modmenu-rows/before
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
RUN = Path(__file__).resolve().parent
CLIENT = ROOT / "work" / "launcher-e2e"
CLIENT_MODS = CLIENT / "mods"
FABRIC_API = ROOT / "work" / "instances" / "fabric-1.21.1-server" / "mods" / "fabric-api.jar"
PROBE = ROOT / "work" / "tmp" / "p204probe.jar"

# Same combined set p204 ran; only the Mod Menu jar is a parameter this time.
OTHER_MODS = [
    (ROOT / "work" / "corpus" / "deps" / "balm-fabric-1.21.1-21.0.66.jar", "balm.jar"),
    (ROOT / "work" / "client" / "shulker-patched2.jar", "shulker-patched2.jar"),
    (ROOT / "work" / "client" / "sbtpreview.jar", "sbtpreview.jar"),
    (ROOT / "work" / "client" / "appleskin-patched.jar", "appleskin-patched.jar"),
    (ROOT / "work" / "client" / "ironchests-final.jar", "ironchests-final.jar"),
    (ROOT / "work" / "client" / "lithium-final.jar", "lithium-final.jar"),
    (ROOT / "work" / "client" / "trashslot-client-final.jar", "trashslot-client-final.jar"),
    (ROOT / "work" / "client" / "fallingtree-patched.jar", "fallingtree-patched.jar"),
]
USER = "RowUser"


def load_p204():
    """Import p204's harness for the Win32 helpers (window raise, foreground, SendInput)."""
    path = ROOT / "runs" / "p204-wheel-input" / "run.py"
    spec = importlib.util.spec_from_file_location("p204harness", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


p204 = load_p204()
sys.path.insert(0, str(ROOT / "tools"))


def setup_mods(modmenu: Path) -> list[str]:
    CLIENT_MODS.mkdir(parents=True, exist_ok=True)
    for path in CLIENT_MODS.glob("*.jar"):
        path.unlink()
    shutil.copy2(FABRIC_API, CLIENT_MODS / "fabric-api.jar")
    installed = ["fabric-api.jar"]
    shutil.copy2(modmenu, CLIENT_MODS / "modmenu.jar")
    installed.append("modmenu.jar")
    for src, name in OTHER_MODS:
        if not src.exists():
            raise SystemExit(f"missing mod jar: {src}")
        shutil.copy2(src, CLIENT_MODS / name)
        installed.append(name)
    if not PROBE.exists():
        raise SystemExit(f"missing probe jar: {PROBE}; run runs/p204-wheel-input/build.py first")
    shutil.copy2(PROBE, CLIENT_MODS / "p204probe.jar")
    installed.append("p204probe.jar")
    return installed


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--modmenu", required=True, help="patched Mod Menu jar to install")
    ap.add_argument("--out", required=True)
    ap.add_argument("--timeout", type=int, default=300)
    ap.add_argument("--notches", type=int, default=2)
    args = ap.parse_args()

    out = Path(args.out)
    if not out.is_absolute():
        out = ROOT / out
    out.mkdir(parents=True, exist_ok=True)
    jar = Path(args.modmenu)
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
        extra_jvm=["-Dmcbridge.listrender.debug=true"],
        extra_game=["--width", "1280", "--height", "720"])
    say("JVMFLAG -Dmcbridge.listrender.debug=true (the bridge only prints P205_LIST with it set)")
    say("MODMENU " + str(jar) + " sha256=" + hashlib.sha256(jar.read_bytes()).hexdigest())
    say("mods: " + ", ".join(installed))

    result: dict = {"modmenu_jar": str(jar),
                    "modmenu_sha256": hashlib.sha256(jar.read_bytes()).hexdigest(),
                    "jvm_flags": ["-Dmcbridge.listrender.debug=true"],
                    "mods": installed}

    with client_log.open("w", encoding="utf-8", errors="replace") as cout:
        cout.write(" ".join(cmd) + "\n")
        cout.flush()
        client = subprocess.Popen(cmd, cwd=str(CLIENT), stdout=cout, stderr=subprocess.STDOUT)
        try:
            deadline = time.time() + args.timeout
            ready = False
            while time.time() < deadline:
                if "P204_READY" in p204.read_text(client_log):
                    ready = True
                    break
                if client.poll() is not None:
                    break
                time.sleep(0.5)
            if not ready:
                say("probe never became ready; client tail:")
                say("\n".join(p204.read_text(client_log).splitlines()[-16:]))
                return 1
            time.sleep(1.0)
            log = p204.read_text(client_log)
            list_rect = p204.parse_rect(log, "list")
            list_center = p204.parse_point(log, "listCenter")
            window = re.search(r"P204_WINDOW handle=(\d+) m4480=(\d+) m4486=(\d+) "
                               r"m4502=(\d+) m4507=(\d+) scale=([\d.]+)", log)
            if list_rect is None or list_center is None:
                say("probe did not announce the list geometry")
                return 1
            result["list"] = list_rect
            result["list_center"] = list(list_center)
            if window:
                result["window"] = {"client_w": int(window.group(2)),
                                    "client_h": int(window.group(5)),
                                    "scale": float(window.group(6))}
            state = re.findall(r"P204_SCROLL_STATE tick=\d+ scroll=([\d.]+) max=(-?\d+) "
                               r"entries=(\d+)", log)
            if state:
                result["scroll_before"], result["max_scroll"], result["entries"] = (
                    float(state[-1][0]), int(state[-1][1]), int(state[-1][2]))

            pid = client.pid
            hwnd = p204._window_handle(pid)
            if not hwnd:
                say("no window handle for the client pid")
                return 1
            p204._focus(hwnd)
            time.sleep(0.4)
            ox, oy, cw, ch = p204._client_origin(hwnd)
            say(f"CLIENTAREA origin=({ox},{oy}) size={cw}x{ch} hwnd={hwnd}")
            x, y = ox + list_center[0], oy + list_center[1]
            p204._move(x, y)
            time.sleep(0.5)
            cx, cy = p204._cursor_pos()
            under = p204._window_at(cx, cy)
            on_game = p204._root_window(under) == p204._root_window(hwnd)
            say(f"MOVE listCenter requested=({x},{y}) cursorNow=({cx},{cy}) underIsGame={on_game}")
            result["cursor"] = [cx, cy]
            result["cursor_on_game"] = on_game

            p204._grab_window(str(out / "rows-before.png"), pid)
            time.sleep(0.6)
            accepted = p204._wheel(-args.notches)
            time.sleep(1.4)
            p204._grab_window(str(out / "rows-scrolled.png"), pid)
            say(f"WHEEL notches={args.notches} accepted={accepted}")
            result["wheel"] = {"notches": args.notches, "accepted": accepted}

            text = p204.read_text(client_log)
            state_after = re.findall(r"P204_SCROLL_STATE tick=\d+ scroll=([\d.]+)", text)
            result["scroll_after"] = float(state_after[-1]) if state_after else -1.0
            result["scroll_events"] = len(re.findall(r"P204_SCROLL n=", text))
            listing = [ln.split("STDOUT]: ", 1)[-1].strip() for ln in text.splitlines()
                       if "P205_LIST" in ln]
            result["p205_list_lines"] = listing
            result["p205_list_line"] = listing[0] if listing else ""
            say("SCROLL " + f"{result.get('scroll_before')} -> {result['scroll_after']} "
                f"events={result['scroll_events']}")
            for line in listing:
                say("P205 " + line)
            if not listing:
                say("P205 missing")
            (out / "result.json").write_text(
                json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
                newline="\n")
            return 0
        finally:
            if client.poll() is None:
                client.terminate()
                try:
                    client.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    client.kill()


if __name__ == "__main__":
    sys.exit(main())
