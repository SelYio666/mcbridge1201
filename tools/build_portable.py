#!/usr/bin/env python3
"""Build a portable, self-contained launcher package for people who cannot use GitHub.

The package bundles the launcher sources plus an embeddable CPython runtime and the
optional `minecraft-launcher-lib` (BSD-2) with its pure-Python dependencies, so the
recipient only needs to double-click `run.bat`.

It never bundles Minecraft / mod jars: the game is still downloaded at first launch
from Mojang (with the BMCLAPI mirror as fallback), exactly like the source checkout.

Usage:
  python tools/build_portable.py                     # dist/mcbridge-launcher-portable.zip
  python tools/build_portable.py --no-python         # source-only zip (needs system Python)
  python tools/build_portable.py --python-zip work/portable-cache/python-embed.zip
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import os
import shutil
import sys
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PY_VERSION = "3.12.10"
PY_URLS = [
    f"https://www.python.org/ftp/python/{PY_VERSION}/python-{PY_VERSION}-embed-amd64.zip",
    f"https://registry.npmmirror.com/-/binary/python/{PY_VERSION}/python-{PY_VERSION}-embed-amd64.zip",
]
# vendored optional dependency (minecraft-launcher-lib needs requests and friends)
VENDOR = ["minecraft_launcher_lib", "requests", "certifi", "urllib3", "idna",
          "charset_normalizer", "typing_extensions.py"]

THIRD_PARTY = """# 第三方组件与许可证（便携包）

本便携包不含任何 Minecraft 游戏文件、模组 jar 或转换件；它们全部在运行时下载或由用户提供。

| 组件 | 版本/来源 | 许可证 |
|---|---|---|
| CPython 嵌入式运行时 | python.org `{pyver}` embed-amd64 | Python Software Foundation License |
| minecraft-launcher-lib | 可选依赖（安装 Forge / NeoForge 回退、Java 运行时、mrpack） | BSD-2-Clause |
| requests | minecraft-launcher-lib 依赖 | Apache-2.0 |
| certifi | requests 依赖（CA 证书） | MPL-2.0 |
| urllib3 | requests 依赖 | MIT |
| idna | requests 依赖 | BSD-3-Clause |
| charset-normalizer | requests 依赖 | MIT |
| typing_extensions | 依赖 | PSF-2.0 |

mcbridge1201 本体：MIT（见 LICENSE）。各组件原始许可证文本可在其官方仓库获取。
"""


def sha1(path: Path) -> str:
    h = hashlib.sha1()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fetch(urls: list[str], dest: Path) -> Path:
    if dest.exists() and dest.stat().st_size > 1_000_000:
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    last = None
    for url in urls:
        try:
            print("downloading", url)
            req = urllib.request.Request(url, headers={"User-Agent": "mcbridge-build"})
            with urllib.request.urlopen(req, timeout=120) as r, dest.open("wb") as f:
                shutil.copyfileobj(r, f, 1 << 20)
            print("  ->", dest, dest.stat().st_size, "bytes")
            return dest
        except Exception as exc:  # noqa: BLE001
            last = exc
            dest.unlink(missing_ok=True)
            print("  failed:", exc)
    raise RuntimeError(f"python embed download failed: {last}")


def package_dir_of(name: str) -> Path | None:
    module = name[:-3] if name.endswith(".py") else name
    spec = importlib.util.find_spec(module)
    if spec is None:
        return None
    if spec.submodule_search_locations:
        return Path(list(spec.submodule_search_locations)[0])
    if spec.origin and spec.origin.endswith(".py"):
        return Path(spec.origin)  # single-file module
    return None


def vendor_deps(site_packages: Path, licenses: Path) -> list[str]:
    copied = []
    site_packages.mkdir(parents=True, exist_ok=True)
    licenses.mkdir(parents=True, exist_ok=True)
    for name in VENDOR:
        src = package_dir_of(name)
        if src is None:
            print("  missing dependency, skipped:", name)
            continue
        if src.is_file():
            shutil.copy2(src, site_packages / src.name)
            dist_name = name[:-3] if name.endswith(".py") else name
        else:
            shutil.copytree(src, site_packages / src.name,
                            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
            dist_name = name
        # keep dist-info (metadata) and its license files so the package stays compliant
        metas = list(src.parent.glob(f"{dist_name.replace('_', '-')}*.dist-info"))
        metas += list(src.parent.glob(f"{dist_name}*.dist-info"))
        for meta in metas:
            shutil.copytree(meta, site_packages / meta.name, dirs_exist_ok=True)
            for lic in meta.rglob("*"):
                if lic.is_file() and lic.name.upper().startswith(("LICENSE", "COPYING", "NOTICE")):
                    shutil.copy2(lic, licenses / f"{meta.name}__{lic.name}")
        copied.append(name)
        print("  vendored", name, "->", (site_packages / src.name))
    return copied


def write_launchers(stage: Path, label: str) -> None:
    # an explicit bootstrap: the embeddable python's ._pth ignores PYTHONPATH
    (stage / "bootstrap.py").write_text(
        "import os\r\n"
        "import sys\r\n"
        "\r\n"
        "here = os.path.dirname(os.path.abspath(__file__))\r\n"
        "sys.path.insert(0, os.path.join(here, 'launcher'))\r\n"
        "import server\r\n"
        "\r\n"
        "if __name__ == '__main__':\r\n"
        "    server.main()\r\n",
        encoding="utf-8")
    (stage / "run.bat").write_text(
        "@echo off\r\n"
        "cd /d \"%~dp0\"\r\n"
        "set LAUNCHER_PORT=\r\n"
        "if exist \"%~dp0python\\python.exe\" (\r\n"
        "  \"%~dp0python\\python.exe\" \"%~dp0bootstrap.py\"\r\n"
        ") else (\r\n"
        "  echo [mcbridge] 没有内置 Python，改用系统 python...\r\n"
        "  python \"%~dp0bootstrap.py\"\r\n"
        ")\r\n"
        "pause\r\n",
        encoding="utf-8")
    (stage / "README-PORTABLE.txt").write_text(
        f"""mcbridge1201 便携启动器 {label}
=====================================

怎么用
------
1. 解压整个文件夹到任意位置（路径最好不要带空格/中文也可以，但越简单越好）；
2. 双击 run.bat，浏览器会自动打开 http://127.0.0.1:8765/ ；
3. 左上选版本（例如 1.21.1），选 Fabric，点“安装并启动”。

第一次运行需要联网下载游戏文件（client jar / libraries / assets）。
仓库和本包都不含任何游戏或模组 jar。国内网络下资源 CDN 超时会自动走
BMCLAPI 镜像；如果仍然很慢，换个时间或多等一会儿（已下载的文件会跳过）。

游戏装在哪
----------
默认是“我的文档”附近自动检测到的 .minecraft（界面上会显示具体路径）；
也可以在“高级设置 → 游戏目录”里改成任意文件夹。
mods / saves 都在游戏目录下：界面右上角有“打开 mods”“打开存档”。

想用 PCL / HMCL 启动
--------------------
把它们的“游戏目录”指到本启动器的游戏目录即可；注意版本隔离：
PCL 开隔离时读 versions/<id>/mods，本启动器读全局 mods/，详见 docs/guide.md。

常见问题
--------
- 双击没反应：先看窗口里有没有“没有内置 Python”，有的话装 Python 3.10+；
- 浏览器没弹出：手动打开 http://127.0.0.1:8765/ ；
- 端口被占用：设置环境变量 LAUNCHER_PORT=8766 后再运行 run.bat；
- 杀毒软件拦截：本包没有 exe 安装器，只有 python.exe（官方嵌入式运行时），可加信任。

许可证
------
mcbridge1201 本体 MIT；内置 Python 为 PSF 许可证；
minecraft-launcher-lib 为 BSD-2。详见 THIRD-PARTY-NOTICES.md。
""",
        encoding="utf-8")


def build(args) -> Path:
    label = args.label or "portable"
    dist = ROOT / "dist"
    dist.mkdir(exist_ok=True)
    stage = ROOT / "work" / "portable-stage" / f"mcbridge-launcher-{label}"
    if stage.exists():
        shutil.rmtree(stage)
    stage.mkdir(parents=True)

    # launcher sources (no config.json / __pycache__)
    shutil.copytree(ROOT / "launcher", stage / "launcher",
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "config.json"))
    (stage / "docs").mkdir()
    for name in ("guide.md", "launcher.md"):
        shutil.copy2(ROOT / "docs" / name, stage / "docs" / name)
    shutil.copy2(ROOT / "LICENSE", stage / "LICENSE")
    (stage / "THIRD-PARTY-NOTICES.md").write_text(
        THIRD_PARTY.format(pyver=PY_VERSION), encoding="utf-8")

    if not args.no_python:
        cache = ROOT / "work" / "portable-cache"
        if args.python_zip:
            py_zip = Path(args.python_zip)
        else:
            py_zip = fetch(PY_URLS, cache / f"python-{PY_VERSION}-embed-amd64.zip")
        py_dir = stage / "python"
        with zipfile.ZipFile(py_zip) as z:
            z.extractall(py_dir)
        print("python runtime:", sha1(py_zip)[:12], py_zip.stat().st_size, "bytes")
        pth = next(py_dir.glob("python*._pth"), None)
        if pth is None:
            raise RuntimeError("embeddable python has no ._pth file")
        lines = pth.read_text(encoding="utf-8").splitlines()
        extra = ["Lib\\site-packages"]
        for line in extra:
            if line not in lines:
                lines.append(line)
        pth.write_text("\n".join(lines) + "\n", encoding="utf-8")
        licenses = stage / "THIRD-PARTY-LICENSES"
        py_license = next((p for p in py_dir.iterdir() if p.name.upper() == "LICENSE.TXT"), None)
        if py_license:
            licenses.mkdir(exist_ok=True)
            shutil.copy2(py_license, licenses / "PYTHON-LICENSE.txt")
        vendor_deps(py_dir / "Lib" / "site-packages", licenses)

    write_launchers(stage, label)

    out = dist / f"mcbridge-launcher-{label}.zip"
    if out.exists():
        out.unlink()
    prefix = f"mcbridge-launcher-{label}"
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for path in sorted(stage.rglob("*")):
            if path.is_file():
                z.write(path, f"{prefix}/{path.relative_to(stage).as_posix()}")
    print("package:", out, out.stat().st_size, "bytes")
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", default="portable", help="suffix for dist/mcbridge-launcher-<label>.zip")
    ap.add_argument("--no-python", action="store_true", help="do not bundle Python (needs system Python)")
    ap.add_argument("--python-zip", default="", help="use a local embeddable python zip")
    args = ap.parse_args()
    out = build(args)
    print("done")
    return 0 if out.exists() else 1


if __name__ == "__main__":
    sys.exit(main())
