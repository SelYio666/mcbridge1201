"""Open the one-click PCL panel for real and record what it shows (p211).

The fix for a stale desktop shortcut only counts if the *panel* says what happened: the field still
holds a game directory, so a user cannot tell "detected from your shortcut" from "your shortcut is
broken, this is the fallback". This builds the panel, reads back the widget state, and grabs the
window with PrintWindow, so the note can be checked as rendered rather than as source text.

Read-only with respect to the launcher: the panel only loads the version manifest; no install is
started and no game folder is written.

Usage:
  python runs/p211-pcl2-detect/panel_smoke.py
"""
from __future__ import annotations

import json
import os
import sys
import time
import tkinter as tk
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUN = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "tools"))
import pcl_panel  # noqa: E402
from test_launcher_e2e import _grab_window  # noqa: E402


def main() -> int:
    info: dict = {}
    shot = RUN / "panel-smoke.png"
    try:
        root = tk.Tk()
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"error": f"no Tk display: {exc}"}, ensure_ascii=False))
        (RUN / "panel-smoke.json").write_text(
            json.dumps({"error": f"no Tk display: {exc}"}, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8", newline="\n")
        return 2
    root.geometry("640x520+80+80")
    panel = pcl_panel.Panel(root)
    root.update_idletasks()
    root.update()
    info["dir_field"] = panel.dir_var.get()
    info["note_label"] = panel.note_label.cget("text")
    info["note_visible"] = bool(panel.note_label.winfo_viewable())
    info["note_geometry"] = panel.note_label.winfo_width(), panel.note_label.winfo_height()
    info["title"] = root.title()
    # Give the manifest thread a few seconds: 103 release versions was the p195 smoke figure.
    deadline = time.time() + 8
    while time.time() < deadline and not panel._all:
        root.update()
        time.sleep(0.1)
    info["versions_loaded"] = len(panel._all)
    info["status"] = panel.status.cget("text")
    info["screenshot"] = None
    if _grab_window(str(shot), os.getpid()) and shot.is_file():
        info["screenshot"] = str(shot)
        info["screenshot_bytes"] = shot.stat().st_size
    root.destroy()
    (RUN / "panel-smoke.json").write_text(json.dumps(info, ensure_ascii=False, indent=2) + "\n",
                                         encoding="utf-8", newline="\n")
    print(json.dumps(info, ensure_ascii=False, indent=2))
    return 0 if info["note_visible"] and info["note_label"] else 1


if __name__ == "__main__":
    sys.exit(main())
