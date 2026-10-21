#!/usr/bin/env python3
"""mcbridge launcher core: install Minecraft versions from official sources and launch offline.

Design rules:
- never bundle game files; everything is downloaded from Mojang / Fabric / Forge / NeoForge meta;
- offline mode only: singleplayer and LAN, no Mojang authentication;
- one game root (like .minecraft), shared libraries/assets, per-version folders.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
import uuid
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

UA = {"User-Agent": "mcbridge-launcher/0.1 (offline, local)"}
MANIFEST_URL = "https://piston-meta.mojang.com/mc/game/version_manifest_v2.json"
FABRIC_META = "https://meta.fabricmc.net/v2"
FORGE_PROMOS = "https://files.minecraftforge.net/net/minecraftforge/forge/promotions_slim.json"
NEOFORGE_VERSIONS = "https://maven.neoforged.net/api/maven/versions/releases/net/neoforged/neoforge"
ASSET_BASE = "https://resources.download.minecraft.net"
JAVA_FALLBACK = r"C:\Program Files\Java\jdk-21\bin\java.exe"


class Progress:
    def __init__(self):
        self.phase = "idle"
        self.total = 0
        self.done = 0
        self.message = ""
        self.error = None
        self.lock = threading.Lock()

    def set(self, phase=None, message=None, total=None, done=None, error=None):
        with self.lock:
            if phase is not None:
                self.phase = phase
            if message is not None:
                self.message = message
            if total is not None:
                self.total = total
            if done is not None:
                self.done = done
            if error is not None:
                self.error = error

    def inc(self):
        with self.lock:
            self.done += 1

    def snapshot(self):
        with self.lock:
            return {"phase": self.phase, "total": self.total, "done": self.done,
                    "message": self.message, "error": self.error}


def http_json(url: str, retries: int = 3):
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read())
        except Exception as exc:  # noqa: BLE001
            last = exc
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"GET {url} failed: {last}")


def sha1_of(path: Path) -> str:
    h = hashlib.sha1()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


MIRRORS = [
    ("https://resources.download.minecraft.net/", "https://bmclapi2.bangbang93.com/assets/"),
    ("http://resources.download.minecraft.net/", "https://bmclapi2.bangbang93.com/assets/"),
    ("https://libraries.minecraft.net/", "https://bmclapi2.bangbang93.com/maven/"),
    ("https://piston-data.mojang.com/", "https://bmclapi2.bangbang93.com/"),
]


def mirror_urls(url: str) -> list[str]:
    """Official URL first; fall back to the BMCLAPI mirror when it fails."""
    mirrors = []
    for official, mirror in MIRRORS:
        if url.startswith(official):
            mirrors.append(mirror + url[len(official):])
    return [url] + mirrors


def download(url: str, dest: Path, sha1: str | None = None, retries: int = 4) -> None:
    if dest.exists() and (sha1 is None or sha1_of(dest) == sha1):
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    last = None
    for candidate in mirror_urls(url):
        for attempt in range(retries):
            try:
                req = urllib.request.Request(candidate, headers=UA)
                with urllib.request.urlopen(req, timeout=30) as r, tmp.open("wb") as f:
                    shutil.copyfileobj(r, f, 1 << 20)
                if sha1 and sha1_of(tmp) != sha1:
                    tmp.unlink(missing_ok=True)
                    raise RuntimeError("sha1 mismatch")
                tmp.replace(dest)
                return
            except Exception as exc:  # noqa: BLE001
                last = exc
                tmp.unlink(missing_ok=True)
                time.sleep(2.0 * (attempt + 1))
    raise RuntimeError(f"download {url} failed: {last}")


def eval_rules(rules, features=None) -> bool:
    """Evaluate Mojang rule lists for Windows with an empty feature set."""
    if not rules:
        return True
    features = features or {}
    ok = False
    for rule in rules:
        applies = True
        os_name = (rule.get("os") or {}).get("name")
        if os_name and os_name != "windows":
            applies = False
        feats = rule.get("features")
        if feats:
            for key, want in feats.items():
                if bool(features.get(key, False)) != bool(want):
                    applies = False
        if applies:
            ok = rule.get("action") == "allow"
    return ok


def allowed_win(lib: dict) -> bool:
    return eval_rules(lib.get("rules"))


def version_manifest():
    data = http_json(MANIFEST_URL)
    return data["versions"], data["latest"]


def find_version(version_id: str):
    versions, _ = version_manifest()
    for v in versions:
        if v["id"] == version_id:
            return v
    raise RuntimeError(f"unknown version {version_id}")



def ensure_profile(version_id: str, root: Path, name: str | None = None) -> None:
    """Write a launcher_profiles.json entry so other launchers list this version."""
    import json as _json
    import time as _time

    root = Path(root)
    path = root / "launcher_profiles.json"
    data = {}
    if path.exists():
        try:
            data = _json.loads(path.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            data = {}
    profiles = data.setdefault("profiles", {})
    if version_id not in profiles:
        now = _time.strftime("%Y-%m-%dT%H:%M:%S.000Z", _time.gmtime())
        profiles[version_id] = {
            "name": name or version_id,
            "type": "custom",
            "created": now,
            "lastUsed": now,
            "icon": "Furnace",
            "lastVersionId": version_id,
            "gameDir": str(root),
        }
        data.setdefault("settings", {})
        data.setdefault("version", 3)
        path.write_text(_json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def install_vanilla(mc: str, root: Path, progress: Progress | None = None) -> str:
    root = Path(root)
    v = find_version(mc)
    progress and progress.set(phase="download", message=f"version json {mc}")
    meta = http_json(v["url"])
    vdir = root / "versions" / mc
    vdir.mkdir(parents=True, exist_ok=True)
    (vdir / f"{mc}.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")

    # client jar
    jar = meta.get("downloads", {}).get("client")
    if jar:
        progress and progress.set(message="client jar")
        download(jar["url"], vdir / f"{mc}.jar", jar.get("sha1"))

    # libraries + natives
    libs = [lib for lib in meta.get("libraries", []) if allowed_win(lib)]
    natives_dir = vdir / "natives"
    natives_dir.mkdir(parents=True, exist_ok=True)

    def get_lib(lib):
        dl = lib.get("downloads", {})
        art = dl.get("artifact")
        if art:
            download(art["url"], root / "libraries" / art["path"], art.get("sha1"))
        native_key = (lib.get("natives") or {}).get("windows")
        if native_key:
            cls = dl.get("classifiers", {}).get(native_key.replace("${arch}", "64"))
            if cls:
                jar_path = root / "libraries" / cls["path"]
                download(cls["url"], jar_path, cls.get("sha1"))
                with zipfile.ZipFile(jar_path) as z:
                    for name in z.namelist():
                        if name.endswith((".dll", ".so", ".dylib")):
                            target = natives_dir / Path(name).name
                            if not target.exists():
                                target.write_bytes(z.read(name))

    progress and progress.set(total=len(libs), done=0, message="libraries")
    with ThreadPoolExecutor(max_workers=8) as pool:
        futs = [pool.submit(get_lib, lib) for lib in libs]
        for f in as_completed(futs):
            f.result()
            progress and progress.inc()

    # asset index + objects
    idx = meta.get("assetIndex")
    if idx:
        idx_path = root / "assets" / "indexes" / f"{idx['id']}.json"
        download(idx["url"], idx_path, idx.get("sha1"))
        index = json.loads(idx_path.read_text(encoding="utf-8"))
        objects = list(index.get("objects", {}).items())
        progress and progress.set(total=len(objects), done=0, message="assets")
        pending = []

        def get_obj(item):
            name, obj = item
            dest = root / "assets" / "objects" / obj["hash"][:2] / obj["hash"]
            if dest.exists() and dest.stat().st_size == obj.get("size", -1):
                return
            download(f"{ASSET_BASE}/{obj['hash'][:2]}/{obj['hash']}", dest, obj["hash"])

        with ThreadPoolExecutor(max_workers=24) as pool:
            futs = [pool.submit(get_obj, it) for it in objects]
            for f in as_completed(futs):
                f.result()
                progress and progress.inc()
    ensure_natives(mc, root)
    ensure_profile(mc, root)
    return mc


def install_fabric(mc: str, root: Path, progress: Progress | None = None,
                   loader_version: str | None = None) -> str:
    root = Path(root)
    loaders = http_json(f"{FABRIC_META}/versions/loader/{mc}")
    if loader_version:
        match = [x for x in loaders if x.get("loader", {}).get("version") == loader_version]
        if not match:
            raise RuntimeError(f"fabric loader {loader_version} is not available for {mc}")
        loader = match[0]
    else:
        loader = next((x for x in loaders if x.get("loader", {}).get("stable")), loaders[0])
    loader_ver = loader["loader"]["version"]
    vid = f"fabric-loader-{loader_ver}-{mc}"
    progress and progress.set(phase="download", message=f"fabric {vid}")
    profile = http_json(f"{FABRIC_META}/versions/loader/{mc}/{loader_ver}/profile/json")
    profile["id"] = vid
    vdir = root / "versions" / vid
    vdir.mkdir(parents=True, exist_ok=True)
    (vdir / f"{vid}.json").write_text(json.dumps(profile, indent=2), encoding="utf-8")
    libs = profile.get("libraries", [])
    progress and progress.set(total=len(libs), done=0, message="fabric libraries")

    def get_lib(lib):
        name = lib["name"]
        parts = name.split(":")
        group, artifact, ver = parts[0], parts[1], parts[2]
        classifier = parts[3] if len(parts) > 3 else None
        rel = f"{group.replace('.', '/')}/{artifact}/{ver}/{artifact}-{ver}" + (
            f"-{classifier}" if classifier else "") + ".jar"
        base = (lib.get("url") or "https://maven.fabricmc.net/").rstrip("/") + "/"
        download(base + rel, root / "libraries" / rel)

    with ThreadPoolExecutor(max_workers=8) as pool:
        futs = [pool.submit(get_lib, lib) for lib in libs]
        for f in as_completed(futs):
            f.result()
            progress and progress.inc()
    ensure_profile(vid, root)
    return vid


def ensure_natives(mc: str, root: Path) -> None:
    """Extract the Windows natives of an installed version into versions/<mc>/natives."""
    root = Path(root)
    meta_path = root / "versions" / mc / f"{mc}.json"
    if not meta_path.exists():
        return
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    natives_dir = root / "versions" / mc / "natives"
    natives_dir.mkdir(parents=True, exist_ok=True)
    jars = []
    for lib in meta.get("libraries", []):
        if not allowed_win(lib):
            continue
        dl = lib.get("downloads", {})
        key = (lib.get("natives") or {}).get("windows")
        if key:
            cls = dl.get("classifiers", {}).get(key.replace("${arch}", "64"))
            if cls:
                jars.append((cls["path"], cls["url"], cls.get("sha1")))
            continue
        name = lib.get("name", "")
        parts = name.split(":")
        if len(parts) >= 4 and "natives-windows" in parts[3]:
            art = dl.get("artifact")
            if art:
                jars.append((art["path"], art["url"], art.get("sha1")))
    for rel, url, sha1 in jars:
        jar = root / "libraries" / rel
        if not jar.exists():
            download(url, jar, sha1)
        with zipfile.ZipFile(jar) as z:
            for name in z.namelist():
                if name.endswith((".dll", ".so", ".dylib")):
                    target = natives_dir / Path(name).name
                    if not target.exists():
                        target.write_bytes(z.read(name))


def install_vanilla_launcher_profile(mc: str, root: Path) -> None:
    """Ensure the vanilla version folder exists (needed before fabric inherits it)."""
    if not (Path(root) / "versions" / mc / f"{mc}.json").exists():
        install_vanilla(mc, root)
    ensure_natives(mc, root)


def _run_installer(jar: Path, root: Path, log_path: Path) -> int:
    java = find_java()
    with log_path.open("w", encoding="utf-8", errors="replace") as log:
        log.write(f"$ {java} -jar {jar.name} --installClient {root}\n")
        log.flush()
        proc = subprocess.run([java, "-jar", str(jar), "--installClient", str(root)],
                              cwd=str(root), stdout=log, stderr=subprocess.STDOUT)
    return proc.returncode


def install_forge(mc: str, root: Path, progress: Progress | None = None, version: str | None = None) -> str:
    root = Path(root)
    promos = http_json(FORGE_PROMOS)["promos"]
    version = version or promos.get(f"{mc}-recommended") or promos.get(f"{mc}-latest")
    if not version:
        raise RuntimeError(f"no forge promotion for {mc}")
    forge_ver = f"{mc}-{version}"
    vid = f"{mc}-forge-{version}"
    vdir = root / "versions" / vid
    if (vdir / f"{vid}.json").exists():
        return vid
    progress and progress.set(phase="download", message=f"forge installer {forge_ver}")
    installer = root / "installers" / f"forge-{forge_ver}-installer.jar"
    url = f"https://maven.minecraftforge.net/net/minecraftforge/forge/{forge_ver}/forge-{forge_ver}-installer.jar"
    download(url, installer)
    progress and progress.set(message="running forge installer")
    rc = _run_installer(installer, root, root / "installers" / f"forge-{forge_ver}.log")
    if rc != 0 or not (vdir / f"{vid}.json").exists():
        found = sorted((root / "versions").glob(f"{mc}-forge-*"))
        if found:
            return found[-1].name
        raise RuntimeError(f"forge installer failed rc={rc}")
    return vid


def install_neoforge(mc: str, root: Path, progress: Progress | None = None, version: str | None = None) -> str:
    root = Path(root)
    data = http_json(NEOFORGE_VERSIONS)
    all_versions = data.get("versions", [])
    prefix = mc.split("-")[0]  # 1.21.1 -> 21.1
    major = ".".join(mc.split(".")[:2])  # 1.21
    cands = [v for v in all_versions if v.startswith(major + ".") or v.startswith(prefix)]
    if not cands:
        raise RuntimeError(f"no neoforge build matched {mc}")
    version = version or cands[-1]
    vid = f"neoforge-{version}"
    vdir = root / "versions" / vid
    if (vdir / f"{vid}.json").exists():
        return vid
    progress and progress.set(phase="download", message=f"neoforge installer {version}")
    installer = root / "installers" / f"neoforge-{version}-installer.jar"
    url = f"https://maven.neoforged.net/releases/net/neoforged/neoforge/{version}/neoforge-{version}-installer.jar"
    download(url, installer)
    progress and progress.set(message="running neoforge installer")
    rc = _run_installer(installer, root, root / "installers" / f"neoforge-{version}.log")
    if rc != 0 and not (vdir / f"{vid}.json").exists():
        found = sorted((root / "versions").glob("neoforge-*"))
        if found:
            return found[-1].name
        raise RuntimeError(f"neoforge installer failed rc={rc}")
    return vid if (vdir / f"{vid}.json").exists() else sorted((root / "versions").glob("neoforge-*"))[-1].name



def verify_install(version_id: str, root: Path) -> dict:
    """Check an installed version: json, client jar, libraries, natives, assets."""
    root = Path(root)
    vdir = root / "versions" / version_id
    report = {"version": version_id, "root": str(root), "ok": True, "items": {}}

    meta_path = vdir / f"{version_id}.json"
    report["items"]["version_json"] = meta_path.exists()
    if not meta_path.exists():
        report["ok"] = False
        return report
    data = json.loads(meta_path.read_text(encoding="utf-8"))
    base_id = data.get("inheritsFrom") or version_id
    base_dir = root / "versions" / base_id
    base_data = data if base_id == version_id else json.loads(
        (base_dir / f"{base_id}.json").read_text(encoding="utf-8"))

    jar = base_dir / f"{base_id}.jar"
    report["items"]["client_jar"] = {
        "ok": jar.exists(),
        "path": str(jar),
        "size": jar.stat().st_size if jar.exists() else 0,
    }
    if not jar.exists():
        report["ok"] = False

    libs = []
    lib_missing = []
    all_libs = list(data.get("libraries", []))
    if base_id != version_id:
        all_libs += list(base_data.get("libraries", []))
    for lib in all_libs:
        if not allowed_win(lib):
            continue
        art = lib.get("downloads", {}).get("artifact")
        if not art:
            continue
        libs.append(art["path"])
        if not (root / "libraries" / art["path"]).exists():
            lib_missing.append(art["path"])
    report["items"]["libraries"] = {"total": len(libs), "missing": len(lib_missing),
                                    "missing_sample": lib_missing[:5]}
    if lib_missing:
        report["ok"] = False

    natives_dir = base_dir / "natives"
    dlls = sorted(p.name for p in natives_dir.glob("*.dll")) if natives_dir.exists() else []
    report["items"]["natives"] = {"dir": str(natives_dir), "dll": len(dlls), "sample": dlls[:4]}

    idx = base_data.get("assetIndex") or {}
    idx_path = root / "assets" / "indexes" / f"{idx.get('id', 'legacy')}.json"
    report["items"]["asset_index"] = {"ok": idx_path.exists(), "path": str(idx_path)}
    if idx_path.exists():
        index = json.loads(idx_path.read_text(encoding="utf-8"))
        total = 0
        missing = 0
        for _name, obj in index.get("objects", {}).items():
            total += 1
            dest = root / "assets" / "objects" / obj["hash"][:2] / obj["hash"]
            if not dest.exists():
                missing += 1
        report["items"]["assets"] = {"total": total, "missing": missing}
        if missing:
            report["ok"] = False
    else:
        report["ok"] = False
    return report


def print_report(report: dict) -> None:
    print(f"version: {report['version']}")
    print(f"root:    {report['root']}")
    items = report["items"]
    print(f"  version json : {'ok' if items.get('version_json') else 'MISSING'}")
    jar = items.get("client_jar", {})
    print(f"  client jar   : {'ok' if jar.get('ok') else 'MISSING'} ({jar.get('size', 0)} bytes)")
    lib = items.get("libraries", {})
    print(f"  libraries    : {lib.get('total', 0) - lib.get('missing', 0)}/{lib.get('total', 0)} present")
    if lib.get("missing_sample"):
        print(f"    missing e.g.: {', '.join(lib['missing_sample'])}")
    nat = items.get("natives", {})
    print(f"  natives      : {nat.get('dll', 0)} dll {nat.get('sample', [])}")
    assets = items.get("assets", {})
    print(f"  assets       : {assets.get('total', 0) - assets.get('missing', 0)}/{assets.get('total', 0)} present")
    print("RESULT:", "OK" if report["ok"] else "INCOMPLETE")



def ensure_version_jar(version_id: str, root: Path) -> None:
    """Forge/NeoForge inherit the vanilla jar but the library expects <id>.jar; copy it."""
    root = Path(root)
    vdir = root / "versions" / version_id
    path = vdir / f"{version_id}.json"
    if not path.exists():
        return
    target = vdir / f"{version_id}.jar"
    if target.exists():
        return
    data = json.loads(path.read_text(encoding="utf-8"))
    base = data.get("inheritsFrom")
    if not base:
        return
    source = root / "versions" / base / f"{base}.jar"
    if source.exists():
        shutil.copy2(source, target)


def ensure_version_libraries(version_id: str, root: Path, progress: Progress | None = None) -> int:
    """Download every library the version profile references (Forge/NeoForge profiles need this)."""
    root = Path(root)
    vdir = root / "versions" / version_id
    path = vdir / f"{version_id}.json"
    if not path.exists():
        return 0
    data = json.loads(path.read_text(encoding="utf-8"))
    libs = [lib for lib in data.get("libraries", []) if allowed_win(lib)]
    done = 0
    for lib in libs:
        art = lib.get("downloads", {}).get("artifact")
        if art:
            download(art["url"], root / "libraries" / art["path"], art.get("sha1"))
            done += 1
            continue
        name = lib.get("name", "")
        parts = name.split(":")
        if len(parts) >= 3 and lib.get("url"):
            group, artifact, ver = parts[0], parts[1], parts[2]
            classifier = parts[3] if len(parts) > 3 else None
            rel = f"{group.replace('.', '/')}/{artifact}/{ver}/{artifact}-{ver}" + (
                f"-{classifier}" if classifier else "") + ".jar"
            download(lib["url"].rstrip("/") + "/" + rel, root / "libraries" / rel)
            done += 1
    return done


def find_runtime_java(root: Path) -> str | None:
    """A Java runtime installed under <root>/runtime by the launcher, if any."""
    matches = sorted((Path(root) / "runtime").glob("**/bin/java.exe"))
    return str(matches[0]) if matches else None


def find_java() -> str:
    env = os.environ.get("MC_JAVA") or os.environ.get("JAVA_HOME")
    if env:
        p = Path(env) / "bin" / "java.exe"
        if p.exists():
            return str(p)
        if Path(env).exists() and Path(env).suffix == ".exe":
            return str(env)
    java = shutil.which("java")
    if java:
        return java
    candidates = []
    local = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local")))
    for pkg in local.glob("Packages/Microsoft.4297127D64EC6_*/LocalCache/Local/runtime/**/bin/java.exe"):
        candidates.append(pkg)
    minecraft_roots = [Path.home() / ".minecraft", Path(r"D:\我的世界\.minecraft")]
    for mc in minecraft_roots:
        candidates += list(mc.glob("runtime/**/bin/java.exe"))
        candidates += list(mc.glob("versions/**/runtime/bin/java.exe"))
    candidates += list(Path(r"C:\Program Files\Java").glob("jdk*/bin/java.exe"))
    candidates += list(Path(r"C:\Program Files\Eclipse Adoptium").glob("jdk*/bin/java.exe"))
    if candidates:
        return str(sorted(candidates)[-1])
    roots = [Path(__file__).resolve().parent.parent, Path(__file__).resolve().parent.parent.parent]
    for root in roots:
        for cand in root.glob(".toolchain/jdk/bin/java.exe"):
            return str(cand)
    raise RuntimeError("Java not found: set JAVA_HOME or MC_JAVA")
def load_version(version_id: str, root: Path) -> dict:
    root = Path(root)
    vdir = root / "versions" / version_id
    path = vdir / f"{version_id}.json"
    if not path.exists():
        raise RuntimeError(f"version {version_id} not installed ({path})")
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("inheritsFrom"):
        base = load_version(data["inheritsFrom"], root)
        merged = dict(base)
        merged["id"] = version_id
        merged["inheritsFrom"] = data["inheritsFrom"]
        merged["libraries"] = data.get("libraries", []) + base.get("libraries", [])
        merged["arguments"] = {
            "game": data.get("arguments", {}).get("game", []) + base.get("arguments", {}).get("game", []),
            "jvm": base.get("arguments", {}).get("jvm", []) + data.get("arguments", {}).get("jvm", []),
        }
        merged["mainClass"] = data.get("mainClass") or base.get("mainClass")
        merged["_dir"] = str(vdir)
        merged["_base_dir"] = base.get("_dir")
        return merged
    data["_dir"] = str(vdir)
    return data


def _resolve_args(items, values):
    out = []
    for item in items:
        if isinstance(item, str):
            out.append(item)
        elif isinstance(item, dict):
            if eval_rules(item.get("rules")):
                val = item.get("value")
                if isinstance(val, list):
                    out.extend(val)
                elif val is not None:
                    out.append(val)
    safe = {"quickPlayPath": "", "quickPlaySingleplayer": "", "quickPlayMultiplayer": "",
            "resolution_width": "854", "resolution_height": "480", "auth_session": "0",
            "game_assets": values.get("assets_root", "")}
    safe.update(values)
    resolved = []
    for a in out:
        if "${" in a:
            try:
                a = a.replace("${", "{").format_map(safe)
            except Exception:
                pass
        elif "{" in a:
            try:
                a = a.format_map(safe)
            except Exception:
                pass
        resolved.append(a)
    return resolved


def offline_uuid(name: str) -> str:
    return str(uuid.UUID(bytes=hashlib.md5(("OfflinePlayer:" + name).encode()).digest(), version=3))


def build_command(version_id: str, root: Path, username: str, max_mem="2G",
                  extra_jvm=None, extra_game=None) -> tuple[list[str], Path, Path]:
    try:
        import backend
        if backend.AVAILABLE and ("-forge-" in version_id or version_id.startswith("neoforge")):
            ensure_version_jar(version_id, root)
            ensure_version_libraries(version_id, root)
            cmd = backend.command(version_id, root, username) or []
            if cmd:
                cmd = [cmd[0], f"-Xmx{max_mem}"] + cmd[1:]
                log = root / "logs" / f"launch-{time.strftime('%Y%m%d-%H%M%S')}.log"
                return cmd, log, root
    except Exception:
        pass
    root = Path(root).resolve()
    data = load_version(version_id, root)
    libs = [lib for lib in data.get("libraries", []) if allowed_win(lib)]
    cp = []
    for lib in libs:
        art = lib.get("downloads", {}).get("artifact")
        if art:
            cp.append(str(root / "libraries" / art["path"]))
            continue
        name = lib.get("name", "")
        parts = name.split(":")
        if len(parts) >= 3:
            group, artifact, ver = parts[0], parts[1], parts[2]
            classifier = parts[3] if len(parts) > 3 else None
            rel = f"{group.replace('.', '/')}/{artifact}/{ver}/{artifact}-{ver}" + (
                f"-{classifier}" if classifier else "") + ".jar"
            cp.append(str(root / "libraries" / rel))
    vdir = Path(data["_dir"])
    jar = vdir / f"{version_id}.jar"
    if not jar.exists():
        base_name = data.get("inheritsFrom") or version_id
        base_dir = Path(data["_base_dir"]) if data.get("_base_dir") else vdir
        jar = base_dir / f"{base_name}.jar"
    cp.append(str(jar))

    assets_root = str(root / "assets")
    asset_index = (data.get("assetIndex") or {}).get("id", "legacy")
    natives_dir = vdir / "natives"
    if data.get("inheritsFrom"):
        base_natives = root / "versions" / data["inheritsFrom"] / "natives"
        if base_natives.exists() and any(base_natives.iterdir()):
            natives_dir = base_natives
        elif not natives_dir.exists():
            natives_dir.mkdir(parents=True, exist_ok=True)
    natives = str(natives_dir)
    uid = offline_uuid(username)
    values = {
        "auth_player_name": username,
        "version_name": version_id,
        "game_directory": str(root),
        "assets_root": assets_root,
        "assets_index_name": asset_index,
        "auth_uuid": uid,
        "auth_access_token": "0",
        "clientid": "0",
        "auth_xuid": "0",
        "user_type": "msa",
        "version_type": data.get("type", "release"),
        "natives_directory": natives,
        "launcher_name": "mcbridge-launcher",
        "launcher_version": "0.1",
        "classpath": ";".join(cp),
        "library_directory": str(root / "libraries"),
        "classpath_separator": ";",
    }
    args_blob = data.get("arguments") or {}
    jvm_args = _resolve_args(args_blob.get("jvm") or [], values)
    game_args = _resolve_args(args_blob.get("game") or [], values)
    if not jvm_args:
        jvm_args = ["-Djava.library.path=" + natives, "-cp", ";".join(cp)]
    main_class = data.get("mainClass", "net.minecraft.client.main.Main")
    legacy = main_class.startswith(("cpw.mods", "net.neoforged"))
    if legacy:
        jvm_args = [a for a in jvm_args if a not in ("-cp", "-classpath")]
        jvm_args.append("-DlegacyClassPath=" + ";".join(cp))
    elif "-cp" not in jvm_args and "-classpath" not in jvm_args:
        jvm_args += ["-cp", ";".join(cp)]
    if not any(a.startswith("-Djava.library.path=") for a in jvm_args):
        jvm_args.insert(0, "-Djava.library.path=" + natives)

    def ensure(flag, value):
        if flag not in game_args:
            game_args.extend([flag, value])

    ensure("--username", username)
    ensure("--version", version_id)
    ensure("--gameDir", str(root))
    ensure("--assetsDir", assets_root)
    ensure("--assetIndex", asset_index)
    ensure("--uuid", uid)
    ensure("--accessToken", "0")
    ensure("--userType", "msa")
    ensure("--versionType", data.get("type", "release"))
    java = find_runtime_java(root) or find_java()
    cmd = [java, f"-Xmx{max_mem}"] + jvm_args + [main_class] + game_args
    if extra_game:
        cmd += extra_game
    log = root / "logs" / f"launch-{time.strftime('%Y%m%d-%H%M%S')}.log"
    return cmd, log, root


def launch(version_id: str, root: Path, username: str, log_path: Path | None = None,
           max_mem="2G", extra_game=None):
    cmd, log, root = build_command(version_id, root, username, max_mem, extra_game=extra_game)
    log.parent.mkdir(parents=True, exist_ok=True)
    log_path = log_path or log
    f = open(log_path, "w", encoding="utf-8", errors="replace")
    f.write(" ".join(cmd) + "\n")
    f.flush()
    proc = subprocess.Popen(cmd, cwd=str(root), stdout=f, stderr=subprocess.STDOUT)
    return proc, log_path


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: mclaunch.py install <mc> <root> [fabric|vanilla|forge|neoforge]")
        print("       mclaunch.py launch <version_id> <root> <username>")
        print("       mclaunch.py verify <version_id> <root>")
        sys.exit(1)
    cmd = sys.argv[1]
    if cmd == "install":
        mc, root = sys.argv[2], Path(sys.argv[3])
        loader = sys.argv[4] if len(sys.argv) > 4 else "vanilla"
        p = Progress()
        if loader == "vanilla":
            print(install_vanilla(mc, root, p))
        elif loader == "fabric":
            install_vanilla_launcher_profile(mc, root)
            print(install_fabric(mc, root, p))
        elif loader == "forge":
            print(install_forge(mc, root, p))
        elif loader == "neoforge":
            print(install_neoforge(mc, root, p))
        else:
            raise SystemExit("unknown loader")
        print(p.snapshot())
    elif cmd == "verify":
        rep = verify_install(sys.argv[2], Path(sys.argv[3]))
        print_report(rep)
        sys.exit(0 if rep["ok"] else 3)
    elif cmd == "launch":
        proc, log = launch(sys.argv[2], Path(sys.argv[3]), sys.argv[4])
        print("pid", proc.pid, "log", log)
    else:
        print("unknown command")
        sys.exit(1)
