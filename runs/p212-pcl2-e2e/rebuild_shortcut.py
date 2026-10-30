"""Rebuild the desktop PCL2 shortcut so it points at the launcher that actually exists (p212).

The shortcut on this desktop named the folder p137 used (`D:\\我的世界\\.minecraft\\涟漪专用启动器`),
which has been deleted; the launcher lives under `D:\\浏览器所下载文件\\…`. p211 made the detector say
so instead of silently falling back; this step fixes the shortcut itself, so the shortcut path of
the detector has something to find - the other half of the p211 change (a *valid* shortcut must
resolve, with no notes).

**Encoding, learned the hard way**: a path with Chinese characters cannot ride inside
`powershell -Command "..."` - the command line is decoded in the console codepage, so
`D:\\浏览器所下载文件\\…` arrived as `D:\\PCL2_2.12.8.2\\…` and the shortcut was written pointing at a
folder that does not exist. Everything here goes through a `.ps1` file written as UTF-8 **with BOM**
(PowerShell 5.1 reads that correctly) and results come back in a JSON file, not stdout.

The old shortcut's bytes are copied into the evidence directory before it is replaced, so the broken
state stays checkable while the desktop is left with one working shortcut and no `.bak` clutter.

Usage:
  python runs/p212-pcl2-e2e/rebuild_shortcut.py \
      --target "D:\\浏览器所下载文件\\我的世界PCL2启动器_2.12.8.2\\plain craft launcher 2.exe" \
      --out runs/p212-pcl2-e2e
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LNK_NAME = "Plain Craft Launcher 2.lnk"


def ps_quote(value: str) -> str:
    return "'" + str(value).replace("'", "''") + "'"


def run_ps(body: str, result: Path) -> dict:
    """Run a PowerShell body from a BOM'd .ps1, returning whatever it wrote as JSON."""
    script = (body + "\n[IO.File]::WriteAllText(" + ps_quote(str(result))
              + ", ($result | ConvertTo-Json -Depth 4), [Text.UTF8Encoding]::new($false))\n")
    ps1 = Path(tempfile.gettempdir()) / "mcbridge_pcl_shortcut.ps1"
    ps1.write_text(script, encoding="utf-8-sig")
    proc = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
                           "-File", str(ps1)],
                          capture_output=True, text=True, encoding="utf-8", errors="replace",
                          timeout=60)
    data: dict = {}
    if result.is_file():
        data = json.loads(result.read_text(encoding="utf-8-sig"))
        result.unlink()
    data["_rc"] = proc.returncode
    if proc.returncode != 0 and proc.stderr:
        data["_stderr"] = proc.stderr.strip()[:400]
    return data


def resolve(lnk: Path) -> dict:
    body = ("$s=(New-Object -ComObject WScript.Shell).CreateShortcut(" + ps_quote(str(lnk)) + ")\n"
            "$result=@{target=$s.TargetPath; working_dir=$s.WorkingDirectory; "
            "description=$s.Description; icon=$s.IconLocation}")
    return run_ps(body, Path(tempfile.gettempdir()) / "mcbridge_lnk_read.json")


def make(lnk: Path, target: Path) -> dict:
    body = ("$s=(New-Object -ComObject WScript.Shell).CreateShortcut(" + ps_quote(str(lnk)) + ")\n"
            "$s.TargetPath=" + ps_quote(str(target)) + "\n"
            "$s.WorkingDirectory=" + ps_quote(str(target.parent)) + "\n"
            "$s.Description='Plain Craft Launcher 2'\n"
            "$s.IconLocation=" + ps_quote(str(target) + ",0") + "\n"
            "$s.Save()\n"
            "$result=@{saved=(Test-Path -LiteralPath " + ps_quote(str(lnk)) + ")}")
    return run_ps(body, Path(tempfile.gettempdir()) / "mcbridge_lnk_write.json")


def sha(path: Path) -> str:
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", required=True, help="PCL2 的 exe（新快捷方式要指向它）")
    ap.add_argument("--lnk", default=None,
                    help="快捷方式路径，默认桌面上的 Plain Craft Launcher 2.lnk")
    ap.add_argument("--restore", default=None,
                    help="先用这份 .lnk 覆盖目标位置（重跑时把被写坏的快捷方式恢复成原始状态）")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    out = Path(args.out)
    if not out.is_absolute():
        out = ROOT / out
    out.mkdir(parents=True, exist_ok=True)
    lnk = Path(args.lnk) if args.lnk else Path(os.environ["USERPROFILE"]) / "Desktop" / LNK_NAME
    target = Path(args.target)
    info: dict = {"lnk": str(lnk), "target": str(target), "target_exists": target.is_file()}
    if not target.is_file():
        raise SystemExit(f"launcher exe not found: {target}")

    if args.restore:
        restore = Path(args.restore)
        if not restore.is_absolute():
            restore = ROOT / restore
        shutil.copy2(restore, lnk)
        info["restored_from"] = str(restore)

    if lnk.is_file():
        backup = out / "desktop-shortcut-before.lnk"
        shutil.copy2(lnk, backup)
        info["before"] = resolve(lnk)
        info["before"].update({"lnk_bytes": lnk.stat().st_size, "lnk_sha256": sha(backup)})
        info["backup"] = str(backup)

    info["create"] = make(lnk, target)
    info["after"] = resolve(lnk) if lnk.is_file() else {}
    if lnk.is_file():
        info["after"].update({"lnk_bytes": lnk.stat().st_size, "lnk_sha256": sha(lnk)})
    info["after"]["points_at_the_launcher"] = bool(
        info["after"].get("target") and Path(info["after"]["target"]).exists()
        and Path(info["after"]["target"]).resolve() == target.resolve())

    # Independent check through our own resolver: it reads the target via a base64 round trip, so
    # it does not share this script's encoding path.
    sys.path.insert(0, str(ROOT / "tools"))
    import from_source_install as fs

    info["detect_pcl_root"] = str(fs.detect_pcl_root() or "") or None
    info["pcl2_from_desktop"] = str(fs.pcl2_from_desktop() or "") or None
    (out / "shortcut.json").write_text(json.dumps(info, ensure_ascii=False, indent=2) + "\n",
                                       encoding="utf-8", newline="\n")
    print(json.dumps({k: info[k] for k in ("before", "create", "after", "detect_pcl_root",
                                           "pcl2_from_desktop")
                      if k in info}, ensure_ascii=False, indent=2))
    return 0 if info["after"]["points_at_the_launcher"] else 1


if __name__ == "__main__":
    sys.exit(main())
