#!/usr/bin/env python3
"""Small GUI panel for the one-click PCL installer.

    python tools/pcl_panel.py

Pick a version, confirm the PCL game folder, click install, watch progress.
"""
from __future__ import annotations

import queue
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))
import from_source_install as fs  # noqa: E402


class Panel:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        root.title("mcbridge · 一键安装到 PCL")
        root.geometry("640x520")
        root.minsize(560, 460)

        style = ttk.Style()
        try:
            style.theme_use("vista")
        except tk.TclError:
            pass

        top = ttk.Frame(root, padding=12)
        top.pack(fill="x")

        ttk.Label(top, text="版本").grid(row=0, column=0, sticky="w")
        self.version_var = tk.StringVar()
        self.version_box = ttk.Combobox(top, textvariable=self.version_var, width=28)
        self.version_box.grid(row=0, column=1, sticky="we", padx=6)
        self.version_box.bind("<KeyRelease>", lambda e: self._filter_versions())

        self.type_var = tk.StringVar(value="正式版")
        type_box = ttk.Combobox(top, textvariable=self.type_var, width=10, state="readonly",
                                values=["正式版", "快照", "全部"])
        type_box.grid(row=0, column=2, padx=4)
        type_box.bind("<<ComboboxSelected>>", lambda e: self._reload_versions())

        ttk.Label(top, text="PCL 目录 / 游戏目录").grid(row=1, column=0, sticky="w", pady=(10, 0))
        # Why the field holds what it holds: a stale desktop shortcut used to be dropped in
        # silence, leaving the %APPDATA%/.minecraft fallback looking like a real detection
        # (runs/p211-pcl2-detect/). The notes are shown next to the field instead of a log line
        # the user never opens.
        detect_notes: list[str] = []
        self.dir_var = tk.StringVar(value=str(fs.detect_pcl_root(detect_notes) or ""))
        dir_entry = ttk.Entry(top, textvariable=self.dir_var, width=44)
        dir_entry.grid(row=1, column=1, columnspan=2, sticky="we", padx=6, pady=(10, 0))
        ttk.Button(top, text="浏览…", command=self._browse).grid(row=1, column=3, pady=(10, 0))
        self.note_label = ttk.Label(top, text="；".join(detect_notes), foreground="#8a6d00",
                                    wraplength=520, justify="left")
        self.note_label.grid(row=3, column=0, columnspan=4, sticky="w", padx=12)

        self.open_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(top, text="装完打开游戏目录", variable=self.open_var).grid(
            row=2, column=1, sticky="w", padx=6, pady=(8, 0))

        actions = ttk.Frame(root, padding=(12, 4))
        actions.pack(fill="x")
        self.install_btn = ttk.Button(actions, text="安装到 PCL", command=self._start)
        self.install_btn.pack(side="left")
        self.status = ttk.Label(actions, text="就绪")
        self.status.pack(side="left", padx=10)

        self.bar = ttk.Progressbar(root, mode="determinate")
        self.bar.pack(fill="x", padx=12, pady=6)

        self.log = tk.Text(root, height=10, wrap="word", state="disabled")
        self.log.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        self._all: list[dict] = []
        self._shown: list[dict] = []
        self._queue: queue.Queue = queue.Queue()
        self._busy = False
        threading.Thread(target=self._load_versions, daemon=True).start()
        self.root.after(100, self._drain)

    # ---------- versions ----------
    def _load_versions(self) -> None:
        try:
            self._all = list(fs.manifest()["versions"])
            self.root.after(0, self._reload_versions)
        except Exception as exc:  # noqa: BLE001
            self.root.after(0, lambda: self._write(f"版本清单加载失败: {exc}\n"))

    def _kind(self) -> str:
        return {"正式版": "release", "快照": "snapshot", "全部": "all"}[self.type_var.get()]

    def _reload_versions(self) -> None:
        kind = self._kind()
        self._shown = [v for v in self._all if kind == "all" or v["type"] == kind][:400]
        self.version_box["values"] = [v["id"] for v in self._shown]
        if not self.version_var.get() and self._shown:
            latest = fs.manifest()["latest"]["release"]
            self.version_var.set(latest if kind in ("release", "all") else self._shown[0]["id"])
        self._write(f"已加载 {len(self._shown)} 个版本（{self.type_var.get()}）\n")

    def _filter_versions(self) -> None:
        text = self.version_var.get().lower()
        if not text:
            self._reload_versions()
            return
        vals = [v["id"] for v in self._shown if text in v["id"].lower()][:50]
        self.version_box["values"] = vals

    def _browse(self) -> None:
        picked = filedialog.askdirectory(title="选择 PCL 启动器目录或 .minecraft")
        if picked:
            self.dir_var.set(picked)

    def _resolve_root(self) -> Path | None:
        raw = self.dir_var.get().strip()
        if not raw:
            return None
        p = Path(raw)
        resolved = fs.pcl2_game_dir(p) if p.exists() else None
        return resolved or p

    # ---------- install ----------
    def _start(self) -> None:
        if self._busy:
            return
        root_dir = self._resolve_root()
        if root_dir is None:
            messagebox.showwarning("缺少目录", "请先选择 PCL 目录或游戏目录")
            return
        version = self.version_var.get().strip() or fs.manifest()["latest"]["release"]
        if not any(v["id"] == version for v in self._all):
            messagebox.showwarning("版本无效", f"清单里没有 {version}，请从下拉列表选择")
            return
        self._busy = True
        self.install_btn.config(state="disabled")
        self.status.config(text="准备中…")
        self._write(f"开始安装 {version} -> {root_dir}\n")
        threading.Thread(target=self._work, args=(version, root_dir), daemon=True).start()

    def _work(self, version: str, root_dir: Path) -> None:
        def progress(phase: str, done: int, total: int, msg: str) -> None:
            self._queue.put(("progress", phase, done, total, msg))

        try:
            rc = fs.install(version, root_dir, progress=progress)
        except Exception as exc:  # noqa: BLE001
            self._queue.put(("error", str(exc)))
            return
        if rc == 0:
            try:
                fs.write_launcher_profiles(root_dir, version)
            except Exception as exc:  # noqa: BLE001
                self._queue.put(("error", f"写 launcher_profiles 失败: {exc}"))
                return
            self._queue.put(("done", version, str(root_dir)))
        else:
            self._queue.put(("error", f"安装失败（退出码 {rc}），请看日志"))

    # ---------- ui helpers ----------
    def _write(self, text: str) -> None:
        self.log.config(state="normal")
        self.log.insert("end", text)
        self.log.see("end")
        self.log.config(state="disabled")

    def _drain(self) -> None:
        try:
            while True:
                item = self._queue.get_nowait()
                if item[0] == "progress":
                    _, phase, done, total, msg = item
                    self.status.config(text=f"{phase} {done}/{total} {msg}".strip())
                    self.bar.config(maximum=max(total, 1), value=done)
                    if msg:
                        self._write(msg + "\n")
                elif item[0] == "done":
                    _, version, path = item
                    self._busy = False
                    self.install_btn.config(state="normal")
                    self.bar.config(value=self.bar["maximum"])
                    self.status.config(text="完成")
                    self._write(f"完成：{version} 已写入 {path}\n")
                    messagebox.showinfo("完成", f"{version} 已装好。打开 PCL 刷新版本列表即可。")
                    if self.open_var.get():
                        try:
                            import os

                            os.startfile(path)  # type: ignore[attr-defined]
                        except Exception:  # noqa: BLE001
                            pass
                elif item[0] == "error":
                    self._busy = False
                    self.install_btn.config(state="normal")
                    self.status.config(text="失败")
                    self._write("错误：" + item[1] + "\n")
                    messagebox.showerror("失败", item[1])
        except queue.Empty:
            pass
        self.root.after(120, self._drain)


def main() -> None:
    root = tk.Tk()
    Panel(root)
    root.mainloop()


if __name__ == "__main__":
    main()
