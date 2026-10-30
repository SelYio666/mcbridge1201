"""Click 安装到 PCL in the real panel and record what it does to the real game folder (p212).

This is the missing half of 任务 6: the p195 smoke opened the panel, the p211 probe proved where
PCL2 and its game folder are and that the shortcut is now valid - but nobody had ever pressed the
button against a real launcher installation.

What is real here: the Tk window, the panel's own `install_btn.invoke()` (the same command a click
runs), `from_source_install.install()`, the official Mojang downloads, and the write into
`C:\\Users\\27682\\AppData\\Roaming\\.minecraft`.

What is stubbed, and only this: `messagebox.showinfo/showerror/showwarning`. A modal dialog would
block a machine with nobody at the keyboard, so they are recorded (`dialogs`) instead of shown;
`open_var` is turned off so the finished panel does not pop an Explorer window. Everything else -
threading, progress queue, launcher_profiles write - is the shipped code.

Usage:
  python runs/p212-pcl2-e2e/panel_install.py --version 1.20.4 --out runs/p212-pcl2-e2e
"""
from __future__ import annotations

import argparse
import json
import time
import tkinter as tk
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUN = Path(__file__).resolve().parent
import sys

sys.path.insert(0, str(ROOT / "tools"))
import pcl_panel  # noqa: E402
import from_source_install as fs  # noqa: E402
from test_launcher_e2e import _grab_window  # noqa: E402


def snapshot(game: Path, version: str) -> dict:
    vdir = game / "versions" / version
    profiles = {}
    lpj = game / "launcher_profiles.json"
    if lpj.is_file():
        try:
            profiles = json.loads(lpj.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            profiles = {}
    versions = []
    vroot = game / "versions"
    if vroot.is_dir():
        versions = sorted(p.name for p in vroot.iterdir() if p.is_dir())
    files = {}
    if vdir.is_dir():
        for p in sorted(vdir.iterdir()):
            if p.is_file():
                files[p.name] = p.stat().st_size
    return {
        "game": str(game),
        "versions": versions,
        "version_dir": str(vdir) if vdir.is_dir() else None,
        "version_files": files,
        "profile_keys": sorted((profiles.get("profiles") or {}).keys()),
        "profile_for_version": (profiles.get("profiles") or {}).get(f"mcbridge-{version}"),
        "selected_profile": profiles.get("selectedProfile"),
        "checked_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", default="1.20.4")
    ap.add_argument("--out", required=True)
    ap.add_argument("--timeout", type=int, default=2700)
    args = ap.parse_args()

    out = Path(args.out)
    if not out.is_absolute():
        out = ROOT / out
    out.mkdir(parents=True, exist_ok=True)

    dialogs: list[dict] = []

    def record(kind: str):
        def _f(title, message, **_kw):
            dialogs.append({"kind": kind, "title": str(title), "message": str(message)})
            return "ok"

        return _f

    pcl_panel.messagebox.showinfo = record("info")
    pcl_panel.messagebox.showerror = record("error")
    pcl_panel.messagebox.showwarning = record("warning")

    root = tk.Tk()
    root.geometry("640x520+80+80")
    panel = pcl_panel.Panel(root)
    root.update()

    info: dict = {"version": args.version, "dialogs": dialogs}
    # The panel validates the version against the manifest, so wait for the list.
    deadline = time.time() + 90
    while time.time() < deadline and not panel._all:
        root.update()
        time.sleep(0.1)
    info["manifest_versions"] = len(panel._all)
    if not any(v["id"] == args.version for v in panel._all):
        info["error"] = f"version not in the manifest: {args.version}"
        (out / "install.json").write_text(json.dumps(info, ensure_ascii=False, indent=2) + "\n",
                                          encoding="utf-8", newline="\n")
        return 2

    panel.open_var.set(False)  # no Explorer window when it finishes
    panel.version_var.set(args.version)
    root.update()
    game = Path(panel.dir_var.get())
    info["panel_dir_field"] = str(game)
    info["note_label"] = panel.note_label.cget("text")
    info["before"] = snapshot(game, args.version)

    shot_before = out / "panel-before-install.png"
    if _grab_window(str(shot_before), __import__("os").getpid()):
        info["screenshot_before"] = str(shot_before)

    started = time.time()
    panel.install_btn.invoke()  # the button's own command, i.e. what a click runs
    info["busy_after_invoke"] = panel._busy
    progress: list[str] = []
    last = None
    deadline = time.time() + args.timeout
    while time.time() < deadline:
        root.update()
        status = panel.status.cget("text")
        if status != last:
            progress.append(status)
            last = status
        if not panel._busy and status in ("完成", "失败"):
            break
        time.sleep(0.1)
    info["seconds"] = round(time.time() - started, 1)
    info["progress"] = progress
    info["status"] = panel.status.cget("text")
    info["log_tail"] = panel.log.get("1.0", "end").strip().splitlines()[-25:]
    info["after"] = snapshot(game, args.version)
    info["dialogs"] = dialogs
    info["install_ok"] = info["status"] == "完成" and not [d for d in dialogs if d["kind"] == "error"]

    shot_after = out / "panel-after-install.png"
    if _grab_window(str(shot_after), __import__("os").getpid()):
        info["screenshot_after"] = str(shot_after)
    # Let the progress queue and the manifest thread land before the window goes away: the panel
    # used to print a traceback from that thread when the root was destroyed underneath it.
    settle = time.time() + 2
    while time.time() < settle:
        root.update()
        time.sleep(0.05)
    try:
        root.destroy()
    except Exception:  # noqa: BLE001
        pass

    (out / "install.json").write_text(json.dumps(info, ensure_ascii=False, indent=2) + "\n",
                                      encoding="utf-8", newline="\n")
    print(json.dumps({k: info[k] for k in ("status", "seconds", "install_ok", "progress",
                                           "after")}, ensure_ascii=False, indent=2))
    return 0 if info["install_ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
