#!/usr/bin/env python3
"""p204: drive the Mod Menu screen with a REAL OS wheel and a REAL OS keyboard.

Why this exists
---------------
p104 recorded the wheel path as "not verified" after three Windows injection methods left the list
scroll at 0.0. p202 then found what was actually wrong with that class of run: the game window was
not on top, so the point under the cursor belonged to the terminal and nothing reached the game.
p204 re-runs the wheel on top of that fix, and adds the keyboard channel p104 also skipped.

What this harness does
----------------------
1. One client, nine patched mods, no server: the probe opens Mod Menu's ModsScreen from the title
   screen and announces where its list and search box are, in WINDOW coordinates.
2. Control A: park the cursor outside the game window and send five notches. Nothing may move.
3. Control B: park the cursor inside the window but off the list (right pane) and send five
   notches. The event may arrive (P204_SCROLL), the mod list's scroll amount may not.
4. Test: park the cursor over the list centre and send ONE notch at a time, reading the scroll
   amount after each. Vanilla moves the list by itemHeight/2 per notch, so the staircase is the
   prediction: 12, 24, 36, then clamped at max.
5. Keyboard: click the search box with a real left click, then type "menu" through
   SendInput KEYEVENTF_UNICODE. The probe logs every char the text field receives and the list's
   entry count, which has to fall.

The probe never writes the scroll amount; every number here is read from the widget.
"""
from __future__ import annotations

import argparse
import ctypes
import json
import os
import re
import shutil
import subprocess
import sys
import time
from ctypes import wintypes
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUN = Path(__file__).resolve().parent
CLIENT = ROOT / "work" / "launcher-e2e"
CLIENT_MODS = CLIENT / "mods"
FABRIC_API = ROOT / "work" / "instances" / "fabric-1.21.1-server" / "mods" / "fabric-api.jar"
PROBE = ROOT / "work" / "tmp" / "p204probe.jar"

# The p96/p202 combined set: every jar here is a patched build that already passed its own run.
MODS = [
    (ROOT / "work" / "client" / "modmenu-patched.jar", "modmenu-patched.jar"),
    (ROOT / "work" / "corpus" / "deps" / "balm-fabric-1.21.1-21.0.66.jar", "balm.jar"),
    (ROOT / "work" / "client" / "shulker-patched2.jar", "shulker-patched2.jar"),
    (ROOT / "work" / "client" / "sbtpreview.jar", "sbtpreview.jar"),
    (ROOT / "work" / "client" / "appleskin-patched.jar", "appleskin-patched.jar"),
    (ROOT / "work" / "client" / "ironchests-final.jar", "ironchests-final.jar"),
    (ROOT / "work" / "client" / "lithium-final.jar", "lithium-final.jar"),
    (ROOT / "work" / "client" / "trashslot-client-final.jar", "trashslot-client-final.jar"),
    (ROOT / "work" / "client" / "fallingtree-patched.jar", "fallingtree-patched.jar"),
]
USER = "WheelUser"

sys.path.insert(0, str(ROOT / "launcher"))
sys.path.insert(0, str(ROOT / "tools"))
import mclaunch  # noqa: E402
from test_launcher_e2e import _grab_window  # noqa: E402


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except FileNotFoundError:
        return ""


def setup_mods() -> list[str]:
    CLIENT_MODS.mkdir(parents=True, exist_ok=True)
    for path in CLIENT_MODS.glob("*.jar"):
        path.unlink()
    shutil.copy2(FABRIC_API, CLIENT_MODS / "fabric-api.jar")
    installed = ["fabric-api.jar"]
    for src, name in MODS:
        if not src.exists():
            raise SystemExit(f"missing mod jar: {src}")
        shutil.copy2(src, CLIENT_MODS / name)
        installed.append(name)
    shutil.copy2(PROBE, CLIENT_MODS / "p204probe.jar")
    installed.append("p204probe.jar")
    return installed


# ---------------------------------------------------------------- Win32 input
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_ABSOLUTE = 0x8000
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_WHEEL = 0x0800
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004
WHEEL_DOWN = 0xFFFFFF88  # -120 as an unsigned 32-bit wheel delta


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [("dx", wintypes.LONG), ("dy", wintypes.LONG),
                ("mouseData", wintypes.DWORD), ("dwFlags", wintypes.DWORD),
                ("time", wintypes.DWORD),
                ("dwExtraInfo", ctypes.POINTER(wintypes.ULONG))]


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [("wVk", wintypes.WORD), ("wScan", wintypes.WORD),
                ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD),
                ("dwExtraInfo", ctypes.POINTER(wintypes.ULONG))]


class _INPUTUNION(ctypes.Union):
    _fields_ = [("mi", MOUSEINPUT), ("ki", KEYBDINPUT)]


class INPUT(ctypes.Structure):
    _fields_ = [("type", wintypes.DWORD), ("u", _INPUTUNION)]


def _send_input(events: list[INPUT]) -> int:
    if not events:
        return 0
    array = (INPUT * len(events))(*events)
    return int(ctypes.windll.user32.SendInput(len(events), array, ctypes.sizeof(INPUT)))


def _window_handle(pid: int) -> int | None:
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
    user32 = ctypes.windll.user32
    rect = wintypes.RECT()
    user32.GetClientRect(hwnd, ctypes.byref(rect))
    point = wintypes.POINT(0, 0)
    user32.ClientToScreen(hwnd, ctypes.byref(point))
    return point.x, point.y, rect.right, rect.bottom


def _focus(hwnd: int) -> None:
    """Same raise-the-window fix p202 needed: a terminal on top eats every mouse message."""
    user32 = ctypes.windll.user32
    HWND_TOPMOST, HWND_NOTOPMOST = -1, -2
    flags = 0x0001 | 0x0002 | 0x0040  # NOSIZE | NOMOVE | SHOWWINDOW
    user32.ShowWindow(hwnd, 9)  # SW_RESTORE
    user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, flags)
    user32.SetForegroundWindow(hwnd)
    user32.SetWindowPos(hwnd, HWND_NOTOPMOST, 0, 0, 0, 0, flags)
    user32.BringWindowToTop(hwnd)


def _window_at(x: int, y: int) -> int:
    class POINT(ctypes.Structure):
        _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]

    return int(ctypes.windll.user32.WindowFromPoint(POINT(int(x), int(y))) or 0)


def _root_window(hwnd: int) -> int:
    return int(ctypes.windll.user32.GetAncestor(hwnd, 2) or 0)  # GA_ROOT


def _foreground() -> int:
    return int(ctypes.windll.user32.GetForegroundWindow() or 0)


def _ensure_foreground(hwnd: int) -> bool:
    """Make the game the real foreground window - keyboard events go to focus, not to the cursor.

    Mouse messages follow the point under the cursor, which is why p202 could fix hover with a
    raise alone. WM_KEYDOWN/WM_CHAR do not: they go to the focused window, and Windows often
    ignores a bare SetForegroundWindow from a background process. AttachThreadInput borrows the
    foreground thread's right to set it.
    """
    user32 = ctypes.windll.user32
    if _foreground() == hwnd:
        return True
    _focus(hwnd)
    time.sleep(0.4)
    if _foreground() == hwnd:
        return True
    fg = _foreground()
    tid_fg = user32.GetWindowThreadProcessId(fg, None)
    tid_me = ctypes.windll.kernel32.GetCurrentThreadId()
    attached = user32.AttachThreadInput(tid_me, tid_fg, True)
    user32.SetForegroundWindow(hwnd)
    user32.SetFocus(hwnd)
    user32.AttachThreadInput(tid_me, tid_fg, False)
    time.sleep(0.4)
    return _foreground() == hwnd


def _cursor_pos() -> tuple[int, int]:
    point = wintypes.POINT(0, 0)
    ctypes.windll.user32.GetCursorPos(ctypes.byref(point))
    return point.x, point.y


def _screen_size() -> tuple[int, int]:
    user32 = ctypes.windll.user32
    return int(user32.GetSystemMetrics(0)), int(user32.GetSystemMetrics(1))


def _move(x: int, y: int) -> int:
    """Absolute move through the OS input queue (a real WM_MOUSEMOVE, not a field write)."""
    screen_w, screen_h = _screen_size()
    nx = int(round(x * 65535 / max(screen_w - 1, 1)))
    ny = int(round(y * 65535 / max(screen_h - 1, 1)))
    event = INPUT()
    event.type = 0
    event.u.mi = MOUSEINPUT(nx, ny, 0, MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE, 0, None)
    return _send_input([event])


def _wheel(notches: int) -> int:
    """notches < 0 scrolls the content up (wheel down). One INPUT per notch."""
    events = []
    for _ in range(abs(notches)):
        event = INPUT()
        event.type = 0
        event.u.mi = MOUSEINPUT(0, 0, WHEEL_DOWN if notches < 0 else 120,
                                MOUSEEVENTF_WHEEL, 0, None)
        events.append(event)
    return _send_input(events)


def _click(x: int, y: int) -> int:
    move = INPUT()
    move.type = 0
    screen_w, screen_h = _screen_size()
    move.u.mi = MOUSEINPUT(int(round(x * 65535 / max(screen_w - 1, 1))),
                           int(round(y * 65535 / max(screen_h - 1, 1))), 0,
                           MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE, 0, None)
    down = INPUT()
    down.type = 0
    down.u.mi = MOUSEINPUT(0, 0, 0, MOUSEEVENTF_LEFTDOWN, 0, None)
    up = INPUT()
    up.type = 0
    up.u.mi = MOUSEINPUT(0, 0, 0, MOUSEEVENTF_LEFTUP, 0, None)
    return _send_input([move, down, up])


def _type_text(text: str) -> int:
    """Type through KEYEVENTF_UNICODE: no keyboard layout is involved, WM_CHAR carries the char."""
    events = []
    for chr_ in text:
        for flags in (KEYEVENTF_UNICODE, KEYEVENTF_UNICODE | KEYEVENTF_KEYUP):
            event = INPUT()
            event.type = 1
            event.u.ki = KEYBDINPUT(0, ord(chr_), flags, 0, None)
            events.append(event)
    return _send_input(events)


# ---------------------------------------------------------------- log helpers
def parse_point(log: str, name: str) -> tuple[int, int] | None:
    match = re.search(rf"P204_POINT {name} win=(-?\d+),(-?\d+)", log)
    return (int(match.group(1)), int(match.group(2))) if match else None


def parse_rect(log: str, kind: str) -> dict | None:
    match = re.search(rf"P204_RECT {kind} gui=(-?\d+),(-?\d+),(-?\d+),(-?\d+) win=(-?\d+),(-?\d+)",
                      log)
    if not match:
        return None
    gui = [int(g) for g in match.groups()[:4]]
    win = [int(g) for g in match.groups()[4:]]
    return {"gui": gui, "win": win}


def last_int(text: str, pattern: str, default: int = -1) -> int:
    found = re.findall(pattern, text)
    return int(found[-1]) if found else default


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--timeout", type=int, default=300)
    ap.add_argument("--out", default=None)
    ap.add_argument("--notches", type=int, default=5)
    args = ap.parse_args()
    global RUN
    if args.out:
        RUN = Path(args.out)
    RUN.mkdir(parents=True, exist_ok=True)
    if not PROBE.exists():
        print(f"missing probe jar: {PROBE}; run build.py first", file=sys.stderr)
        return 2
    installed = setup_mods()

    harness_log = RUN / "harness.log"
    harness_lines: list[str] = []

    def say(message: str) -> None:
        print(message)
        harness_lines.append(message)
        harness_log.write_text("\n".join(harness_lines) + "\n", encoding="utf-8")

    client_log = RUN / "client.log"
    client_log.write_text("", encoding="utf-8")
    cmd, _, _ = mclaunch.build_command(
        "fabric-loader-0.19.5-1.21.1", CLIENT, USER, "2G",
        extra_game=["--width", "1280", "--height", "720"])
    say("mods: " + ", ".join(installed))

    with client_log.open("w", encoding="utf-8", errors="replace") as cout:
        cout.write(" ".join(cmd) + "\n")
        cout.flush()
        client = subprocess.Popen(cmd, cwd=str(CLIENT), stdout=cout, stderr=subprocess.STDOUT)
        try:
            deadline = time.time() + args.timeout
            ready = False
            while time.time() < deadline:
                if "P204_READY" in read_text(client_log):
                    ready = True
                    break
                if client.poll() is not None:
                    break
                time.sleep(0.5)
            if not ready:
                tail = "\n".join(read_text(client_log).splitlines()[-16:])
                say("probe never became ready; client tail:")
                say(tail)
                return 1
            time.sleep(1.0)
            log = read_text(client_log)
            list_rect = parse_rect(log, "list")
            search_rect = parse_rect(log, "search")
            list_center = parse_point(log, "listCenter")
            search_center = parse_point(log, "searchCenter")
            say(f"READY list={list_rect} search={search_rect} "
                f"listCenter={list_center} searchCenter={search_center}")
            if list_center is None or list_rect is None:
                say("probe did not announce the list geometry")
                return 1
            window = re.search(r"P204_WINDOW handle=(\d+) m4480=(\d+) m4486=(\d+) "
                               r"m4502=(\d+) m4507=(\d+) scale=([\d.]+)", log)
            say("WINDOW " + (window.group(0) if window else "missing"))

            pid = client.pid
            hwnd = _window_handle(pid)
            if not hwnd:
                say("no window handle for the client pid")
                return 1
            _focus(hwnd)
            time.sleep(0.4)
            ox, oy, cw, ch = _client_origin(hwnd)
            say(f"CLIENTAREA origin=({ox},{oy}) size={cw}x{ch} hwnd={hwnd}")

            def move_to(name: str, point: tuple[int, int]) -> tuple[int, int]:
                x, y = ox + point[0], oy + point[1]
                accepted = _move(x, y)
                time.sleep(0.35)
                cx, cy = _cursor_pos()
                under = _window_at(cx, cy)
                is_game = _root_window(under) == _root_window(hwnd)
                say(f"MOVE {name} requested=({x},{y}) accepted={accepted} "
                    f"cursorNow=({cx},{cy}) underIsGame={is_game}")
                return cx, cy

            def scroll_now() -> tuple[float, int]:
                text = read_text(client_log)
                states = re.findall(r"P204_SCROLL_STATE tick=\d+ scroll=([\d.]+)", text)
                events = len(re.findall(r"P204_SCROLL n=", text))
                return (float(states[-1]) if states else -1.0), events

            result: dict = {"mods": installed, "list": list_rect, "search": search_rect}
            if window:
                result["window"] = {"client_w": int(window.group(2)),
                                    "client_h": int(window.group(5)),
                                    "scale": float(window.group(6))}
            item_height = last_int(log, r"itemHeight=(\d+)")
            expected_step = item_height / 2.0
            maximum = last_int(log, r" max=(-?\d+)")
            entries_before = last_int(log, r"entries=(\d+)")
            result.update({"item_height": item_height, "expected_step": expected_step,
                           "max_scroll": maximum, "entries_before": entries_before})
            say(f"PREDICT itemHeight={item_height} step={expected_step} max={maximum} "
                f"entries={entries_before}")

            # ---- control A: wheel with the cursor outside the game window
            screen_w, screen_h = _screen_size()
            candidates = [(ox + cw + 60, oy + ch // 2), (ox - 60, oy + ch // 2),
                          (ox + cw // 2, oy - 45), (ox + cw // 2, oy + ch + 45)]
            outside = None
            for x, y in candidates:
                if not (2 <= x < screen_w - 2 and 2 <= y < screen_h - 2):
                    continue
                under = _window_at(x, y)
                if _root_window(under) != _root_window(hwnd):
                    outside = (x, y)
                    break
            before_scroll, before_events = scroll_now()
            control_a = {"point": outside, "under_is_game": False}
            if outside is None:
                control_a["skipped"] = "no screen point outside the window"
                say("CONTROL_A skipped: every candidate point still hits the game window")
            else:
                cx, cy = _cursor_pos()
                _move(*outside)
                time.sleep(0.3)
                cx, cy = _cursor_pos()
                control_a["under_is_game"] = _root_window(_window_at(cx, cy)) == _root_window(hwnd)
                accepted = _wheel(-args.notches)
                time.sleep(1.2)
                after_scroll, after_events = scroll_now()
                control_a.update({"accepted": accepted, "scroll_before": before_scroll,
                                  "scroll_after": after_scroll,
                                  "events_delta": after_events - before_events,
                                  "cursor": [cx, cy]})
                say(f"CONTROL_A outside={outside} underIsGame={control_a['under_is_game']} "
                    f"accepted={accepted} scroll {before_scroll} -> {after_scroll} "
                    f"eventsDelta={after_events - before_events}")
            result["control_a"] = control_a

            # ---- control B: same window, cursor off the list (right pane)
            pane_point = (cw - 40, list_center[1])
            _move(ox + pane_point[0], oy + pane_point[1])
            time.sleep(0.4)
            before_scroll, before_events = scroll_now()
            accepted = _wheel(-args.notches)
            time.sleep(1.2)
            after_scroll, after_events = scroll_now()
            control_b = {"offset": list(pane_point), "accepted": accepted,
                         "scroll_before": before_scroll, "scroll_after": after_scroll,
                         "events_delta": after_events - before_events}
            say(f"CONTROL_B pane=({pane_point[0]},{pane_point[1]}) accepted={accepted} "
                f"scroll {before_scroll} -> {after_scroll} "
                f"eventsDelta={after_events - before_events}")
            result["control_b"] = control_b

            # ---- test: one notch at a time over the list centre
            move_to("listCenter", list_center)
            _grab_window(str(RUN / "list-before.png"), pid)
            time.sleep(0.6)
            steps = []
            first_notch_at = -1
            for n in range(1, args.notches + 1):
                _wheel(-1)
                time.sleep(0.9)
                scroll, events = scroll_now()
                steps.append({"notch": n, "scroll": scroll, "scroll_events": events})
                say(f"WHEEL notch={n} scroll={scroll} scrollEvents={events}")
                if n == 1:
                    first_notch_at = 1
                    _grab_window(str(RUN / "list-scrolled.png"), pid)
                    time.sleep(0.6)
                    move_to("listCenter-again", list_center)
            result["wheel_steps"] = steps
            result["scroll_before_wheel"] = before_scroll
            _grab_window(str(RUN / "list-scrolled-max.png"), pid)
            time.sleep(0.6)

            # ---- keyboard: real click into the search box, then real typed chars
            if search_center:
                focus_ok = _ensure_foreground(hwnd)
                say(f"FOREGROUND hwnd={hwnd} foreground={_foreground()} ok={focus_ok}")
                _click(ox + search_center[0], oy + search_center[1])
                time.sleep(0.8)
                probe_focus = re.findall(r"searchFocused=(true|false)", read_text(client_log))
                say(f"CLICK searchCenter={search_center} searchFocused={probe_focus[-3:]}")
                typed = _type_text("menu")
                time.sleep(2.5)
                text_after = read_text(client_log)
                search_text = re.findall(r'text="([^"]*)"', text_after)
                entries_after = last_int(text_after, r"entries=(\d+)")
                chars = len(re.findall(r"P204_CHAR n=", text_after))
                keys = len(re.findall(r"P204_KEY n=", text_after))
                result["keyboard"] = {"click": list(search_center), "sent": "menu",
                                      "accepted": typed, "chars": chars, "keys": keys,
                                      "text_after": search_text[-1] if search_text else "",
                                      "entries_after": entries_after,
                                      "foreground": focus_ok}
                say(f"KEYBOARD click={search_center} sent=menu accepted={typed} "
                    f"chars={chars} keys={keys} "
                    f"text={search_text[-1] if search_text else ''} entries={entries_after}")
                _grab_window(str(RUN / "list-filtered.png"), pid)
                for _ in range(30):
                    if "P204_DONE" in read_text(client_log):
                        break
                    time.sleep(0.5)
            else:
                result["keyboard"] = {"skipped": "no search box"}

            text = read_text(client_log)
            result["scroll_events_total"] = len(re.findall(r"P204_SCROLL n=", text))
            result["raw_scroll_lines"] = [ln.strip() for ln in text.splitlines()
                                          if "P204_SCROLL n=" in ln][:12]
            result["done"] = next((ln.strip() for ln in text.splitlines() if "P204_DONE" in ln), "")

            # ---- verdict
            checks = {}
            checks["probe_ready"] = bool(result.get("list"))
            checks["control_a_no_event"] = (control_a.get("skipped") is not None
                                            or control_a.get("events_delta") == 0)
            checks["control_b_list_unchanged"] = (
                abs(control_b["scroll_after"] - control_b["scroll_before"]) < 1e-6)
            increments = []
            previous = steps[0]["scroll"] - expected_step if steps else 0
            for step in steps:
                increments.append(round(step["scroll"] - previous, 3))
                previous = step["scroll"]
            result["increments"] = increments
            expected = []
            running = 0.0
            for _ in steps:
                running = min(running + expected_step, float(maximum))
                expected.append(running)
            checks["wheel_staircase"] = bool(steps) and all(
                abs(s["scroll"] - e) <= 0.01 for s, e in zip(steps, expected))
            checks["wheel_reached_max"] = bool(steps) and abs(steps[-1]["scroll"] - maximum) < 0.01
            keyboard = result.get("keyboard") or {}
            checks["keyboard_text"] = keyboard.get("text_after") == "menu"
            checks["keyboard_filter"] = (keyboard.get("entries_after", entries_before)
                                         < entries_before)
            result["checks"] = checks
            result["passed"] = all(checks.values())
            (RUN / "result.json").write_text(
                json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(json.dumps(checks, ensure_ascii=False))
            return 0 if result["passed"] else 1
        finally:
            if client.poll() is None:
                client.terminate()
                try:
                    client.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    client.kill()


if __name__ == "__main__":
    sys.exit(main())
