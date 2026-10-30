"""Where is PCL2, and does our detection actually see it? (p211)

The p195/p137 evidence said "本机 PCL2 路径不存在", so 任务 6 was recorded as blocked for lack of a
PCL2 install. It turned out the launcher is on this machine, under a different folder than the one
the old desktop shortcut names: `D:\\浏览器所下载文件\\我的世界PCL2启动器_2.12.8.2\\plain craft
launcher 2.exe` (FileVersion **2.13.1.1**, the version p137 tested), whose `PCL/Setup.ini` points at
`C:\\Users\\27682\\AppData\\Roaming\\.minecraft`.

This probe writes down the environment as facts (paths, versions, hashes, the launcher's own
config) and what our detector makes of it, so the conclusion can be re-checked without re-deriving
it. It is read-only: it opens no launcher, installs nothing, and writes only under `--out`.

`--exe` is required because the launcher's location is a user-machine fact: pass the path on this
machine, a different one elsewhere, and the JSON records which was used.

Usage:
  python runs/p211-pcl2-detect/probe_pcl.py --out runs/p211-pcl2-detect/before
  python runs/p211-pcl2-detect/probe_pcl.py --out runs/p211-pcl2-detect/after
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "tools"
sys.path.insert(0, str(TOOLS))
import from_source_install as fs  # noqa: E402


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def file_version(exe: Path) -> str | None:
    """FileVersion of a Windows exe, read without pywin32."""
    if os.name != "nt":
        return None
    ps = f"(Get-Item -LiteralPath '{exe}').VersionInfo.FileVersion"
    try:
        out = subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                             capture_output=True, text=True, encoding="utf-8",
                             errors="replace", timeout=30).stdout.strip()
    except Exception:  # noqa: BLE001
        return None
    return out or None


def shortcut_target(lnk: Path) -> str | None:
    """Target path of a .lnk, resolved through WScript.Shell (no pywin32 needed)."""
    if os.name != "nt":
        return None
    ps = ("$p=(New-Object -ComObject WScript.Shell).CreateShortcut('"
          + str(lnk) + "').TargetPath; [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($p))")
    try:
        raw = subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                             capture_output=True, text=True, encoding="ascii",
                             errors="ignore", timeout=30).stdout.strip()
    except Exception:  # noqa: BLE001
        return None
    import base64
    try:
        return base64.b64decode(raw).decode("utf-8", "replace").strip() or None
    except Exception:  # noqa: BLE001
        return None


def setup_ini_line(exe: Path) -> str | None:
    ini = exe.parent / "PCL" / "Setup.ini"
    if not ini.is_file():
        return None
    for line in ini.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith("LaunchFolderSelect:"):
            return line.split(":", 1)[1].strip()
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--exe", required=True, help="PCL2 的 exe（或它的安装目录）")
    ap.add_argument("--out", required=True)
    ap.add_argument("--label", default="")
    args = ap.parse_args()

    out = Path(args.out)
    if not out.is_absolute():
        out = ROOT / out
    out.mkdir(parents=True, exist_ok=True)

    given = Path(args.exe)
    exe = given.parent / given.name if given.suffix.lower() == ".exe" else \
        given / "plain craft launcher 2.exe"
    # The folder name and the exe version disagree on this machine; both are recorded rather than
    # reconciled, because "2.12.8.2" is only the download folder's name.
    info: dict = {
        "label": args.label,
        "given": str(given),
        "exe": str(exe) if exe.is_file() else None,
        "exe_exists": exe.is_file(),
        "exe_bytes": exe.stat().st_size if exe.is_file() else None,
        "exe_sha256": sha256(exe) if exe.is_file() else None,
        "exe_file_version": file_version(exe) if exe.is_file() else None,
        "launcher_dir_name": exe.parent.name if exe.is_file() else None,
        # The launcher's own configuration: this is the folder PCL2 actually uses, and it is read
        # by the installer's --pcl2 path too.
        "setup_ini": str(exe.parent / "PCL" / "Setup.ini")
        if (exe.parent / "PCL" / "Setup.ini").is_file() else None,
        "launch_folder_select": setup_ini_line(exe) if exe.is_file() else None,
        "portable_minecraft_exists": (exe.parent / ".minecraft").is_dir() if exe.is_file() else None,
        "pcl2_game_dir": None,
        "game_dir_exists": None,
        "game_dir_versions": [],
        "launcher_profiles_exists": None,
    }

    if exe.is_file():
        game = fs.pcl2_game_dir(exe)
        info["pcl2_game_dir"] = str(game) if game else None
        if game:
            info["game_dir_exists"] = game.is_dir()
            versions = game / "versions"
            if versions.is_dir():
                info["game_dir_versions"] = sorted(p.name for p in versions.iterdir() if p.is_dir())
            info["launcher_profiles_exists"] = (game / "launcher_profiles.json").is_file()

    # The desktop shortcut is the other auto-detection input, and on this machine it is stale:
    # it still names the folder p137 used, which no longer exists.
    desktop = Path(os.environ.get("USERPROFILE", "")) / "Desktop"
    shortcuts = []
    for lnk in sorted(desktop.glob("*.lnk")) if desktop.is_dir() else []:
        name = lnk.name.lower()
        if "pcl" not in name and "plain craft" not in name:
            continue
        target = shortcut_target(lnk)
        shortcuts.append({"lnk": str(lnk), "target": target,
                          "target_exists": bool(target) and Path(target).exists()})
    info["desktop_shortcuts"] = shortcuts

    # What the shipped detector does with all of that. `notes` exists only after the fix; its
    # absence in `before/` is the finding, so it is recorded instead of assumed.
    notes: list[str] = []
    detect = fs.detect_pcl_root(notes) if _accepts_notes(fs.detect_pcl_root) else fs.detect_pcl_root()
    scan = getattr(fs, "pcl2_shortcut_scan", None)
    info["pcl2_from_desktop"] = str(fs.pcl2_from_desktop() or "") or None
    info["detect_pcl_root"] = str(detect) if detect else None
    info["detector_accepts_notes"] = _accepts_notes(fs.detect_pcl_root)
    info["shortcut_scan_exists"] = scan is not None
    info["notes"] = notes
    if scan is not None:
        scanned, scan_notes = scan()
        info["shortcut_scan_game_dir"] = str(scanned) if scanned else None
        info["shortcut_scan_notes"] = scan_notes

    (out / "probe.json").write_text(json.dumps(info, ensure_ascii=False, indent=2) + "\n",
                                   encoding="utf-8", newline="\n")
    lines = [f"{k} = {v}" for k, v in info.items()]
    (out / "probe.log").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(lines))
    return 0 if info["exe_exists"] else 1


def _accepts_notes(func) -> bool:
    import inspect

    try:
        return "notes" in inspect.signature(func).parameters
    except (TypeError, ValueError):
        return False


if __name__ == "__main__":
    sys.exit(main())
