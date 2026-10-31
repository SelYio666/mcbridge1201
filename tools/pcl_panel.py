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

# Palette shared with launcher/web so both user-facing surfaces read as one product.
BG = "#101713"
CARD = "#182220"
BORDER = "#2c3a34"
FIELD = "#0e1512"
TEXT = "#e8f0ea"
MUTED = "#93a89b"
ACCENT = "#4ade80"
WARN = "#f0c15a"
ERROR = "#f08a8a"
LOG_BG = "#0c120f"
LOG_FG = "#cfe3d6"
SEL_BG = "#2c4a38"


class Panel:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        root.title("mcbridge · 一键安装到 PCL")
        root.geometry("720x640")
        root.minsize(640, 560)
        root.configure(bg=BG)

        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        base_font = ("Microsoft YaHei UI", 10)
        style.configure(".", font=base_font, background=BG, foreground=TEXT,
                        bordercolor=BORDER, darkcolor=BG, lightcolor=BG, troughcolor=BG)
        style.configure("Card.TFrame", background=CARD)
        style.configure("TLabel", background=BG, foreground=TEXT)
        style.configure("Card.TLabel", background=CARD, foreground=TEXT)
        style.configure("Muted.TLabel", background=BG, foreground=MUTED,
                        font=("Microsoft YaHei UI", 9))
        style.configure("Muted.Card.TLabel", background=CARD, foreground=MUTED,
                        font=("Microsoft YaHei UI", 9))
        style.configure("Warn.Card.TLabel", background=CARD, foreground=WARN,
                        font=("Microsoft YaHei UI", 9))
        style.configure("Title.TLabel", background=BG, foreground=TEXT,
                        font=("Microsoft YaHei UI", 16, "bold"))
        style.configure("Sub.TLabel", background=BG, foreground=MUTED)
        style.configure("Step.TLabel", background=CARD, foreground=ACCENT,
                        font=("Microsoft YaHei UI", 10, "bold"))
        style.configure("TEntry", fieldbackground=FIELD, foreground=TEXT,
                        insertcolor=TEXT, bordercolor=BORDER, padding=4)
        style.configure("TCombobox", fieldbackground=FIELD, foreground=TEXT,
                        background=CARD, bordercolor=BORDER, arrowcolor=TEXT, padding=3)
        style.map("TCombobox",
                  fieldbackground=[("readonly", FIELD)],
                  foreground=[("readonly", TEXT)],
                  selectbackground=[("readonly", FIELD)],
                  selectforeground=[("readonly", TEXT)])
        root.option_add("*TCombobox*Listbox*Background", FIELD)
        root.option_add("*TCombobox*Listbox*Foreground", TEXT)
        root.option_add("*TCombobox*Listbox*selectBackground", SEL_BG)
        root.option_add("*TCombobox*Listbox*selectForeground", TEXT)
        root.option_add("*TCombobox*Listbox*Font", base_font)
        style.configure("TCheckbutton", background=CARD, foreground=TEXT)
        style.map("TCheckbutton", background=[("active", CARD)],
                  foreground=[("disabled", MUTED)])
        style.configure("TButton", background=CARD, foreground=TEXT, padding=(14, 7),
                        bordercolor=BORDER)
        style.map("TButton",
                  background=[("active", "#24332c"), ("pressed", SEL_BG)],
                  foreground=[("disabled", MUTED)])
        style.configure("Accent.TButton", background="#22c55e", foreground="#07130c",
                        font=("Microsoft YaHei UI", 10, "bold"))
        style.map("Accent.TButton",
                  background=[("active", ACCENT), ("pressed", "#16a34a"),
                              ("disabled", "#24332c")],
                  foreground=[("disabled", MUTED)])
        style.configure("Status.TLabel", background=CARD, foreground=MUTED)
        style.configure("Busy.Status.TLabel", background=CARD, foreground=WARN)
        style.configure("Ok.Status.TLabel", background=CARD, foreground=ACCENT)
        style.configure("Error.Status.TLabel", background=CARD, foreground=ERROR)
        style.configure("Accent.Horizontal.TProgressbar", background=ACCENT,
                        troughcolor=FIELD, bordercolor=BORDER,
                        lightcolor=ACCENT, darkcolor=ACCENT)
        style.configure("Vertical.TScrollbar", background=CARD, troughcolor=BG,
                        bordercolor=BORDER, arrowcolor=TEXT)
        style.map("Vertical.TScrollbar", background=[("active", SEL_BG)])

        header = tk.Frame(root, bg=BG)
        header.pack(fill="x", padx=18, pady=(16, 2))
        ttk.Label(header, text="安装到 PCL", style="Title.TLabel").pack(anchor="w")
        ttk.Label(header, text="选一个 Minecraft 版本，装进 PCL 的游戏目录，装完即可在 PCL 里启动。",
                  style="Sub.TLabel").pack(anchor="w", pady=(2, 0))

        # ---- step 1: version ----
        v_card = self._card(root, "1 · 选择版本")
        row1 = ttk.Frame(v_card, style="Card.TFrame")
        row1.pack(fill="x")
        ttk.Label(row1, text="版本", style="Card.TLabel").pack(side="left")
        self.version_var = tk.StringVar()
        self.version_box = ttk.Combobox(row1, textvariable=self.version_var, width=30)
        self.version_box.pack(side="left", padx=(8, 10), fill="x", expand=True)
        self.version_box.bind("<KeyRelease>", lambda e: self._filter_versions())
        self.type_var = tk.StringVar(value="正式版")
        type_box = ttk.Combobox(row1, textvariable=self.type_var, width=8, state="readonly",
                                values=["正式版", "快照", "全部"])
        type_box.pack(side="left")
        type_box.bind("<<ComboboxSelected>>", lambda e: self._reload_versions())
        self.ver_hint = ttk.Label(v_card, text="正在加载版本清单…", style="Muted.Card.TLabel")
        self.ver_hint.pack(anchor="w", pady=(6, 0))

        # ---- step 2: game directory ----
        d_card = self._card(root, "2 · PCL 目录 / 游戏目录")
        row2 = ttk.Frame(d_card, style="Card.TFrame")
        row2.pack(fill="x")
        # Why the field holds what it holds: a stale desktop shortcut used to be dropped in
        # silence, leaving the %APPDATA%/.minecraft fallback looking like a real detection
        # (runs/p211-pcl2-detect/). The notes are shown next to the field instead of a log line
        # the user never opens.
        detect_notes: list[str] = []
        self.dir_var = tk.StringVar(value=str(fs.detect_pcl_root(detect_notes) or ""))
        dir_entry = ttk.Entry(row2, textvariable=self.dir_var)
        dir_entry.pack(side="left", fill="x", expand=True)
        ttk.Button(row2, text="浏览…", command=self._browse).pack(side="left", padx=(8, 0))
        self.note_label = ttk.Label(d_card, text="；".join(detect_notes),
                                    style="Warn.Card.TLabel", wraplength=620, justify="left")
        self.note_label.pack(anchor="w", pady=(6, 0))
        self.open_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(d_card, text="装完打开游戏目录", variable=self.open_var).pack(
            anchor="w", pady=(8, 0))

        # ---- step 3: install ----
        a_card = self._card(root, "3 · 安装")
        row3 = ttk.Frame(a_card, style="Card.TFrame")
        row3.pack(fill="x")
        self.install_btn = ttk.Button(row3, text="安装到 PCL", style="Accent.TButton",
                                      command=self._start)
        self.install_btn.pack(side="left")
        self.status = ttk.Label(row3, text="就绪", style="Status.TLabel")
        self.status.pack(side="left", padx=12)
        self.bar = ttk.Progressbar(a_card, mode="determinate",
                                   style="Accent.Horizontal.TProgressbar")
        self.bar.pack(fill="x", pady=(10, 0))

        # ---- log ----
        outer = tk.Frame(root, bg=CARD, highlightthickness=1, highlightbackground=BORDER, bd=0)
        outer.pack(fill="both", expand=True, padx=16, pady=(10, 0))
        ttk.Label(outer, text="安装日志", style="Step.TLabel").pack(anchor="w", padx=14,
                                                                    pady=(10, 6))
        log_wrap = ttk.Frame(outer, style="Card.TFrame", padding=(14, 0, 14, 12))
        log_wrap.pack(fill="both", expand=True)
        self.log = tk.Text(log_wrap, height=9, wrap="word", state="disabled",
                           bg=LOG_BG, fg=LOG_FG, insertbackground=TEXT,
                           selectbackground=SEL_BG, selectforeground=TEXT,
                           relief="flat", bd=0, padx=8, pady=6, font=("Consolas", 9))
        scroll = ttk.Scrollbar(log_wrap, orient="vertical", command=self.log.yview)
        self.log.configure(yscrollcommand=scroll.set)
        self.log.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        ttk.Label(root, text="仅写入所选版本文件 · 不动存档与其他版本",
                  style="Muted.TLabel").pack(anchor="w", padx=18, pady=(8, 10))

        self._all: list[dict] = []
        self._shown: list[dict] = []
        self._queue: queue.Queue = queue.Queue()
        self._busy = False
        threading.Thread(target=self._load_versions, daemon=True).start()
        self.root.after(100, self._drain)

    def _card(self, parent: tk.Misc, title: str) -> ttk.Frame:
        outer = tk.Frame(parent, bg=CARD, highlightthickness=1,
                         highlightbackground=BORDER, highlightcolor=BORDER, bd=0)
        outer.pack(fill="x", padx=16, pady=(10, 0))
        ttk.Label(outer, text=title, style="Step.TLabel").pack(anchor="w", padx=14,
                                                               pady=(10, 6))
        body = ttk.Frame(outer, style="Card.TFrame", padding=(14, 0, 14, 12))
        body.pack(fill="x")
        return body

    # ---------- versions ----------
    def _post(self, callback) -> None:
        """Schedule a UI callback, tolerating a window that was closed while a fetch ran.

        `root.after` raises RuntimeError ("main thread is not in main loop") once the Tk root is
        gone, and the manifest fetch is a background thread - closing the panel while it is in
        flight used to print a traceback from that thread (seen in runs/p212-pcl2-e2e). Losing a
        progress line is fine; a crash-on-exit is not.
        """
        try:
            self.root.after(0, callback)
        except (RuntimeError, tk.TclError):
            pass

    def _load_versions(self) -> None:
        try:
            versions = list(fs.manifest()["versions"])
        except Exception as exc:  # noqa: BLE001
            def fail() -> None:
                self._write(f"版本清单加载失败: {exc}\n")
                self.ver_hint.config(text=f"版本清单加载失败：{exc}",
                                     style="Error.Status.TLabel")
            self._post(fail)
            return
        self._all = versions
        self._post(self._reload_versions)

    def _kind(self) -> str:
        return {"正式版": "release", "快照": "snapshot", "全部": "all"}[self.type_var.get()]

    def _reload_versions(self) -> None:
        kind = self._kind()
        self._shown = [v for v in self._all if kind == "all" or v["type"] == kind][:400]
        self.version_box["values"] = [v["id"] for v in self._shown]
        if not self.version_var.get() and self._shown:
            latest = fs.manifest()["latest"]["release"]
            self.version_var.set(latest if kind in ("release", "all") else self._shown[0]["id"])
        self.ver_hint.config(
            text=f"共 {len(self._shown)} 个版本可选（{self.type_var.get()}）· 输入可筛选",
            style="Muted.Card.TLabel")
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
        self.status.config(text="准备中…", style="Busy.Status.TLabel")
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
                    self.status.config(text=f"{phase} {done}/{total} {msg}".strip(),
                                       style="Busy.Status.TLabel")
                    self.bar.config(maximum=max(total, 1), value=done)
                    if msg:
                        self._write(msg + "\n")
                elif item[0] == "done":
                    _, version, path = item
                    self._busy = False
                    self.install_btn.config(state="normal")
                    self.bar.config(value=self.bar["maximum"])
                    self.status.config(text="完成", style="Ok.Status.TLabel")
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
                    self.status.config(text="失败", style="Error.Status.TLabel")
                    self._write("错误：" + item[1] + "\n")
                    messagebox.showerror("失败", item[1])
        except queue.Empty:
            pass
        self._post(lambda: self.root.after(120, self._drain))


def main() -> None:
    root = tk.Tk()
    Panel(root)
    root.mainloop()


if __name__ == "__main__":
    main()
