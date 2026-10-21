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
        elif parts[1] <= 21 and not (parts[1] == 21 and len(parts) > 2 and parts[2] >= 6):
            # 1.20.5 - 1.21.5: Java 21 (delta); NeoForge 21.1 rejects Java 25
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


def _retrying_get(url, **kwargs):
    """requests.get with retries; Mojang endpoints drop TLS connections intermittently here."""
    import time

    import requests as _requests

    kwargs.setdefault("timeout", 25)
    last = None
    for attempt in range(5):
        try:
            return _requests.get(url, **kwargs)
        except Exception as exc:  # noqa: BLE001
            last = exc
            time.sleep(1.5 * (attempt + 1))
    raise last


def _install_network_shims() -> None:
    """Patch the library modules to use the retrying getter (module-local, not global)."""
    import requests as _requests

    class _RequestsShim:
        def get(self, *args, **kwargs):
            return _retrying_get(*args, **kwargs)

        def __getattr__(self, name):
            return getattr(_requests, name)

    try:
        from minecraft_launcher_lib import _helper as helper
        from minecraft_launcher_lib import runtime as rt

        shim = _RequestsShim()
        rt.requests = shim
        helper.requests = shim
    except Exception:  # noqa: BLE001 - library missing; callers will surface it
        pass


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


def _pack_dependencies(path: Path) -> dict:
    import json
    import zipfile

    with zipfile.ZipFile(path) as z:
        index = json.loads(z.read("modrinth.index.json"))
    return index.get("dependencies", {})


def install_mrpack(path: Path, root: Path, progress=None) -> dict:
    """Install a Modrinth .mrpack: dependencies through our verified installers, then files."""
    if not AVAILABLE:
        raise RuntimeError("minecraft-launcher-lib not installed")
    from minecraft_launcher_lib import mrpack as mll_mrpack

    import mclaunch

    root = Path(root)
    info = mll_mrpack.get_mrpack_information(str(path))
    deps = _pack_dependencies(path)
    mc = deps.get("minecraft") or info.get("minecraftVersion")
    if mc:
        progress and progress.set(message=f"mrpack {path.name}: vanilla {mc}")
        mclaunch.install_vanilla_launcher_profile(mc, root)
    if deps.get("fabric-loader"):
        progress and progress.set(message=f"mrpack {path.name}: fabric {deps['fabric-loader']}")
        mclaunch.install_fabric(mc, root, progress, deps["fabric-loader"])
    if deps.get("forge"):
        progress and progress.set(message=f"mrpack {path.name}: forge {deps['forge']}")
        install("forge", mc, root, deps["forge"], mclaunch.find_java(), progress)
    if deps.get("neoforge"):
        progress and progress.set(message=f"mrpack {path.name}: neoforge {deps['neoforge']}")
        install("neoforge", mc, root, deps["neoforge"], mclaunch.find_java(), progress)

    progress and progress.set(message=f"mrpack {path.name}: files/overrides")
    _install_network_shims()
    mll_mrpack.install_mrpack(str(path), str(root), callback=_callback(progress),
                              mrpack_install_options={"skipDependenciesInstall": True})
    try:
        launch = mll_mrpack.get_mrpack_launch_version(str(path))
    except Exception:  # noqa: BLE001
        launch = None
    return {"name": info.get("name"), "version": info.get("versionId"),
            "minecraft": mc, "launch": launch}


def jvm_runtimes() -> list[str]:
    if not AVAILABLE:
        return []
    from minecraft_launcher_lib import runtime as mll_runtime

    return list(mll_runtime.get_jvm_runtimes())


def installed_runtimes(root: Path) -> list[str]:
    if not AVAILABLE:
        return []
    from minecraft_launcher_lib import runtime as mll_runtime

    try:
        return list(mll_runtime.get_installed_jvm_runtimes(str(root)))
    except Exception:  # noqa: BLE001
        return []


def install_jvm(root: Path, jvm_id: str, progress=None) -> str:
    if not AVAILABLE:
        raise RuntimeError("minecraft-launcher-lib not installed")
    import time

    from minecraft_launcher_lib import runtime as mll_runtime

    _install_network_shims()
    last = None
    for attempt in range(3):
        try:
            progress and progress.set(message=f"java {jvm_id}" + (f" (retry {attempt})" if attempt else ""))
            mll_runtime.install_jvm_runtime(jvm_id, str(root), _callback(progress))
            return jvm_id
        except Exception as exc:  # noqa: BLE001 - the Mojang endpoints are flaky on this network
            last = exc
            time.sleep(3 * (attempt + 1))
    raise RuntimeError(f"java runtime install failed after retries: {last}")


def loader_versions(loader: str, mc: str) -> list[str]:
    """Available loader versions for one game version (newest first where the source allows)."""
    if not AVAILABLE:
        return []
    try:
        obj = mll_mod_loader.get_mod_loader(loader)
        return list(obj.get_loader_versions(mc, False))
    except Exception:  # noqa: BLE001 - network failures are reported by the endpoint
        raise


NEOFORGE_MAVEN = "https://maven.neoforged.net/releases/net/neoforged/neoforge"


def _urllib_json(url: str):
    import json
    import urllib.request

    req = urllib.request.Request(url, headers={"User-Agent": "mcbridge-launcher/0.1"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def neoforge_versions(mc: str) -> list[str]:
    prefix = ".".join(mc.split(".")[1:]) + "."
    data = _urllib_json(NEOFORGE_MAVEN + "/../neoforge") if False else _urllib_json(
        "https://maven.neoforged.net/api/maven/versions/releases/net/neoforged/neoforge")
    return [v for v in data.get("versions", []) if v.startswith(prefix)]


def _version_key(v: str):
    return [int(x) if x.isdigit() else x for x in v.replace("-", ".").split(".")]


def install_neoforge_direct(mc: str, root: Path, version: str | None = None,
                            java: str | None = None, progress=None) -> str:
    """Install NeoForge through its official installer using urllib (requests is blocked here)."""
    import subprocess

    import mclaunch

    root = Path(root)
    versions = neoforge_versions(mc)
    if version:
        if version not in versions:
            raise RuntimeError(f"neoforge {version} is not available for {mc}")
        ver = version
    elif versions:
        ver = sorted(versions, key=_version_key)[-1]
    else:
        raise RuntimeError(f"no neoforge build for {mc}")
    vid = f"neoforge-{ver}"
    if (root / "versions" / vid / f"{vid}.json").exists() and all(
            mclaunch.loader_artifacts(vid, root).values()):
        return vid
    progress and progress.set(message=f"neoforge installer {ver}")
    installer = root / "installers" / f"neoforge-{ver}-installer.jar"
    mclaunch.download_maven(f"{NEOFORGE_MAVEN}/{ver}/neoforge-{ver}-installer.jar", installer)
    mclaunch.prepare_installer_libraries(installer, root, progress)
    java = java or mclaunch.find_java()
    progress and progress.set(message="running neoforge installer")
    root = root.resolve()
    installer = installer.resolve()
    log_path = root / "installers" / f"neoforge-{ver}.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run([java, "-jar", str(installer), "--installClient", str(root)],
                          cwd=str(root), capture_output=True, text=True)
    log_path.write_text((proc.stdout or "") + (proc.stderr or ""), encoding="utf-8", errors="replace")
    missing = [name for name, present in mclaunch.loader_artifacts(vid, root).items() if not present]
    if proc.returncode != 0 or missing:
        detail = (proc.stdout or proc.stderr or "").strip().splitlines()[-1:] or [""]
        raise RuntimeError(
            f"neoforge installer incomplete (rc={proc.returncode}, missing: "
            f"{', '.join(missing) or 'profile json'}, {detail[0]}); see {log_path}")
    if (root / "versions" / vid / f"{vid}.json").exists():
        return vid
    found = sorted(p.name for p in (root / "versions").glob("neoforge-*"))
    if not found:
        raise RuntimeError("neoforge installer produced no version profile")
    return found[-1]


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
        import json as _json
        import re

        mc = None
        meta = Path(root) / "versions" / version_id / f"{version_id}.json"
        if meta.exists():
            try:
                mc = _json.loads(meta.read_text(encoding="utf-8")).get("inheritsFrom")
            except Exception:  # noqa: BLE001
                mc = None
        if not mc:
            m = re.search(r"(\d+\.\d+(?:\.\d+)?)", version_id)
            mc = m.group(1) if m else None
        java = pick_java(mc) if mc else None
    if java:
        options["executablePath"] = java
    return mll_command.get_minecraft_command(version_id, str(root), options)  # type: ignore[arg-type]
