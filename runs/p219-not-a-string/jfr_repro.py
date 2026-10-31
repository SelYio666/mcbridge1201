#!/usr/bin/env python3
"""Reproduce a client world-join run under JFR, so a thrown exception can be traced.

Usage:
    python runs/p219-not-a-string/jfr_repro.py \
        --root work/launcher-e2e --version 1.20.4 \
        --world "C:\\...\\saves\\新的世界" --jfr D:\\tmp\\x.jfr

Requires the launcher's game root to already contain the version (libs/assets/jar).
Copy the world into <root>/saves/<name>, optionally clear player data, launch with
`--quickPlaySingleplayer <name>`, stop the recording with jcmd, then inspect:

    jfr print --events jdk.JavaExceptionThrow --stack-depth 30 x.jfr
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "launcher"))
import mclaunch  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True, help="game root holding the version")
    ap.add_argument("--version", required=True)
    ap.add_argument("--world", required=True, help="world directory to copy in")
    ap.add_argument("--name", default="p219-world")
    ap.add_argument("--jfr", default=r"D:\mcbridge-data\work\tmp\notastring.jfr")
    ap.add_argument("--username", default="SelYio")
    ap.add_argument("--uuid", default="00000000-0000-3006-998f-555b73d6dcef")
    ap.add_argument("--clear-player-data", action="store_true")
    ap.add_argument("--wait", type=int, default=60)
    args = ap.parse_args()

    root = Path(args.root).resolve()
    dst = root / "saves" / args.name
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(Path(args.world), dst)
    if args.clear_player_data:
        for sub in ("advancements", "stats", "playerdata"):
            d = dst / sub
            if d.is_dir():
                for f in d.iterdir():
                    f.unlink()

    jfr = Path(args.jfr)
    jfr.parent.mkdir(parents=True, exist_ok=True)
    jfr.unlink(missing_ok=True)
    cmd, log, _ = mclaunch.build_command(
        args.version, root, args.username, "2G",
        extra_jvm=[f"-XX:StartFlightRecording=filename={jfr},settings=profile,dumponexit=true"],
        extra_game=["--quickPlaySingleplayer", args.name],
    )
    for i, a in enumerate(cmd):
        if a == "--uuid" and i + 1 < len(cmd):
            cmd[i + 1] = args.uuid
        if a == "--accessToken" and i + 1 < len(cmd):
            cmd[i + 1] = args.uuid

    log.parent.mkdir(parents=True, exist_ok=True)
    out = open(log, "w", encoding="utf-8", errors="replace")
    out.write(" ".join(cmd) + "\n")
    out.flush()
    proc = subprocess.Popen(cmd, cwd=str(root), stdout=out, stderr=subprocess.STDOUT)
    print("pid", proc.pid, "log", log, flush=True)

    seen = False
    deadline = time.time() + args.wait
    while time.time() < deadline:
        time.sleep(2)
        text = log.read_text(encoding="utf-8", errors="replace") if log.exists() else ""
        if "Not a string" in text:
            seen = True
            print("MARKER: Not a string seen", flush=True)
            break
        if "logged in" in text or "joined the game" in text:
            time.sleep(8)
            break
        if proc.poll() is not None:
            break

    if proc.poll() is None:
        jcmd = Path(sys.executable).parent / "jcmd.exe"  # fallback; override if needed
        jcmd = jcmd if jcmd.exists() else Path(r"C:\Users\27682\Documents\新建文件夹\.toolchain\jdk\bin\jcmd.exe")
        r = subprocess.run([str(jcmd), str(proc.pid), "JFR.stop", f"filename={jfr}"],
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        print("jfr stop rc", r.returncode, r.stdout.strip()[:80], flush=True)
        time.sleep(2)
        proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()
    print("seen =", seen, "jfr bytes =", jfr.stat().st_size if jfr.exists() else 0, flush=True)
    return 0 if seen else 1


if __name__ == "__main__":
    sys.exit(main())
