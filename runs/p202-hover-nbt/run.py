#!/usr/bin/env python3
"""p202: OS-cursor hover + 27 heterogeneous NBT stacks in a Shulker preview.

Why this exists
---------------
p193/p196/p197 proved the preview grid, the server-synced box and the rebindable preview keys, but
every hover in those runs was aimed by writing Mouse.field_1795/field_1794 through an accessor.
That is a probe poke: it proves the renderer works, not that a real cursor position reaches the
game. And all 27 slots held distinct ITEM IDS with identical (empty) component maps.

What this harness does
----------------------
1. The server places a 27-slot shulker box where every slot differs: item id, count, custom name,
   and a mix of lore / enchantments / custom_model_data.
2. The client probe opens the survival inventory and announces the WINDOW coordinates of slot 10
   (P202_TARGET). It never writes mouse state.
3. This script moves the OS cursor there with user32.SetCursorPos (after focusing the window), and
   logs the client-area origin it converted from, so the numbers can be checked.
4. Hover has to arrive through WM_MOUSEMOVE -> GLFW callback -> Mouse.onTick -> Screen.render ->
   HandledScreen.focusedSlot. The probe prints GLFW's own position and the game's computed position
   side by side (P202_CURSOR) and only then P202_HOVER_OK with keysSent=false.
5. Only after the hover is on record are the preview keys (J=74 -> COMPACT, +K=75 -> FULL) forged
   at the poll boundary, exactly as in p197.

If the OS move never reaches the window, the probe says P202_FALLBACK and uses glfwSetCursorPos;
the run then reports glfwCursor=true / osCursor=false instead of pretending they are the same.
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
CLIENT_MODS = CLIENT / "mods"
FABRIC_API = ROOT / "work" / "instances" / "fabric-1.21.1-server" / "mods" / "fabric-api.jar"
BALM = ROOT / "work" / "corpus" / "deps" / "balm-fabric-1.21.1-21.0.66.jar"
SHULKER = ROOT / "work" / "client" / "shulker-patched2.jar"
SBT = ROOT / "work" / "client" / "sbtpreview.jar"
PROBE = ROOT / "work" / "tmp" / "p202probe.jar"
PORT = "25567"
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
    shutil.copy2(PROBE, CLIENT_MODS / "p202probe.jar")


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


def _slot_item(index: int) -> str:
    """One container entry whose components differ from every other entry."""
    item = ITEM_IDS[index]
    count = (index % 3) + 1
    tag = f"S{index:02d}"
    components = [f"\"minecraft:custom_name\":'{{\"text\":\"{tag}\"}}'"]
    if index % 3 == 0:
        components.append(
            f"\"minecraft:lore\":['{{\"text\":\"{tag} lore A\"}}',"
            f"'{{\"text\":\"{tag} lore B\"}}']")
    if index % 4 == 0:
        components.append(
            "\"minecraft:enchantments\":{levels:{\"minecraft:sharpness\":%d}}" % ((index % 5) + 1))
    if index % 5 == 1:
        components.append("\"minecraft:custom_model_data\":%d" % (100 + index))
    return (f"{{slot:{index},item:{{id:\"minecraft:{item}\",count:{count},"
            f"components:{{{','.join(components)}}}}}}}")


def rich_box_command() -> str:
    entries = ",".join(_slot_item(i) for i in range(27))
    return (f"item replace entity {USER} container.10 with "
            f"minecraft:shulker_box[minecraft:container=[{entries}]]")


def plain_box_command() -> str:
    entries = ",".join(f'{{slot:{i},item:{{id:"minecraft:{item}",count:{(i % 3) + 1}}}}}'
                       for i, item in enumerate(ITEM_IDS))
    return (f"item replace entity {USER} container.10 with "
            f"minecraft:shulker_box[minecraft:container=[{entries}]]")


# ---------------------------------------------------------------- OS cursor control
def _window_handle(pid: int) -> int | None:
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    found: list[int] = []

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def _enum(hwnd, _lparam):  # noqa: ANN001
        if not user32.IsWindowVisible(hwnd):
            return True
        owner = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(owner))
        if owner.value == pid:
            found.append(hwnd)
        return True

    user32.EnumWindows(_enum, 0)
    return found[0] if found else None


def _client_origin(hwnd: int) -> tuple[int, int, int, int]:
    """Screen coordinates of the client area's top-left corner, plus its size."""
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    rect = wintypes.RECT()
    user32.GetClientRect(hwnd, ctypes.byref(rect))
    point = wintypes.POINT(0, 0)
    user32.ClientToScreen(hwnd, ctypes.byref(point))
    return point.x, point.y, rect.right, rect.bottom


def _focus(hwnd: int) -> None:
    """Raise the game window for real.

    "Focused" (WM_SETFOCUS) is not the same as "the window a point hits": an automated run keeps a
    terminal on top of the game, so a cursor moved into the game's rectangle can land on the
    terminal and the game never gets a mouse message. SWP_TOPMOST is the only reliable way to put
    it above our own window from a background process (SetForegroundWindow is frequently ignored).
    """
    import ctypes

    user32 = ctypes.windll.user32
    HWND_TOPMOST = -1
    HWND_NOTOPMOST = -2
    SWP_NOSIZE = 0x0001
    SWP_NOMOVE = 0x0002
    SWP_SHOWWINDOW = 0x0040
    user32.ShowWindow(hwnd, 9)  # SW_RESTORE
    user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0,
                        SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW)
    user32.SetForegroundWindow(hwnd)
    user32.SetWindowPos(hwnd, HWND_NOTOPMOST, 0, 0, 0, 0,
                        SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW)
    user32.BringWindowToTop(hwnd)


def _window_at(x: int, y: int) -> int:
    """Which window would receive a mouse message at this screen point?"""
    import ctypes
    from ctypes import wintypes

    class POINT(ctypes.Structure):
        _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]

    point = POINT(int(x), int(y))
    return int(ctypes.windll.user32.WindowFromPoint(point) or 0)


def _root_window(hwnd: int) -> int:
    import ctypes

    return int(ctypes.windll.user32.GetAncestor(hwnd, 2) or 0)  # GA_ROOT


def _cursor_pos() -> tuple[int, int]:
    import ctypes
    from ctypes import wintypes

    point = wintypes.POINT(0, 0)
    ctypes.windll.user32.GetCursorPos(ctypes.byref(point))
    return point.x, point.y


def _set_cursor(x: int, y: int) -> tuple[int, int, int]:
    """Warp the pointer with SetCursorPos. Returns (sent, cursorX, cursorY)."""
    import ctypes

    user32 = ctypes.windll.user32
    user32.SetCursorPos(int(x), int(y))
    cx, cy = _cursor_pos()
    return 1, cx, cy


def _send_input_move(x: int, y: int) -> tuple[int, int, int]:
    """Inject an absolute mouse move into the OS input stream (SendInput).

    This is the difference from p191/p193/p197: the cursor is moved by the window manager's input
    queue, so the game gets a real WM_MOUSEMOVE instead of a field write. Returns
    (eventsAccepted, cursorX, cursorY).
    """
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    screen_w = user32.GetSystemMetrics(0) or 1
    screen_h = user32.GetSystemMetrics(1) or 1
    nx = int(round(x * 65535 / max(screen_w - 1, 1)))
    ny = int(round(y * 65535 / max(screen_h - 1, 1)))

    class MOUSEINPUT(ctypes.Structure):
        _fields_ = [("dx", wintypes.LONG), ("dy", wintypes.LONG),
                    ("mouseData", wintypes.DWORD), ("dwFlags", wintypes.DWORD),
                    ("time", wintypes.DWORD),
                    ("dwExtraInfo", ctypes.POINTER(wintypes.ULONG))]

    class INPUT(ctypes.Structure):
        _fields_ = [("type", wintypes.DWORD), ("mi", MOUSEINPUT)]

    MOUSEEVENTF_MOVE = 0x0001
    MOUSEEVENTF_ABSOLUTE = 0x8000
    event = INPUT()
    event.type = 0
    event.mi = MOUSEINPUT(nx, ny, 0, MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE, 0, None)
    accepted = user32.SendInput(1, ctypes.byref(event), ctypes.sizeof(INPUT))
    cx, cy = _cursor_pos()
    return int(accepted), cx, cy


def _target_from_log(text: str) -> tuple[float, float] | None:
    match = re.search(r"P202_TARGET gx=[-\d.]+ gy=[-\d.]+ scale=[-\d.]+ "
                      r"winx=([-\d.]+) winy=([-\d.]+)", text)
    if not match:
        return None
    return float(match.group(1)), float(match.group(2))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--timeout", type=int, default=420)
    ap.add_argument("--cursor-mechanism", choices=("mixed", "sendinput", "warp"),
                    default="mixed",
                    help="mixed = 2x SendInput then 1x SetCursorPos (the A/B in the committed "
                         "log); warp = SetCursorPos only (control: does a pointer warp alone "
                         "produce a hover?); sendinput = injected input only")
    ap.add_argument("--out", default=None,
                    help="write logs/screenshots here instead of runs/p202-hover-nbt")
    args = ap.parse_args()
    global RUN
    if args.out:
        RUN = Path(args.out)
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
    harness_log = RUN / "harness.log"
    harness_lines: list[str] = []

    def say(message: str) -> None:
        print(message)
        harness_lines.append(message)
        harness_log.write_text("\n".join(harness_lines) + "\n", encoding="utf-8")

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
                say("server did not start; tail:")
                say("\n".join(read_text(server_log).splitlines()[-12:]))
                return 2
            say("server ready")

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
                    placed = False
                    placed_at = 0.0
                    moved = 0
                    full_shot = False
                    done = False
                    box_mode = "none"
                    while time.time() < deadline:
                        if not placed and "joined the game" in read_text(server_log):
                            placed = True
                            placed_at = time.time()
                            server.stdin.write((rich_box_command() + "\n").encode("utf-8"))
                            server.stdin.write(
                                (f"data get entity {USER} Inventory[{{Slot:10b}}]\n").encode())
                            server.stdin.flush()
                            say("server sent the 27-slot heterogeneous box")
                        now = read_text(client_log)
                        # 1) the probe announced the window target: move the real cursor there
                        if placed and moved < 3:
                            target = _target_from_log(now)
                            if target is not None:
                                pid = client.pid
                                hwnd = _window_handle(pid)
                                if hwnd:
                                    _focus(hwnd)
                                    time.sleep(0.3)
                                    ox, oy, cw, ch = _client_origin(hwnd)
                                    jitter = [(0, 0), (0, 1), (1, 0)][moved]
                                    sx = ox + int(round(target[0])) + jitter[0]
                                    sy = oy + int(round(target[1])) + jitter[1]
                                    # moves 1-2 inject into the OS input queue; move 3 is a bare
                                    # SetCursorPos warp, kept as the A/B the first run lacked
                                    mode = args.cursor_mechanism
                                    if mode == "warp" or (mode == "mixed" and moved >= 2):
                                        mechanism = "setcursorpos"
                                        accepted, cx, cy = _set_cursor(sx, sy)
                                    else:
                                        mechanism = "sendinput"
                                        accepted, cx, cy = _send_input_move(sx, sy)
                                    moved += 1
                                    under = _window_at(cx, cy)
                                    say(f"OSMOVE {moved} mechanism={mechanism} hwnd={hwnd} "
                                        f"clientOrigin=({ox},{oy}) clientSize={cw}x{ch} "
                                        f"targetWin=({target[0]:.1f},{target[1]:.1f}) "
                                        f"requested=({sx},{sy}) accepted={accepted} "
                                        f"cursorNow=({cx},{cy}) underCursor={under} "
                                        f"underIsGame={_root_window(under) == _root_window(hwnd)}")
                                else:
                                    say("OSMOVE skipped: no window handle for pid")
                        # A bad component name would make the whole /item replace fail atomically,
                        # so watch the server's answer and fall back to the plain box (same 27 item
                        # ids, no per-slot components) instead of reporting a cargo-cult failure.
                        if placed and box_mode == "none" and time.time() > placed_at + 6:
                            tail = read_text(server_log)
                            broken = any(marker in tail for marker in
                                         ("Unknown item component", "Expected", "Couldn't parse",
                                          "Unknown data component", "Invalid"))
                            if broken:
                                box_mode = "plain"
                                server.stdin.write((plain_box_command() + "\n").encode("utf-8"))
                                server.stdin.flush()
                                say("rich box command rejected by the server; sent the plain box")
                            else:
                                box_mode = "rich"
                                say("rich box command accepted (no parser error in server.log)")
                        if "P202_FALLBACK" in now and box_mode == "none":
                            say("probe reported P202_FALLBACK (OS move did not reach the window)")
                        if "P202_FULL_REQUEST" in now and not full_shot:
                            full_shot = True
                            time.sleep(3)
                            _grab_window(str(RUN / "after-full.png"), client.pid)
                            say("FULL screenshot taken")
                        if "P202_DONE" in now:
                            done = True
                            break
                        if client.poll() is not None:
                            break
                        time.sleep(0.5)
                    if not done:
                        tail = "\n".join(read_text(client_log).splitlines()[-16:])
                        say(f"probe did not finish (placed={placed} moved={moved}); client tail:")
                        say(tail)
                        return 1

                    text = read_text(client_log)
                    ser = read_text(server_log)
                    lines_c = text.splitlines()

                    def pick(marker: str, limit: int = 40) -> list[str]:
                        return [ln.split(marker, 1)[1].strip() for ln in lines_c if marker in ln]

                    target_line = next((ln for ln in lines_c if "P202_TARGET " in ln), "")
                    window_line = next((ln for ln in lines_c if "P202_WINDOW " in ln), "")
                    hover_lines = [ln for ln in lines_c if "P202_HOVER_OK" in ln]
                    fallback_lines = [ln for ln in lines_c if "P202_FALLBACK" in ln]
                    cursor_lines = [ln.split("P202_CURSOR ", 1)[1].strip()
                                    for ln in lines_c if "P202_CURSOR " in ln]
                    nbt_lines = [ln.split("P202_NBT ", 1)[1].strip()
                                 for ln in lines_c if "P202_NBT " in ln]
                    nbt_sum = pick("P202_NBT_SUM ")
                    drawitems = pick("P202_DRAWITEMS ")
                    drawitem = pick("P202_DRAWITEM ")
                    tooltip = [ln for ln in lines_c if "P202_TOOLTIP" in ln]
                    done_line = pick("P202_DONE ")
                    poll_line = pick("P202_POLLS ")

                    hover_index = None
                    keys_sent_at_hover = None
                    if hover_lines:
                        match = re.search(r"index=(-?\d+)", hover_lines[0])
                        hover_index = int(match.group(1)) if match else None
                        keys_sent_at_hover = "keysSent=false" in hover_lines[0]
                    os_cursor = bool(hover_lines) and not fallback_lines[:1]
                    glfw_cursor = bool(hover_lines) and bool(fallback_lines)
                    hover_before_keys = bool(hover_lines) and keys_sent_at_hover is True

                    names = set()
                    items_seen = set()
                    for line in nbt_lines:
                        match = re.search(r"name=(.*?) comps=", line)
                        if match:
                            names.add(match.group(1))
                        match = re.search(r"item=(minecraft:[a-z_]+)", line)
                        if match:
                            items_seen.add(match.group(1))
                    nbt_count = len(nbt_lines)
                    heterogeneous = (nbt_count == 27 and len(names) == 27
                                     and len(items_seen) == 27
                                     and any("stacks=27 distinctComponents=27" in s
                                             for s in nbt_sum))

                    distinct_draw = len({ln.split("comps=", 1)[1] for ln in drawitem
                                         if "comps=" in ln})
                    indices = sorted({int(re.search(r"index=(-?\d+)", ln).group(1))
                                      for ln in drawitem if "index=" in ln})
                    full_27 = any("type=FULL" in ln and "items=27" in ln for ln in drawitems)
                    grid_cells = len(indices) >= 27 and indices[:27] == list(range(27))

                    tooltip_mod = any("data=com.misterpemodder" in ln for ln in tooltip)

                    result = {
                        "target_line": target_line,
                        "window_line": window_line,
                        "hover_line": hover_lines[0] if hover_lines else "",
                        "hover_index": hover_index,
                        "hover_before_keys": hover_before_keys,
                        "os_cursor_hover": os_cursor,
                        "glfw_cursor_fallback": glfw_cursor,
                        "fallback_lines": fallback_lines[:4],
                        "cursor_samples": cursor_lines[:12],
                        "box_mode": box_mode,
                        "nbt_stacks": nbt_count,
                        "nbt_distinct_names": len(names),
                        "nbt_distinct_items": len(items_seen),
                        "nbt_sum": nbt_sum[0] if nbt_sum else "",
                        "nbt_heterogeneous": heterogeneous,
                        "nbt_sample": nbt_lines[:4],
                        "drawitems": drawitems[-6:],
                        "drawitem_count": len(drawitem),
                        "drawitem_distinct": distinct_draw,
                        "drawitem_indices": indices[:30],
                        "full_grid_27": full_27,
                        "grid_cells_0_to_26": grid_cells,
                        "tooltip_lines": tooltip[:4],
                        "tooltip_from_mod": tooltip_mod,
                        "polls": poll_line[0] if poll_line else "",
                        "done": done_line[0] if done_line else "",
                        "os_moves": [ln for ln in harness_lines if ln.startswith("OSMOVE")],
                        "client_tail": lines_c[-12:],
                        "server_tail": ser.splitlines()[-8:],
                    }
                    (RUN / "result.json").write_text(
                        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                    keys = ("os_cursor_hover" if os_cursor else "glfw_cursor_fallback",
                            "hover_before_keys", "nbt_heterogeneous", "full_grid_27",
                            "grid_cells_0_to_26", "tooltip_from_mod")
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
