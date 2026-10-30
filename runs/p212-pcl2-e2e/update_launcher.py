"""Update the PCL2 launcher in place from a downloaded snapshot zip (p212).

The zip `PCL 快照版 2.99.0.0.zip` holds a single file, `Plain Craft Launcher 2.exe`. "In place" means
into the folder that already has `PCL\\Setup.ini` and `.minecraft`, so the launcher's own settings and
game folder survive the update; the old exe is kept next to it as
`Plain Craft Launcher 2.exe.<old version>.bak` because a snapshot build can regress and this must be
undoable without re-downloading.

Every step is recorded: the old exe (path/size/sha256/version), the zip member's sha256, the new
exe's sha256, and the shortcut target after the swap. The sha256 of the extracted exe has to equal
the zip member's, and the version reported by the file has to match the zip's name - otherwise the
update is not "done", it is "extracted something".

Actions go through a `.ps1` written with a UTF-8 BOM: a Chinese path inside `powershell -Command
"..."` arrived mangled once already (runs/p212-pcl2-e2e/README.md).

Usage:
  python runs/p212-pcl2-e2e/update_launcher.py \
      --zip "D:\\浏览器所下载文件\\PCL 快照版 2.99.0.0.zip" \
      --launcher-dir "D:\\浏览器所下载文件\\我的世界PCL2启动器_2.12.8.2" \
      --out runs/p212-pcl2-e2e
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MEMBER = "Plain Craft Launcher 2.exe"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def file_version(exe: Path) -> str | None:
    """FileVersion via a BOM'd .ps1 (a Chinese path inside -Command gets mangled)."""
    result = Path(tempfile.gettempdir()) / "mcbridge_exe_version.json"
    body = ("$v=(Get-Item -LiteralPath '" + str(exe).replace("'", "''") + "').VersionInfo\n"
            "$result=@{file_version=$v.FileVersion; product_version=$v.ProductVersion; "
            "description=$v.FileDescription; size=(Get-Item -LiteralPath '"
            + str(exe).replace("'", "''") + "').Length}\n"
            "[IO.File]::WriteAllText('" + str(result) + "', ($result | ConvertTo-Json), "
            "[Text.UTF8Encoding]::new($false))\n")
    ps1 = Path(tempfile.gettempdir()) / "mcbridge_exe_version.ps1"
    ps1.write_text(body, encoding="utf-8-sig")
    subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(ps1)],
                   capture_output=True, timeout=60)
    if result.is_file():
        data = json.loads(result.read_text(encoding="utf-8-sig"))
        result.unlink()
        return data
    return None


def shortcut() -> dict:
    sys.path.insert(0, str(ROOT / "tools"))
    import from_source_install as fs

    return {"pcl2_from_desktop": str(fs.pcl2_from_desktop() or "") or None,
            "detect_pcl_root": str(fs.detect_pcl_root() or "") or None}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--zip", required=True)
    ap.add_argument("--launcher-dir", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--expect-version", default=None,
                    help="期望的新版本号（默认从 zip 文件名里解析）")
    args = ap.parse_args()

    out = Path(args.out)
    if not out.is_absolute():
        out = ROOT / out
    out.mkdir(parents=True, exist_ok=True)
    zip_path = Path(args.zip)
    ldir = Path(args.launcher_dir)
    exe = ldir / MEMBER
    expect = args.expect_version or "".join(ch for ch in zip_path.stem if ch.isdigit() or ch == ".")
    expect = expect.strip(".")

    info: dict = {"zip": str(zip_path), "zip_bytes": zip_path.stat().st_size,
                  "zip_sha256": sha256(zip_path), "launcher_dir": str(ldir),
                  "exe": str(exe), "expect_version": expect}
    if not (ldir / "PCL" / "Setup.ini").is_file():
        raise SystemExit(f"not a PCL2 folder (no PCL/Setup.ini): {ldir}")

    with zipfile.ZipFile(zip_path) as z:
        if MEMBER not in z.namelist():
            raise SystemExit(f"{zip_path.name} does not contain {MEMBER}: {z.namelist()}")
        member_bytes = z.read(MEMBER)
    info["member"] = {"name": MEMBER, "bytes": len(member_bytes),
                      "sha256": hashlib.sha256(member_bytes).hexdigest()}

    info["before"] = {"exe": str(exe), "exists": exe.is_file(),
                      "sha256": sha256(exe) if exe.is_file() else None,
                      "info": file_version(exe) if exe.is_file() else None}
    if exe.is_file():
        backup = exe.with_name(f"{MEMBER}.{info['before']['info']['file_version']}.bak")
        shutil.copy2(exe, backup)
        info["backup"] = {"path": str(backup), "bytes": backup.stat().st_size,
                          "sha256": sha256(backup)}

    # Extract exactly that member over the old exe (zipfile, not Expand-Archive: one file, known name).
    out_exe = ldir / MEMBER
    out_exe.write_bytes(member_bytes)
    info["after"] = {"exe": str(out_exe), "exists": out_exe.is_file(),
                     "sha256": sha256(out_exe) if out_exe.is_file() else None,
                     "info": file_version(out_exe) if out_exe.is_file() else None}
    info["extracted_matches_zip"] = info["after"]["sha256"] == info["member"]["sha256"]
    info["version_matches_name"] = bool(
        info["after"]["info"] and expect and info["after"]["info"]["file_version"].startswith(expect))
    info["setup_ini_still_there"] = (ldir / "PCL" / "Setup.ini").is_file()
    ini = ldir / "PCL" / "Setup.ini"
    info["launch_folder_select"] = next(
        (ln.split(":", 1)[1].strip() for ln in ini.read_text(encoding="utf-8", errors="replace")
         .splitlines() if ln.startswith("LaunchFolderSelect:")), None)
    info.update(shortcut())

    (out / "launcher-update.json").write_text(json.dumps(info, ensure_ascii=False, indent=2) + "\n",
                                              encoding="utf-8", newline="\n")
    print(json.dumps({k: info[k] for k in ("before", "member", "after", "extracted_matches_zip",
                                           "version_matches_name", "launch_folder_select",
                                           "pcl2_from_desktop") if k in info},
                     ensure_ascii=False, indent=2))
    return 0 if info["extracted_matches_zip"] and info["version_matches_name"] else 1


if __name__ == "__main__":
    sys.exit(main())
