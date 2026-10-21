"""Optional adapter around minecraft-launcher-lib (BSD-2-Clause, JakobDev).

The library covers Forge / NeoForge installers, Java runtimes and command assembly. We keep our own
downloader for the parts where a mirror is needed, and fall back to it when this import is missing.
"""
from __future__ import annotations

import hashlib
import uuid
from pathlib import Path

try:  # optional dependency
    import minecraft_launcher_lib as mll
    from minecraft_launcher_lib import command as mll_command
    from minecraft_launcher_lib import forge as mll_forge
    from minecraft_launcher_lib import mod_loader as mll_mod_loader

    AVAILABLE = True
    try:
        from importlib.metadata import version as _pkg_version

        VERSION = _pkg_version("minecraft-launcher-lib")
    except Exception:  # noqa: BLE001
        VERSION = getattr(mll, "__version__", "?")
except Exception:  # noqa: BLE001
    mll = None
    AVAILABLE = False
    VERSION = None

LOADERS = ("forge", "neoforge")


def pick_java(mc: str) -> str | None:
    """Pick an installed official runtime that matches the game's Java era."""
    import os
    import re

    local = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local")))
    rt = local / "Packages"
    runtimes = {}
    for p in rt.glob("Microsoft.4297127D64EC6_*/LocalCache/Local/runtime/*/windows-x64/*/bin/java.exe"):
        runtimes.setdefault(p.parent.parent.name, str(p))
    try:
        parts = [int(x) for x in re.findall(r"\d+", mc)[:3]]
    except ValueError:
        parts = [1, 21, 0]
    if parts and parts[0] == 1:
        if parts[1] <= 16:
            order = ["jre-legacy", "java-runtime-beta", "java-runtime-delta", "java-runtime-epsilon"]
        elif parts[1] <= 20 and not (parts[1] == 20 and len(parts) > 2 and parts[2] >= 5):
            order = ["java-runtime-delta", "java-runtime-gamma", "java-runtime-beta", "java-runtime-epsilon"]
        else:
            order = ["java-runtime-epsilon", "java-runtime-delta", "java-runtime-gamma"]
    else:
        order = ["java-runtime-epsilon", "java-runtime-delta"]
    for name in order:
        for key, value in runtimes.items():
            if key.startswith(name):
                return value
    return None


def offline_uuid(name: str) -> str:
    return str(uuid.UUID(bytes=hashlib.md5(("OfflinePlayer:" + name).encode()).digest(), version=3))


def _callback(progress):
    if progress is None:
        return None

    def set_status(text):
        progress.set(message=str(text)[:120])

    def set_max(n):
        progress.set(total=int(n))

    def set_progress(n):
        progress.set(done=int(n))

    return {"setStatus": set_status, "setMax": set_max, "setProgress": set_progress}


def loader_versions(loader: str, mc: str) -> list[str]:
    """Available loader versions for one game version (newest first where the source allows)."""
    if not AVAILABLE:
        return []
    try:
        obj = mll_mod_loader.get_mod_loader(loader)
        return list(obj.get_loader_versions(mc, False))
    except Exception:  # noqa: BLE001 - network failures are reported by the endpoint
        raise


def _profile_game_version(path: Path) -> str | None:
    try:
        import json as _json

        data = _json.loads(path.read_text(encoding="utf-8"))
        return data.get("inheritsFrom") or data.get("id")
    except Exception:  # noqa: BLE001
        return None


def installed(loader: str, mc: str, root: Path, loader_version: str | None = None) -> str | None:
    """Return the version id if this loader **for this game version** is already installed."""
    root = Path(root)
    if loader == "forge":
        cands = sorted((root / "versions").glob(f"{mc}-forge-*"))
    elif loader == "neoforge":
        cands = sorted((root / "versions").glob("neoforge-*"))
    else:
        return None
    for d in cands:
        meta = d / f"{d.name}.json"
        if not meta.exists():
            continue
        if _profile_game_version(meta) != mc:
            continue
        if loader_version and loader_version not in d.name:
            continue
        return d.name
    return None


def install(loader: str, mc: str, root: Path, version: str | None, java: str, progress=None) -> str:
    if not AVAILABLE:
        raise RuntimeError("minecraft-launcher-lib not installed (pip install minecraft-launcher-lib)")
    root = Path(root)
    existing = installed(loader, mc, root, version)
    if existing:
        return existing
    cb = _callback(progress)
    if loader == "forge":
        vid = version or mll_forge.find_forge_version(mc)
        if not vid:
            vid = f"{mc}-{mll_forge.list_forge_versions()[-1].split('-', 1)[1]}"
        mll_forge.install_forge_version(vid, root, cb, java)
        return mll_forge.forge_to_installed_version(vid)
    if loader == "neoforge":
        loader_obj = mll_mod_loader.get_mod_loader("neoforge")
        loader_ver = version
        if not loader_ver:
            vers = loader_obj.get_loader_versions(mc, True)
            if not vers:
                raise RuntimeError(f"no NeoForge build for {mc}")
            loader_ver = vers[-1]
        progress and progress.set(total=0, done=0)
        loader_obj.install(mc, str(root), cb, java, loader_ver)
        return loader_obj.get_installed_version(mc, loader_ver)
    raise RuntimeError("unsupported loader " + loader)


def command(version_id: str, root: Path, username: str, java: str | None = None) -> list[str]:
    if not AVAILABLE:
        raise RuntimeError("minecraft-launcher-lib not installed")
    options = {
        "username": username,
        "uuid": offline_uuid(username),
        "token": "0",
        "gameDirectory": str(root),
        "launcherName": "mcbridge-launcher",
        "launcherVersion": "0.1",
    }
    if not java:
        import re

        m = re.search(r"(\d+\.\d+(?:\.\d+)?)", version_id)
        java = pick_java(m.group(1)) if m else None
    if java:
        options["executablePath"] = java
    return mll_command.get_minecraft_command(version_id, str(root), options)  # type: ignore[arg-type]
