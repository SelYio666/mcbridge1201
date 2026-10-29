"""Select a mod row with a real left click, then look at what the two lists drew.

p205 fixed the mod list rows but left two things unproven: the description panel (same bridge, but
it had count=0 because nothing was selected) and the selection highlight (never implemented). This
harness clicks a row by its computed centre - row 3 by default, so the click cannot coincide with
whatever Mod Menu preselects on open - and shoots before/after.

Everything else is p204/p205: same client, same eleven mods, same window and cursor path, same
raise-window + foreground dance. Only the jar differs.

Usage:
  python runs/p206-modmenu-select/run.py --modmenu work/client/modmenu-selected.jar \
      --out runs/p206-modmenu-select/after --row 3
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
USER = "SelUser"


def load_p204():
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


# The p205 jar predates the focused/box fields; the control run has to parse its shorter line, so
# everything after `mouse=` is optional and only the run with the new bridge fills it in.
WIDGET_LINE = re.compile(
    r"P205_LIST class=(\S+) count=(-?\d+) left=(-?\d+) rowWidth=(-?\d+) itemHeight=(-?\d+) "
    r"rows=(-?\d+)\.\.(-?\d+) mouse=(-?\d+),(-?\d+)"
    r"(?: focused=(true|false) box=(-?\d+),(-?\d+),(-?\d+),(-?\d+))?")
SELECT_LINE = re.compile(r"P205_SELECT class=(\S+) selected=(-?\d+) count=(-?\d+) focused=(true|false)")


def widget_lines(text: str) -> list[dict]:
    out = []
    for m in WIDGET_LINE.finditer(text):
        g = m.groups()
        out.append({"class": g[0], "count": int(g[1]), "left": int(g[2]), "rowWidth": int(g[3]),
                    "itemHeight": int(g[4]), "rows": [int(g[5]), int(g[6])],
                    "mouse": [int(g[7]), int(g[8])],
                    "focused": (g[9] == "true") if g[9] else None,
                    "box": [int(g[10]), int(g[11]), int(g[12]), int(g[13])] if g[10] else None})
    return out


def select_lines(text: str) -> list[dict]:
    return [{"class": m.group(1), "selected": int(m.group(2)), "count": int(m.group(3)),
             "focused": m.group(4) == "true"} for m in SELECT_LINE.finditer(text)]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--modmenu", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--timeout", type=int, default=300)
    ap.add_argument("--row", type=int, default=3, help="row index to click (0-based, scroll=0)")
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
    say("JVMFLAG -Dmcbridge.listrender.debug=true")
    say("MODMENU " + str(jar) + " sha256=" + hashlib.sha256(jar.read_bytes()).hexdigest()
        + " size=" + str(jar.stat().st_size))
    say("mods: " + ", ".join(installed))

    result: dict = {"modmenu_jar": str(jar),
                    "modmenu_sha256": hashlib.sha256(jar.read_bytes()).hexdigest(),
                    "modmenu_size": jar.stat().st_size,
                    "jvm_flags": ["-Dmcbridge.listrender.debug=true"],
                    "mods": installed, "click_row": args.row}

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
            # The probe opens the mod screen on its own schedule; wait until the bridge has actually
            # drawn the list once, otherwise "no debug line" would be a timing artefact.
            for _ in range(120):
                if "P205_LIST class=ModListWidget" in p204.read_text(client_log):
                    break
                if client.poll() is not None:
                    break
                time.sleep(0.5)
            else:
                say("ModListWidget never rendered")
                return 1
            text = p204.read_text(client_log)
            window = re.search(r"P204_WINDOW handle=(\d+) m4480=(\d+) m4486=(\d+) "
                               r"m4502=(\d+) m4507=(\d+) scale=([\d.]+)", text)
            if not window:
                say("probe did not announce the window")
                return 1
            scale = float(window.group(6))
            result["window"] = {"client_w": int(window.group(2)), "client_h": int(window.group(5)),
                                "scale": scale}

            widgets = {w["class"]: w for w in widget_lines(text)}
            listw = widgets.get("ModListWidget")
            state = re.findall(r"P204_SCROLL_STATE tick=\d+ scroll=([\d.]+) max=(-?\d+) "
                               r"entries=(\d+)", text)
            if state:
                result["scroll_before"] = float(state[-1][0])
                result["entries"] = int(state[-1][2])
            if listw is None:
                say("no ModListWidget debug line; bridge lines seen: " + str(list(widgets)))
                return 1
            result["mod_list"] = listw

            pid = client.pid
            hwnd = p204._window_handle(pid)
            if not hwnd:
                say("no window handle for the client pid")
                return 1
            p204._focus(hwnd)
            time.sleep(0.4)
            ox, oy, cw, ch = p204._client_origin(hwnd)
            say(f"CLIENTAREA origin=({ox},{oy}) size={cw}x{ch} hwnd={hwnd} scale={scale}")

            list_center = p204.parse_point(p204.read_text(client_log), "listCenter")
            if list_center is None:
                say("probe did not announce listCenter")
                return 1
            # Re-raise on every attempt: the window manager sometimes ignores the first
            # SetWindowPos, and p202 already showed what a "cursor over the terminal" run looks
            # like - it silently turns every synthetic event into a no-op.
            on_game = False
            for attempt in range(1, 4):
                p204._move(ox + list_center[0], oy + list_center[1])
                time.sleep(0.6)
                cx, cy = p204._cursor_pos()
                under = p204._window_at(cx, cy)
                on_game = p204._root_window(under) == p204._root_window(hwnd)
                say(f"MOVE attempt={attempt} listCenter=({ox + list_center[0]},{oy + list_center[1]}) "
                    f"cursorNow=({cx},{cy}) underIsGame={on_game}")
                if on_game:
                    break
                p204._focus(hwnd)
                time.sleep(0.8)
            result["cursor_on_game"] = on_game
            if not on_game:
                say("cursor is not over the game window after 3 raises; a click would go elsewhere")
                return 1

            p204._grab_window(str(out / "sel-before.png"), pid)
            time.sleep(0.4)
            before_lines = select_lines(p204.read_text(client_log))
            result["select_before"] = before_lines[-1] if before_lines else None

            # The click point comes from the probe's widget rectangle, not the bridge's box field,
            # so the control (old jar, no box field) and the fix run click the very same pixel.
            probe_list = p204.parse_rect(p204.read_text(client_log), "list")
            if probe_list is None:
                say("probe did not announce the list rectangle")
                return 1
            result["probe_list"] = probe_list
            item = listw["itemHeight"]
            gui_x = probe_list["gui"][0] + probe_list["gui"][2] // 2
            gui_y = probe_list["gui"][1] + args.row * item + item // 2
            dev_x = ox + int(round(gui_x * scale))
            dev_y = oy + int(round(gui_y * scale))
            say(f"CLICK row={args.row} gui=({gui_x},{gui_y}) device=({dev_x},{dev_y})")
            accepted = p204._click(dev_x, dev_y)
            result["click"] = {"row": args.row, "gui": [gui_x, gui_y], "device": [dev_x, dev_y],
                               "accepted": accepted}
            time.sleep(1.6)
            p204._grab_window(str(out / "sel-after.png"), pid)
            time.sleep(0.4)

            text = p204.read_text(client_log)
            after_lines = select_lines(text)
            result["select_after"] = after_lines[-1] if after_lines else None
            result["p205_select"] = after_lines
            widgets_after = {w["class"]: w for w in widget_lines(text)}
            result["description"] = widgets_after.get("DescriptionListWidget")
            result["widget_lines"] = [ln.split("STDOUT]: ", 1)[-1].strip() for ln in text.splitlines()
                                      if "P205_LIST" in ln]
            result["select_lines"] = [ln.split("STDOUT]: ", 1)[-1].strip() for ln in text.splitlines()
                                      if "P205_SELECT" in ln]
            scroll_after = re.findall(r"P204_SCROLL_STATE tick=\d+ scroll=([\d.]+)", text)
            result["scroll_after"] = float(scroll_after[-1]) if scroll_after else -1.0

            say("SELECT before=" + str(result["select_before"]))
            say("SELECT after=" + str(result["select_after"]))
            if result["description"] is None:
                say("DESCRIPTION no debug line (panel never rendered)")
            else:
                say("DESCRIPTION count=" + str(result["description"]["count"])
                    + " box=" + str(result["description"]["box"]))
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
