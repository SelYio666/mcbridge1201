"""Drive the description panel with a real OS wheel, and check the scrollbar it draws (p209).

p207's verdict printed "scrollbar not drawn in this run (maxScroll=0: no description long enough to
scroll)", so the branch that draws it had never executed. This harness makes it execute, without
inventing a fake description:

* the window is narrower (800 px instead of 1280), so the same text wraps into more lines and the
  same 216 px tall panel has to scroll;
* it clicks every fully visible row and records each mod's row count and `maxScroll`, so the row
  that needs scrolling is found by measurement, not by guessing which mod has a long description;
* on that row it parks the cursor over the panel, sends real wheel notches through the OS input
  queue, and shoots before/after;
* then it sends the same notches over the *mod list* and checks that the panel does not move, so
  "the wheel goes to whatever is under the cursor" is tested in both directions instead of assumed.

Both sides of that comparison are read from the bridge's own `P205_LIST` line, which reports
`scroll=`/`max=` per widget. The probe's `P204_SCROLL_STATE` cannot be used for it: `findList` picks
the EntryListWidget with the largest `maxScroll`, so as soon as a long description is selected it
starts reporting the *description panel* instead of the mod list. That is recorded in the result as
`probe_latched_onto` rather than silently mixed in.

Everything else is p204/p206: same client, same eleven mods, same raise-window + foreground dance,
same click-by-computed-centre. Only the jar and the window width differ.

Usage:
  python runs/p209-description-scroll/run.py --modmenu work/client/modmenu-scroll.jar \
      --out runs/p209-description-scroll/after
  python runs/p209-description-scroll/run.py --modmenu work/client/modmenu-description.jar \
      --out runs/p209-description-scroll/before --rows 0-6     # control: p207 jar, no scroll line
"""
import argparse
import hashlib
import importlib.util
import json
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CLIENT = ROOT / "work" / "launcher-e2e"
USER = "ScrollUser"

SCROLL_LINE = re.compile(
    r"P207_SCROLL class=(\S+) scroll=([\d.]+) max=(-?\d+) view=(-?\d+) drawn=(true|false) "
    r"thumb=(\S+)")
# The p207 jar prints the same line in an older shape: no view=/drawn=, and only after the early
# return, so a line existing at all means the scrollbar was drawn. Accepted here so the control run
# measures behaviour instead of dying on a format difference.
SCROLL_LINE_P207 = re.compile(
    r"P207_SCROLL class=(\S+) scroll=([\d.]+) max=(-?\d+) thumb=(\S+) x=(-?\d+)\.\.(-?\d+)")
PANEL_LINE = re.compile(
    r"P207_PANEL class=(\S+) box=(-?\d+),(-?\d+),(-?\d+),(-?\d+) count=(-?\d+) legacy=(\w+) "
    r"rowLeft=(-?\d+)")
# P205_LIST gained scroll=/max= in p209; both trailing groups are optional so the p207 jar (which
# does not print them) still parses with the same expression.
LIST_LINE = re.compile(
    r"P205_LIST class=(\S+) count=(-?\d+) left=(-?\d+) rowWidth=(-?\d+) itemHeight=(-?\d+) "
    r"rows=(-?\d+)\.\.(-?\d+) mouse=(-?\d+),(-?\d+) focused=(true|false) "
    r"box=(-?\d+),(-?\d+),(-?\d+),(-?\d+) legacy=(\w+) getX=(-?\d+)"
    r"(?: scroll=([\d.]+) max=(-?\d+))?(?: firstEntry=(\S+))?")


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# p204 owns every input primitive (real WM_MOUSEMOVE / WM_MOUSEWHEEL / WM_LBUTTON*); p206 owns the
# mod set and the mod-menu jar swap. Reusing them keeps the runs comparable - a re-implementation
# here would be a second variable.
p204 = load(ROOT / "runs" / "p204-wheel-input" / "run.py", "p204harness")
p206 = load(ROOT / "runs" / "p206-modmenu-select" / "run.py", "p206harness")


def list_states(text: str) -> list[dict]:
    out = []
    for m in LIST_LINE.finditer(text):
        out.append({"class": m.group(1), "count": int(m.group(2)), "left": int(m.group(3)),
                    "rowWidth": int(m.group(4)), "itemHeight": int(m.group(5)),
                    "rows": [int(m.group(6)), int(m.group(7))],
                    "mouse": [int(m.group(8)), int(m.group(9))], "focused": m.group(10) == "true",
                    "box": [int(m.group(i)) for i in (11, 12, 13, 14)],
                    "legacy": m.group(15) == "true", "getX": int(m.group(16)),
                    "scroll": float(m.group(17)) if m.group(17) is not None else None,
                    "max": int(m.group(18)) if m.group(18) is not None else None,
                    "first": m.group(19)})
    return out


def scroll_states(text: str) -> list[dict]:
    out = []
    for m in SCROLL_LINE.finditer(text):
        out.append({"class": m.group(1), "scroll": float(m.group(2)), "max": int(m.group(3)),
                    "view": int(m.group(4)), "drawn": m.group(5) == "true", "thumb": m.group(6),
                    "format": "p209"})
    if not out:
        for m in SCROLL_LINE_P207.finditer(text):
            # No drawn= field: the p207 bridge only reached its print after drawing, so the line's
            # existence is the evidence, and view= is not reported (it is the box height).
            out.append({"class": m.group(1), "scroll": float(m.group(2)), "max": int(m.group(3)),
                        "view": None, "drawn": True, "thumb": m.group(4), "format": "p207"})
    return out


def panel_boxes(text: str) -> dict:
    out = {}
    for m in PANEL_LINE.finditer(text):
        out[m.group(1)] = {"box": [int(m.group(i)) for i in (2, 3, 4, 5)],
                           "count": int(m.group(6)), "legacy": m.group(7) == "true",
                           "rowLeft": int(m.group(8))}
    return out


def last_of(states: list[dict], cls: str) -> dict | None:
    found = [s for s in states if s["class"] == cls]
    return found[-1] if found else None


def last_float(text: str, pattern: str, default: float = -1.0) -> float:
    """The probe prints scroll amounts as 18.0, so p204.last_int would blow up on them."""
    found = re.findall(pattern, text)
    return float(found[-1]) if found else default


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--modmenu", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--timeout", type=int, default=300)
    ap.add_argument("--width", type=int, default=800)
    ap.add_argument("--height", type=int, default=720)
    ap.add_argument("--notches", type=int, default=3)
    ap.add_argument("--rows", default="", help="rows to scan; default = every fully visible row")
    ap.add_argument("--row", type=int, default=-1, help="scroll this row instead of the scan result")
    args = ap.parse_args()

    out = Path(args.out)
    if not out.is_absolute():
        out = ROOT / out
    out.mkdir(parents=True, exist_ok=True)
    jar = Path(args.modmenu)
    if not jar.is_absolute():
        jar = ROOT / jar

    installed = p206.setup_mods(jar)
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
        extra_game=["--width", str(args.width), "--height", str(args.height)])
    say("JVMFLAG -Dmcbridge.listrender.debug=true")
    say(f"WINDOW requested={args.width}x{args.height}")
    say("MODMENU " + str(jar) + " sha256=" + hashlib.sha256(jar.read_bytes()).hexdigest()
        + " size=" + str(jar.stat().st_size))
    say("mods: " + ", ".join(installed))

    result: dict = {"modmenu_jar": str(jar),
                    "modmenu_sha256": hashlib.sha256(jar.read_bytes()).hexdigest(),
                    "modmenu_size": jar.stat().st_size,
                    "jvm_flags": ["-Dmcbridge.listrender.debug=true"],
                    "requested_window": [args.width, args.height],
                    "notches": args.notches,
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

            listw = last_of(list_states(text), "ModListWidget")
            if listw is None:
                say("no ModListWidget debug line")
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

            probe_list = p204.parse_rect(p204.read_text(client_log), "list")
            if probe_list is None:
                say("probe did not announce the list rectangle")
                return 1
            result["probe_list"] = probe_list

            on_game = False
            for attempt in range(1, 4):
                p204._move(ox + cw // 2, oy + ch // 2)
                time.sleep(0.6)
                cx, cy = p204._cursor_pos()
                under = p204._window_at(cx, cy)
                on_game = p204._root_window(under) == p204._root_window(hwnd)
                say(f"RAISE attempt={attempt} cursor=({cx},{cy}) underIsGame={on_game}")
                if on_game:
                    break
                p204._focus(hwnd)
                time.sleep(0.8)
            result["cursor_on_game"] = on_game
            if not on_game:
                say("cursor is not over the game window after 3 raises; input would go elsewhere")
                return 1

            # --- scan: which row actually needs scrolling? -------------------------------------
            item = listw["itemHeight"]
            lx, ly, lw, lh = probe_list["gui"]
            if args.rows:
                rows = [int(x) for x in re.split(r"[,\s]+", args.rows.strip()) if x]
            else:
                rows = [r for r in range(listw["count"])
                        if ly + r * item + item // 2 <= ly + lh]
            if args.row >= 0:
                rows = [args.row]
            say(f"SCAN rows={rows} listTop={ly} listHeight={lh} itemHeight={item}")

            scan = []
            for row in rows:
                gui_x = lx + lw // 2
                gui_y = ly + row * item + item // 2
                dev_x = ox + int(round(gui_x * scale))
                dev_y = oy + int(round(gui_y * scale))
                p204._click(dev_x, dev_y)
                time.sleep(0.9)
                text = p204.read_text(client_log)
                desc = last_of(scroll_states(text), "DescriptionListWidget")
                counts = [w["count"] for w in list_states(text)
                          if w["class"] == "DescriptionListWidget"]
                entry = {"row": row, "gui": [gui_x, gui_y], "device": [dev_x, dev_y],
                         "description_count": counts[-1] if counts else None,
                         "scroll": desc["scroll"] if desc else None,
                         "max": desc["max"] if desc else None,
                         "drawn": desc["drawn"] if desc else None,
                         "thumb": desc["thumb"] if desc else None}
                scan.append(entry)
                say(f"SCAN row={row} desc_count={entry['description_count']} "
                    f"max={entry['max']} drawn={entry['drawn']} thumb={entry['thumb']}")
            result["scan"] = scan

            usable = [e for e in scan if e["drawn"] and (e["max"] or 0) > 0]
            if not usable:
                say("NO_SCROLLABLE_ROW every scanned row reports max<=0; the scrollbar branch "
                    "cannot be exercised at this window size")
                (out / "result.json").write_text(
                    json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
                    newline="\n")
                return 1
            chosen = max(usable, key=lambda e: e["max"])
            say(f"CHOSEN row={chosen['row']} desc_count={chosen['description_count']} "
                f"max={chosen['max']} thumb={chosen['thumb']}")
            result["chosen"] = chosen

            # The scan ends on whatever row it clicked last, so the panel currently shows that mod.
            # Re-click the chosen row and prove the panel is scrollable again before wheeling;
            # otherwise the wheel arrives at an empty panel and measures nothing (first attempt).
            p204._click(chosen["device"][0], chosen["device"][1])
            time.sleep(1.0)
            reselected = last_of(scroll_states(p204.read_text(client_log)), "DescriptionListWidget")
            say(f"RESELECT row={chosen['row']} desc={reselected}")
            result["reselected"] = reselected
            if reselected is None or not reselected["drawn"]:
                say("RESELECT_FAILED the chosen row is not scrollable after a second click")
                (out / "result.json").write_text(
                    json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
                    newline="\n")
                return 1

            boxes = panel_boxes(p204.read_text(client_log))
            panel = boxes.get("DescriptionListWidget")
            if panel is None:
                say("the panel never announced its box")
                return 1
            result["panel"] = panel
            bx, by, bw, bh = panel["box"]
            p204._move(ox + int(round((bx + bw // 2) * scale)),
                       oy + int(round((by + bh // 2) * scale)))
            time.sleep(0.5)
            cx, cy = p204._cursor_pos()
            result["cursor_over_panel"] = (p204._root_window(p204._window_at(cx, cy))
                                          == p204._root_window(hwnd))
            say(f"MOVE panelCentre=({cx},{cy}) underIsGame={result['cursor_over_panel']}")

            p204._grab_window(str(out / "scroll-before.png"), pid)
            time.sleep(0.4)
            before_text = p204.read_text(client_log)
            result["before"] = {
                "desc": last_of(scroll_states(before_text), "DescriptionListWidget"),
                "mod": last_of(list_states(before_text), "ModListWidget"),
                "probe_scroll": last_float(before_text,
                                           r"P204_SCROLL_STATE tick=\d+ scroll=([\d.]+)"),
            }

            p204._wheel(-args.notches)
            time.sleep(1.4)
            p204._grab_window(str(out / "scroll-after.png"), pid)
            time.sleep(0.4)
            after_text = p204.read_text(client_log)
            result["after_panel_wheel"] = {
                "desc": last_of(scroll_states(after_text), "DescriptionListWidget"),
                "mod": last_of(list_states(after_text), "ModListWidget"),
                "probe_scroll": last_float(after_text,
                                           r"P204_SCROLL_STATE tick=\d+ scroll=([\d.]+)"),
            }
            say(f"WHEEL over=panel notches=-{args.notches} "
                f"desc={result['before']['desc']} -> {result['after_panel_wheel']['desc']}")
            say(f"WHEEL over=panel modListScroll={result['before']['mod']['scroll']} "
                f"-> {result['after_panel_wheel']['mod']['scroll']}")

            # --- the other direction: the same notches over the mod list ----------------------
            p204._move(ox + int(round((lx + lw // 2) * scale)),
                       oy + int(round((ly + lh // 2) * scale)))
            time.sleep(0.5)
            list_text_before = p204.read_text(client_log)
            p204._wheel(-args.notches)
            time.sleep(1.4)
            tail_text = p204.read_text(client_log)
            result["after_mod_wheel"] = {
                "desc": last_of(scroll_states(tail_text), "DescriptionListWidget"),
                "mod": last_of(list_states(tail_text), "ModListWidget"),
                "probe_scroll": last_float(tail_text,
                                           r"P204_SCROLL_STATE tick=\d+ scroll=([\d.]+)"),
                "before_mod": last_of(list_states(list_text_before), "ModListWidget"),
                "before_desc": last_of(scroll_states(list_text_before), "DescriptionListWidget"),
            }
            say(f"WHEEL over=list notches=-{args.notches} "
                f"modListScroll={result['after_mod_wheel']['before_mod']['scroll']} "
                f"-> {result['after_mod_wheel']['mod']['scroll']}")
            say(f"WHEEL over=list descScroll="
                f"{result['after_mod_wheel']['before_desc']['scroll']} "
                f"-> {result['after_mod_wheel']['desc']['scroll']}")

            # The probe's findList picks the EntryListWidget with the larger maxScroll, so its
            # target flips between the two lists as soon as a long description is selected. Record
            # that instead of pretending its numbers are always the mod list.
            probe_states = [
                {"scroll": float(m.group(1)), "max": int(m.group(2)), "entries": int(m.group(3))}
                for m in re.finditer(r"P204_SCROLL_STATE tick=\d+ scroll=([\d.]+) max=(-?\d+) "
                                     r"entries=(\d+)", tail_text)]
            result["probe_states"] = probe_states
            result["probe_state_targets"] = sorted({s["entries"] for s in probe_states})
            # Two different entry counts in one run means the probe reported one list and then the
            # other; one value means it stayed on a single widget (the p207 jar's own run, where the
            # panel is never scrollable, shows only the mod list).
            result["probe_latched_onto"] = ("switches between both lists"
                                            if len(result["probe_state_targets"]) > 1
                                            else "one list only")
            say(f"PROBE entries_seen={result['probe_state_targets']} -> "
                f"{result['probe_latched_onto']}")

            result["scroll_lines"] = [ln.split("STDOUT]: ", 1)[-1].strip()
                                      for ln in tail_text.splitlines() if "P207_SCROLL" in ln]
            result["panel_lines"] = [ln.split("STDOUT]: ", 1)[-1].strip()
                                     for ln in tail_text.splitlines() if "P207_PANEL" in ln]
            result["list_lines"] = [ln.split("STDOUT]: ", 1)[-1].strip()
                                    for ln in tail_text.splitlines()
                                    if "P205_LIST class=ModListWidget" in ln]
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
