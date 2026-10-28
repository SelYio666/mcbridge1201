#!/usr/bin/env python3
"""Launch the Fabric 1.21.1 client for the p200 scene and capture log + screenshot + memory.

This is the p175 runner plus one thing p175 could not answer: how much memory three 4096x4096 atlas
images actually cost. The working set of the client process is sampled every 500 ms and pinned to
the probe's markers, so the report can quote a measured before/after instead of arithmetic.

Note: the working set is the whole process (heap + native images + driver-side allocations that the
driver keeps in the process). It is NOT a VRAM measurement; VRAM is not observable here without
vendor tooling, and the report says so.
"""
from __future__ import annotations

import argparse
import ctypes
import json
import shutil
import subprocess
import sys
import time
from ctypes import wintypes
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUN = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "launcher"))
sys.path.insert(0, str(ROOT / "tools"))
import mclaunch  # noqa: E402
from test_launcher_e2e import _grab_window  # noqa: E402

VERSION = "fabric-loader-0.19.5-1.21.1"
INSTANCE = ROOT / "work" / "launcher-e2e"
USERNAME = "IFMapUser"
WORLD = "ColdWorldAtlasLayout"
SAMPLE_MS = 100

MARKERS = [
    "[p200-probe] pre-atlas",
    "[p200-probe] allocated",
    "[p200-probe] atlas0 image",
    "[p200-probe] atlas1 image",
    "[p200-probe] atlas2 image",
    "[p200-probe] tile-sweep",
    "[p200-probe] layout-states replaced",
    "[p200-probe] layout-drawn",
]

BAD_MARKERS = [
    "ClassCastException",
    "InvalidInjectionException",
    "Mixin apply for mod immediatelyfast failed",
    "Mixin transformation of net.minecraft.class_330 failed",
    "java.lang.NoClassDefFoundError",
    "java.lang.NoSuchMethodError",
    "Game crashed",
    "Uncaught exception in thread",
    "Unreported exception thrown!",
    "Image is not allocated",
    "OutOfMemoryError",
]


class ProcessMemoryCounters(ctypes.Structure):
    _fields_ = [
        ("cb", wintypes.DWORD),
        ("PageFaultCount", wintypes.DWORD),
        ("PeakWorkingSetSize", ctypes.c_size_t),
        ("WorkingSetSize", ctypes.c_size_t),
        ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
        ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
        ("PagefileUsage", ctypes.c_size_t),
        ("PeakPagefileUsage", ctypes.c_size_t),
    ]


class MemorySampler:
    """Working-set sampler for a Windows child process (no psutil in this environment)."""

    def __init__(self, pid: int) -> None:
        self.pid = pid
        self.handle = None
        self.ok = False
        if sys.platform == "win32":
            kernel32 = ctypes.windll.kernel32
            psapi = ctypes.windll.psapi
            PROCESS_QUERY_INFORMATION = 0x0400
            PROCESS_VM_READ = 0x0010
            self.handle = kernel32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ,
                                               False, pid)
            self.ok = bool(self.handle)
            self._psapi = psapi

    def sample(self) -> dict | None:
        if not self.ok:
            return None
        counters = ProcessMemoryCounters()
        counters.cb = ctypes.sizeof(ProcessMemoryCounters)
        if not self._psapi.GetProcessMemoryInfo(self.handle, ctypes.byref(counters),
                                                counters.cb):
            return None
        return {
            "working_set_mb": round(counters.WorkingSetSize / 1048576, 1),
            "peak_working_set_mb": round(counters.PeakWorkingSetSize / 1048576, 1),
            "pagefile_mb": round(counters.PagefileUsage / 1048576, 1),
        }

    def close(self) -> None:
        if self.ok:
            ctypes.windll.kernel32.CloseHandle(self.handle)


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except FileNotFoundError:
        return ""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--timeout", type=int, default=300)
    ap.add_argument("--settle", type=int, default=4, help="seconds after the last marker")
    ap.add_argument("--username", default=USERNAME)
    ap.add_argument("--world", default=WORLD)
    ap.add_argument("--run-dir", default=str(RUN))
    ap.add_argument("--require-log", action="append", default=[],
                    help="wait for this log substring before the screenshot (repeatable)")
    ap.add_argument("--exit-log", default="map-atlas clear atlases=3")
    args = ap.parse_args()

    # Refuse to run a stale probe: two earlier runs silently used the previous jar because the
    # world build had failed, and the logs looked like a result instead of a build problem.
    built = ROOT / "work" / "tmp" / "p200-probe.jar"
    installed = INSTANCE / "mods" / "p200-probe.jar"
    if (not built.exists() or not installed.exists()
            or installed.stat().st_mtime < built.stat().st_mtime - 1):
        print("stale probe: run build_probe.py then make_world.py first", file=sys.stderr)
        return 2

    out_dir = Path(args.run_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    required = args.require_log or ["[p200-probe] tile-sweep", "[p200-probe] layout-drawn"]
    log = out_dir / "client.log"
    log.write_text("", encoding="utf-8")
    cmd, _, _ = mclaunch.build_command(
        VERSION, INSTANCE, args.username, "2G",
        extra_game=["--quickPlaySingleplayer", args.world, "--width", "1280", "--height", "720"])
    with log.open("w", encoding="utf-8", errors="replace") as out:
        out.write(" ".join(cmd) + "\n")
        out.flush()
        proc = subprocess.Popen(cmd, cwd=str(INSTANCE), stdout=out, stderr=subprocess.STDOUT)

    sampler = MemorySampler(proc.pid)
    joined = False
    seen: dict[str, dict] = {}
    samples: list[dict] = []
    errors: list[str] = []
    shots: list[str] = []
    shot_done = False
    exit_seen = False
    required_ok = False
    started = time.time()
    deadline = started + args.timeout
    try:
        while time.time() < deadline:
            text = read_text(log)
            joined = joined or f"{args.username} joined the game" in text
            now = round(time.time() - started, 1)
            mem = sampler.sample()
            if mem:
                samples.append({"t": now, **mem})
            for marker in MARKERS:
                if marker in text and marker not in seen:
                    seen[marker] = {"t": now, **(sampler.sample() or {})}
            required_ok = all(m in text for m in required)
            errors = [line for line in text.splitlines()
                      if any(marker in line for marker in BAD_MARKERS)]
            if proc.poll() is not None:
                break
            if joined and required_ok:
                time.sleep(args.settle)
                shot_done = bool(_grab_window(str(out_dir / "world.png"), proc.pid))
                if args.exit_log:
                    exit_deadline = time.time() + 90
                    while time.time() < exit_deadline:
                        if args.exit_log in read_text(log):
                            exit_seen = True
                            break
                        if proc.poll() is not None:
                            break
                        time.sleep(0.5)
                break
            time.sleep(SAMPLE_MS / 1000.0)
    finally:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=15)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=10)
        sampler.close()

    time.sleep(1)
    text = read_text(log)
    latest = INSTANCE / "logs" / "latest.log"
    if latest.exists():
        shutil.copy2(latest, out_dir / "latest.log")
    crash = None
    for candidate in sorted((INSTANCE / "crash-reports").glob("crash-*-client.txt"), reverse=True):
        if candidate.stat().st_mtime >= log.stat().st_mtime - 5:
            crash = str(candidate)
            break
    crash_lines = [line for line in text.splitlines()
                   if "Mixin apply for mod immediatelyfast failed" in line
                   or "Image is not allocated" in line
                   or "OutOfMemoryError" in line]
    ok = bool(joined and required_ok and shot_done and exit_seen and not crash
              and not errors and not crash_lines)
    pre = seen.get("[p200-probe] pre-atlas", {}).get("working_set_mb")
    post = seen.get("[p200-probe] allocated", {}).get("working_set_mb")
    peak = max((s["working_set_mb"] for s in samples), default=None)
    result = {
        "joined": joined,
        "required_logs": required,
        "required_ok": required_ok,
        "markers": seen,
        "memory_samples": samples,
        "memory_summary": {
            "samples": len(samples),
            "pre_atlas_working_set_mb": pre,
            "post_atlas_working_set_mb": post,
            "atlas_step_delta_mb": None if pre is None or post is None else round(post - pre, 1),
            "peak_working_set_mb": peak,
            "at_markers": {k: v.get("working_set_mb") for k, v in seen.items()},
            "note": "working set of the client process; not a VRAM measurement",
        },
        "exit_seen": exit_seen,
        "exit_log": args.exit_log,
        "errors": errors,
        "crash": crash,
        "exit_code": proc.returncode,
        "world": args.world,
        "screenshot": "world.png" if shot_done else None,
        "state_screenshots": shots,
    }
    (out_dir / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                                         encoding="utf-8")
    print(json.dumps({k: result[k] for k in
                      ("joined", "required_ok", "exit_seen", "errors", "crash", "exit_code",
                       "screenshot")}, ensure_ascii=False, indent=2))
    print(json.dumps(result["memory_summary"], ensure_ascii=False, indent=2))
    if not ok:
        print("FAILED: see client.log / latest.log", file=sys.stderr)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
