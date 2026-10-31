"""Capture the real Tk PCL panel without starting an installation."""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import tkinter as tk
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import pcl_panel  # noqa: E402
from test_launcher_e2e import _grab_window  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    parser.add_argument("--geometry", default="720x600+80+80")
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    root = tk.Tk()
    panel = pcl_panel.Panel(root)
    root.geometry(args.geometry)
    result: dict = {}
    deadline = time.time() + 12

    def capture() -> None:
        if (not panel._all or not panel.version_var.get()) and time.time() < deadline:
            root.after(100, capture)
            return
        root.update_idletasks()
        ok = _grab_window(str(args.output), os.getpid())
        result.update({
            "screenshot": str(args.output),
            "captured": bool(ok and args.output.is_file()),
            "geometry": root.geometry(),
            "versions_loaded": len(panel._all),
            "selected_version": panel.version_var.get(),
            "status": panel.status.cget("text"),
            "install_button_enabled": str(panel.install_btn["state"]) != "disabled",
        })
        root.destroy()

    root.after(100, capture)
    root.mainloop()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("captured") and result.get("install_button_enabled") else 1


if __name__ == "__main__":
    raise SystemExit(main())
