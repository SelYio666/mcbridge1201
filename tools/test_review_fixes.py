#!/usr/bin/env python3
"""Regression checks for the external review (2026-10-21).

Covers ISSUE-02 (patch validation), ISSUE-03 (mixin config audit), ISSUE-05 (log path),
ISSUE-06 (NeoForge detection), ISSUE-07 (snapshot/old listing) and ISSUE-08 (missing Java).

Run from the repository root:

    python tools/test_review_fixes.py

Exit code 0 means every check passed; 1 means at least one failed; 2 means a prerequisite
(built CLI or the converted sample jars) was missing, and the affected checks were skipped.
"""
from __future__ import annotations

import importlib.util
import json
import os
import re
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from http.server import ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORK = ROOT / "work" / "tmp" / "review-fixes"
WORK.mkdir(parents=True, exist_ok=True)

RESULTS: list[tuple[str, bool, str]] = []
SKIPPED: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    RESULTS.append((name, bool(ok), detail))
    print(f"{'PASS' if ok else 'FAIL'} {name}" + (f"  [{detail}]" if detail and not ok else ""))


def cli_path() -> Path | None:
    base = ROOT / "java" / "build" / "install" / "mcbridge1201" / "bin"
    if os.name == "nt":
        p = base / "mcbridge1201.bat"
    else:
        p = base / "mcbridge1201"
    return p if p.exists() else None


def ensure_java_home() -> bool:
    """Find a JDK so the patch CLI can run without the caller exporting JAVA_HOME."""
    env = os.environ.get("JAVA_HOME")
    if env and (Path(env) / "bin" / ("java.exe" if os.name == "nt" else "java")).exists():
        return True
    candidates = [
        ROOT.parent / ".toolchain" / "jdk",
        ROOT / ".toolchain" / "jdk",
        Path(r"C:\Program Files\Java"),
        Path(r"C:\Program Files\Eclipse Adoptium"),
    ]
    for c in candidates:
        if c.name in ("Java", "Eclipse Adoptium") and c.is_dir():
            found = sorted(c.glob("jdk*/bin/java.exe"))
            if found:
                os.environ["JAVA_HOME"] = str(found[-1].parent.parent)
                return True
        elif (c / "bin" / "java.exe").exists():
            os.environ["JAVA_HOME"] = str(c)
            return True
    import shutil

    java = shutil.which("java")
    if java:
        os.environ["JAVA_HOME"] = str(Path(java).parent.parent)
        return True
    return False


def run(cmd: list[str]) -> tuple[int, str]:
    import subprocess

    # The Java CLI writes diagnostics in the console codepage (GBK on this box); decode leniently.
    p = subprocess.run(cmd, capture_output=True, text=True, errors="replace")
    return p.returncode, ((p.stdout or "") + (p.stderr or ""))


# ---------------------------------------------------------------- ISSUE-03
def test_issue03() -> None:
    bad = WORK / "bad.jar"
    ok = WORK / "ok.jar"
    with zipfile.ZipFile(bad, "w") as z:
        z.writestr("probe.mixins.json", "{broken json")
    with zipfile.ZipFile(ok, "w") as z:
        z.writestr("probe.mixins.json", json.dumps({"package": "probe", "mixins": []}))
    rc_bad, _ = run([sys.executable, str(ROOT / "tools" / "audit_mixins.py"), "--jar", str(bad)])
    rc_ok, _ = run([sys.executable, str(ROOT / "tools" / "audit_mixins.py"), "--jar", str(ok)])
    check("ISSUE-03 broken mixin config fails", rc_bad == 1, f"rc={rc_bad}")
    check("ISSUE-03 valid mixin config passes", rc_ok == 0, f"rc={rc_ok}")


# ---------------------------------------------------------------- ISSUE-02
def test_issue02() -> None:
    cli = cli_path()
    if cli is None:
        print("SKIP ISSUE-02 (CLI not built; run gradle installDist)")
        SKIPPED.append("ISSUE-02")
        return
    if not ensure_java_home():
        print("SKIP ISSUE-02 (no JDK found; set JAVA_HOME)")
        SKIPPED.append("ISSUE-02")
        return
    fresh = ROOT / "work/cb/out/popular/entityculling/entityculling-fabric-1.11.3-mc1.20.1+1.21.1.jar"
    patched = ROOT / "work/cb/out/popular/entityculling/entityculling-nested-patched.jar"
    rules = ROOT / "rules/fabric-1.21.1/identifier-single-arg.json"
    bridges = ROOT / "work/bridges"
    if not fresh.exists() or not rules.exists() or not bridges.exists():
        check("ISSUE-02 patch validation", False, "converted sample or bridges missing")
        return

    data = json.loads(rules.read_text(encoding="utf-8"))
    bad = WORK / "bad-schema.json"
    d = dict(data, schemaVersion="9.9")
    bad.write_text(json.dumps(d), encoding="utf-8")
    rc, _ = run([str(cli), "patch", "--in", str(fresh), "--out", str(WORK / "o1.jar"),
                 "--rules", str(bad), "--bridge-dir", str(bridges)])
    check("ISSUE-02 unsupported schema exits 2", rc == 2, f"rc={rc}")

    other = WORK / "other-target.json"
    d2 = dict(data, target="fabric-1.20.1")
    other.write_text(json.dumps(d2), encoding="utf-8")
    rc, _ = run([str(cli), "patch", "--in", str(fresh), "--out", str(WORK / "o2.jar"),
                 "--rules", str(rules), "--rules", str(other), "--bridge-dir", str(bridges)])
    check("ISSUE-02 mixed targets exit 2", rc == 2, f"rc={rc}")

    rc, _ = run([str(cli), "patch", "--in", str(fresh), "--out", str(WORK / "o3.jar"),
                 "--rules", str(rules), "--bridge-dir", str(bridges),
                 "--require-hit", "no.such.rule"])
    check("ISSUE-02 missing required hit exits 3", rc == 3, f"rc={rc}")

    if patched.exists():
        rc, _ = run([str(cli), "patch", "--in", str(patched), "--out", str(WORK / "o4.jar"),
                     "--rules", str(rules), "--bridge-dir", str(bridges),
                     "--require-hit", "no.such.rule"])
        check("ISSUE-02 already-patched input exits 4", rc == 4, f"rc={rc}")
    else:
        check("ISSUE-02 already-patched input exits 4", False, "patched sample missing")

    rc, _ = run([str(cli), "patch", "--in", str(fresh), "--out", str(WORK / "o5.jar"),
                 "--rules", str(rules), "--bridge-dir", str(bridges),
                 "--require-hit", "identifier.one-arg-ctor"])
    check("ISSUE-02 matching required hit exits 0", rc == 0, f"rc={rc}")


# ---------------------------------------------------------------- ISSUE-05..08
def test_launcher() -> None:
    sys.path.insert(0, str(ROOT / "launcher"))
    try:
        import server  # noqa: E402
        import backend  # noqa: E402
    except Exception as exc:  # noqa: BLE001
        check("ISSUE-05..08 launcher checks", False, f"import failed: {exc}")
        return

    lib = WORK / "launcher-root"
    if lib.exists():
        import shutil

        shutil.rmtree(lib)
    (lib / "versions").mkdir(parents=True)
    for name, meta in {
        "1.21.1": {"id": "1.21.1"},
        "24w14a": {"id": "24w14a"},
        "b1.7.3": {"id": "b1.7.3"},
        "neoforge-20.4.123": {"id": "neoforge-20.4.123", "inheritsFrom": "1.20.4"},
        "neoforge-21.1.172": {"id": "neoforge-21.1.172", "inheritsFrom": "1.21.1"},
        "One Prime Piece 1.7.6": {"id": "One Prime Piece 1.7.6"},
    }.items():
        d = lib / "versions" / name
        d.mkdir(parents=True, exist_ok=True)
        (d / f"{name}.json").write_text(json.dumps(meta), encoding="utf-8")

    server._MANIFEST_IDS = set()
    listed = [v["id"] for v in server.installed_versions(lib)]
    check("ISSUE-07 snapshot listed", "24w14a" in listed, str(listed))
    check("ISSUE-07 old beta listed", "b1.7.3" in listed, str(listed))
    check("ISSUE-07 modpack instance hidden", "One Prime Piece 1.7.6" not in listed, str(listed))

    got = backend.installed("neoforge", "1.21.1", lib)
    check("ISSUE-06 neoforge picks matching game version", got == "neoforge-21.1.172", str(got))

    logs = lib / "logs"
    logs.mkdir()
    log = logs / "启动 日志 1.log"
    log.write_text("hello log\n", encoding="utf-8")
    server.CONFIG = WORK / "launcher-config.json"
    server.CONFIG.write_text(json.dumps({"root": str(lib), "username": "T", "mem": "2G"}),
                             encoding="utf-8")
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
    port = httpd.server_address[1]
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    time.sleep(0.3)

    def get(path: str, timeout: int = 5):
        with urllib.request.urlopen(f"http://127.0.0.1:{port}{path}", timeout=timeout) as r:
            return r.status, r.read()

    def post(path: str, payload: dict):
        req = urllib.request.Request(
            f"http://127.0.0.1:{port}{path}",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, r.read()

    # launcher API surface added after the review: pack scanning and runtime listing
    packs = lib / "packs"
    packs.mkdir(exist_ok=True)
    with zipfile.ZipFile(packs / "probe.mrpack", "w") as z:
        z.writestr("modrinth.index.json", json.dumps({
            "formatVersion": 1, "game": "minecraft", "versionId": "1.0.0",
            "name": "probe pack", "files": [],
            "dependencies": {"minecraft": "1.21.1", "fabric-loader": "0.19.5"}}))
    status, body = get("/api/mrpacks")
    packs_data = json.loads(body)
    names = [p.get("name") for p in packs_data.get("packs", [])]
    check("launcher /api/mrpacks lists packs", status == 200 and "probe pack" in names, str(names))

    mods_dir = lib / "mods"
    mods_dir.mkdir(exist_ok=True)
    (mods_dir / "probe.jar").write_text("x", encoding="utf-8")
    (mods_dir / "probe2.jar.disabled").write_text("x", encoding="utf-8")
    status, body = get("/api/mods")
    mods_data = json.loads(body)
    names = {m["name"]: m["enabled"] for m in mods_data.get("mods", [])}
    check("launcher lists mods", status == 200 and names.get("probe.jar") is True
          and names.get("probe2.jar.disabled") is False, str(names))
    status, body = post("/api/toggle-mod", {"name": "probe2.jar.disabled"})
    status2, body2 = get("/api/mods")
    env = {m["name"]: m["enabled"] for m in json.loads(body2).get("mods", [])}
    check("launcher toggles a mod", status == 200 and env.get("probe2.jar") is True, str(env))

    del_dir = lib / "versions" / "fabric-delete-probe-1.21.1"
    del_dir.mkdir(parents=True, exist_ok=True)
    (del_dir / "fabric-delete-probe-1.21.1.json").write_text("{}", encoding="utf-8")
    status, body = post("/api/delete-version", {"id": "fabric-delete-probe-1.21.1"})
    gone = not del_dir.exists()
    check("launcher deletes an installed version", status == 200 and gone, f"status={status} gone={gone}")
    try:
        post("/api/delete-version", {"id": "../escape"})
        rejected = False
    except urllib.error.HTTPError as exc:
        rejected = exc.code == 400
    check("launcher rejects path traversal in delete", rejected)

    # the in-app help must serve the same usage guide that ships in docs/
    status, body = get("/guide")
    check("launcher serves the usage guide", status == 200
          and "使用说明" in body.decode("utf-8", "replace"))

    # folder helpers: other launchers must be able to find mods/versions without guessing
    from pathlib import Path as _Path

    mods = server.dir_target(_Path(lib), "mods")
    check("launcher dir_target resolves mods", str(mods).replace("\\", "/").endswith("/mods"))
    rejected = 0
    for bad_target, bad_vid in (("../", ""), ("C:/Windows", ""), ("version", ".."),
                                ("version", "../x")):
        try:
            server.dir_target(_Path(lib), bad_target, bad_vid)
        except ValueError:
            rejected += 1
    check("launcher dir_target rejects escapes", rejected == 4, str(rejected))

    status, body = get("/api/dirs?version=neoforge-21.1.172")
    dirs = json.loads(body)
    check("launcher /api/dirs lists game folders", status == 200
          and dirs.get("dirs", {}).get("mods", "").replace("\\", "/").endswith("/mods")
          and dirs.get("dirs", {}).get("version", "").replace("\\", "/").endswith(
              "neoforge-21.1.172"), str(dirs.get("dirs"))[:120])

    status, body = get("/api/downloads")
    downloads = json.loads(body)
    check("launcher /api/downloads exposes the source log", status == 200
          and isinstance(downloads.get("events"), list))

    status, body = get("/api/task")
    task = json.loads(body)
    check("launcher /api/task exposes byte progress and speed", status == 200
          and "bytes_done" in task and "speed" in task and "source" in task, str(task)[:120])

    status, _body = post("/api/config", {"download_source": "mirror"})
    cfg2 = json.loads(get("/api/config")[1])
    check("launcher config stores download_source", status == 200
          and cfg2.get("download_source") == "mirror", str(cfg2.get("download_source")))
    post("/api/config", {"download_source": "auto"})

    status, body = get("/api/source-health")
    health = json.loads(body)
    check("launcher /api/source-health reports mode and hosts", status == 200
          and "mode" in health and isinstance(health.get("health"), list), str(health)[:100])

    summary = server.summarize_canary({
        "ok": True, "core_ok": True, "mirrors_ok": False, "neoforge_ok": False,
        "required": [{"label": "a", "ok": True}],
        "mirrors": [{"label": "bmcl x", "ok": False}],
        "neoforge": [], "expected_misses": [],
    })
    check("launcher condenses canary results", summary["core_ok"] is True
          and summary["mirror_failures"] == ["bmcl x"], str(summary))

    opened = []
    orig_open = server.open_in_explorer
    server.open_in_explorer = opened.append
    try:
        status, _body = post("/api/open-dir", {"target": "mods"})
        check("launcher opens the mods folder", status == 200 and opened
              and str(opened[-1]).replace("\\", "/").endswith("/mods"),
              str(opened[-1]) if opened else "no open")
        try:
            post("/api/open-dir", {"target": "../"})
            rejected_open = False
        except urllib.error.HTTPError as exc:
            rejected_open = exc.code == 400
        check("launcher rejects unknown open-dir target", rejected_open)
    finally:
        server.open_in_explorer = orig_open

    status, _body = post("/api/sync-profiles", {})
    profiles = json.loads((lib / "launcher_profiles.json").read_text(encoding="utf-8"))
    last_ids = {p.get("lastVersionId") for p in profiles.get("profiles", {}).values()}
    check("launcher sync-profiles writes launcher_profiles entries", status == 200
          and "neoforge-21.1.172" in last_ids and "1.21.1" in last_ids, str(sorted(last_ids)))

    try:
        status, body = get("/api/jvm", timeout=60)
        jvm_data = json.loads(body)
        check("launcher /api/jvm returns json", status == 200 and "available" in jvm_data,
              str(jvm_data)[:80])
    except (TimeoutError, urllib.error.URLError):
        print("SKIP launcher /api/jvm (network timeout)")
        SKIPPED.append("launcher /api/jvm")

    try:
        status, body = get("/api/loader-versions?loader=fabric&mc=1.21.1", timeout=60)
        lv = json.loads(body)
        ok = status == 200 and ("versions" in lv) and (bool(lv.get("versions")) or bool(lv.get("error")))
        check("launcher /api/loader-versions responds", ok, str(lv.get("error", ""))[:80])
    except (TimeoutError, urllib.error.URLError):
        print("SKIP launcher /api/loader-versions (network timeout)")
        SKIPPED.append("launcher /api/loader-versions")

    enc = "/log/" + urllib.parse.quote(str(log).replace("\\", "/"))
    status, body = get(enc)
    check("ISSUE-05 encoded log path readable", status == 200 and b"hello log" in body, f"status={status}")

    orig = server.find_java
    server.find_java = lambda: (_ for _ in ()).throw(RuntimeError("Java not found"))
    try:
        status, body = get("/api/config")
        data = json.loads(body)
        ok = status == 200 and data.get("java") is None and data.get("java_error")
        check("ISSUE-08 missing java returns JSON", ok, f"status={status}")
    finally:
        server.find_java = orig
        httpd.shutdown()


def test_neoforge_install() -> None:
    """NeoForge install completeness: a profile json alone must not count as installed."""
    sys.path.insert(0, str(ROOT / "launcher"))
    try:
        import mclaunch
    except Exception as exc:  # noqa: BLE001
        check("NEOFORGE import mclaunch", False, f"import failed: {exc}")
        return

    import shutil

    lib = WORK / "neoforge-unit"
    if lib.exists():
        shutil.rmtree(lib)
    lib.mkdir(parents=True)
    ver, vid = "21.1.264", "neoforge-21.1.264"

    arts = mclaunch.loader_artifacts(vid, lib)
    check("NEOFORGE empty root reports all artifacts missing",
          bool(arts) and not any(arts.values()), str(arts))

    # a minimal installed profile: base version json + jar + empty asset index
    base = lib / "versions" / "1.21.1"
    base.mkdir(parents=True)
    (base / "1.21.1.json").write_text(json.dumps(
        {"id": "1.21.1", "libraries": [], "assetIndex": {"id": "unit"}, "assets": "unit"}),
        encoding="utf-8")
    (base / "1.21.1.jar").write_bytes(b"jar")
    (lib / "assets" / "indexes").mkdir(parents=True)
    (lib / "assets" / "indexes" / "unit.json").write_text(json.dumps({"objects": {}}), encoding="utf-8")
    vdir = lib / "versions" / vid
    vdir.mkdir(parents=True)
    (vdir / f"{vid}.json").write_text(json.dumps(
        {"id": vid, "inheritsFrom": "1.21.1", "libraries": [],
         "mainClass": "net.minecraft.client.main.Main",
         "arguments": {"game": [], "jvm": []}}), encoding="utf-8")

    rep = mclaunch.verify_install(vid, lib)
    check("NEOFORGE verify rejects profile-only install", rep["ok"] is False
          and rep["items"].get("loader_artifacts", {}).get("neoforge_universal") is False,
          str(rep["items"].get("loader_artifacts")))

    try:
        mclaunch.build_command(vid, lib, "UnitUser")
        refused = False
    except RuntimeError as exc:
        refused = "incomplete" in str(exc)
    check("NEOFORGE build_command refuses incomplete install", refused)

    # installer library seeding: a library already present with the right sha1 is not re-downloaded
    installer = WORK / "fake-neoforge-installer.jar"
    seeded = lib / "libraries" / "net" / "example" / "x" / "1" / "x-1.jar"
    seeded.parent.mkdir(parents=True)
    seeded.write_bytes(b"x")
    digest = mclaunch.sha1_of(seeded)
    entry = {"downloads": {"artifact": {"path": "net/example/x/1/x-1.jar",
                                        "url": "https://invalid.example/x-1.jar",
                                        "sha1": digest}}}
    with zipfile.ZipFile(installer, "w") as z:
        z.writestr("install_profile.json", json.dumps({"libraries": [entry]}))
        z.writestr("version.json", json.dumps({"libraries": [entry]}))
    check("NEOFORGE installer seeding skips verified files",
          mclaunch.prepare_installer_libraries(installer, lib) == 0)

    # the four game files FancyModLoader needs for the 'minecraft' / 'neoforge' modules
    mcjars = lib / "libraries" / "net" / "minecraft" / "client" / "1.21.1-20240808.144430"
    mcjars.mkdir(parents=True)
    (mcjars / "client-1.21.1-20240808.144430-srg.jar").write_bytes(b"s")
    (mcjars / "client-1.21.1-20240808.144430-extra.jar").write_bytes(b"e")
    nf = lib / "libraries" / "net" / "neoforged" / "neoforge" / ver
    nf.mkdir(parents=True)
    universal = nf / f"neoforge-{ver}-universal.jar"
    (nf / f"neoforge-{ver}-client.jar").write_bytes(b"c")
    universal.write_bytes(b"u")

    check("NEOFORGE artifacts detected once present",
          all(mclaunch.loader_artifacts(vid, lib).values()))
    check("NEOFORGE verify accepts a complete install", mclaunch.verify_install(vid, lib)["ok"] is True)

    # force our own command builder: the mll backend needs a real profile to add credentials
    backend_mod = None
    orig_available = None
    try:
        import backend as backend_mod  # noqa: E402
        orig_available = backend_mod.AVAILABLE
        backend_mod.AVAILABLE = False
    except Exception:  # noqa: BLE001
        backend_mod = None
    try:
        cmd, _log, _root = mclaunch.build_command(vid, lib, "UnitUser")
    finally:
        if backend_mod is not None:
            backend_mod.AVAILABLE = orig_available
    check("NEOFORGE complete install builds a command", "--username" in cmd
          and "UnitUser" in cmd, str(cmd[:3]))

    # Forge/NeoForge return early through backend.command(); extra game args (quickPlay) must survive
    qcmd: list[str] = []
    try:
        import backend as backend_mod2  # noqa: E402
        saved_cmd = backend_mod2.command
        saved_avail2 = backend_mod2.AVAILABLE
        saved_arts = mclaunch.loader_artifacts
        saved_jar = mclaunch.ensure_version_jar
        saved_libs = mclaunch.ensure_version_libraries
        backend_mod2.AVAILABLE = True
        backend_mod2.command = lambda _v, _r, _u: ["java", "-cp", "x", "Main"]
        mclaunch.loader_artifacts = lambda _v, _r: {"probe": True}
        mclaunch.ensure_version_jar = lambda *a, **k: None
        mclaunch.ensure_version_libraries = lambda *a, **k: None
        try:
            qcmd, _ql, _qr = mclaunch.build_command(
                vid, lib, "UnitUser", extra_game=["--quickPlaySingleplayer", "W"])
            kept = qcmd[-2:] == ["--quickPlaySingleplayer", "W"]
        finally:
            backend_mod2.command = saved_cmd
            backend_mod2.AVAILABLE = saved_avail2
            mclaunch.loader_artifacts = saved_arts
            mclaunch.ensure_version_jar = saved_jar
            mclaunch.ensure_version_libraries = saved_libs
        check("NEOFORGE backend command keeps extra game args (quickPlay)", kept,
              " ".join(qcmd[-4:]))
    except Exception as exc:  # noqa: BLE001
        check("NEOFORGE backend command keeps extra game args (quickPlay)", False, repr(exc))

    universal.unlink()
    rep = mclaunch.verify_install(vid, lib)
    check("NEOFORGE verify flags a missing universal jar", rep["ok"] is False
          and rep["items"]["loader_artifacts"]["neoforge_universal"] is False,
          str(rep["items"]["loader_artifacts"]))


def test_loader_base_ensure() -> None:
    """install_forge must ensure the vanilla base version before/with the loader profile."""
    sys.path.insert(0, str(ROOT / "launcher"))
    try:
        import mclaunch
    except Exception as exc:  # noqa: BLE001
        check("LOADER import mclaunch", False, f"import failed: {exc}")
        return

    import shutil
    lib = WORK / "forge-base-unit"
    if lib.exists():
        shutil.rmtree(lib)
    lib.mkdir(parents=True)
    calls: list[tuple[str, str]] = []
    saved = (mclaunch.install_vanilla_launcher_profile, mclaunch.http_json,
             mclaunch.download_maven, mclaunch.prepare_installer_libraries,
             mclaunch._run_installer)
    vid = None
    try:
        mclaunch.install_vanilla_launcher_profile = lambda mc, root: calls.append((mc, str(root)))
        mclaunch.http_json = lambda *a, **k: {"promos": {"1.20.1-recommended": "47.4.28"}}
        mclaunch.download_maven = lambda *a, **k: 0
        mclaunch.prepare_installer_libraries = lambda *a, **k: 0

        def fake_run(_installer, root, _log):
            vdir = Path(root) / "versions" / "1.20.1-forge-47.4.28"
            vdir.mkdir(parents=True, exist_ok=True)
            (vdir / "1.20.1-forge-47.4.28.json").write_text("{}", encoding="utf-8")
            return 0

        mclaunch._run_installer = fake_run
        vid = mclaunch.install_forge("1.20.1", lib)
    except Exception as exc:  # noqa: BLE001
        check("LOADER install_forge ensures the vanilla base first", False, repr(exc))
        return
    finally:
        (mclaunch.install_vanilla_launcher_profile, mclaunch.http_json,
         mclaunch.download_maven, mclaunch.prepare_installer_libraries,
         mclaunch._run_installer) = saved
    check("LOADER install_forge ensures the vanilla base first",
          calls == [("1.20.1", str(lib))] and vid == "1.20.1-forge-47.4.28", f"{calls} {vid}")


def test_immediatelyfast_port() -> None:
    """The ImmediatelyFast port rule must stay bound to real capability/risk/evidence."""
    rule = ROOT / "rules" / "fabric-1.21.1" / "immediatelyfast-batching-port.json"
    try:
        data = json.loads(rule.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        check("IFPORT rule loads", False, repr(exc))
        return
    reps = data.get("mixinClassReplacements") or []
    bound = (len(reps) >= 6
             and all(r.get("capability") and r.get("risk") and r.get("evidence") for r in reps))
    check("IFPORT rule binds 6+ replacements to capability/risk/evidence", bound,
          f"{len(reps)} replacements")
    additions = data.get("mixinConfigAdditions") or []
    added = (len(additions) >= 2
             and all(a.get("capability") and a.get("evidence") for a in additions))
    check("IFPORT rule re-adds the HUD mixins with evidence", added, f"{len(additions)} additions")
    ctors = data.get("constructorRedirects") or []
    bridged = (len(ctors) >= 2
               and all(c.get("bridgeClass") == "top/mcbridge1201/bridge/IdentifierBridge"
                       for c in ctors))
    check("IFPORT rule bridges the Identifier constructors", bridged, f"{len(ctors)} redirects")
    base = ROOT / "java" / "src" / "compat" / "java" / "net" / "raphimc" / "immediatelyfast"
    files = [
        base / "feature" / "core" / "BatchableBufferSource.java",
        base / "feature" / "batching" / "BatchingBuffers.java",
        base / "feature" / "batching" / "HudBatchingBufferSource.java",
        base / "feature" / "batching" / "SimpleImmediate.java",
        base / "feature" / "batching" / "BatchingRenderLayers.java",
        base / "feature" / "batching" / "BlendFuncDepthFuncState.java",
        base / "injection" / "mixins" / "core" / "MixinVertexConsumerProvider.java",
        base / "injection" / "mixins" / "fast_text_lookup" / "MixinTextRenderer_Drawer.java",
        base / "injection" / "mixins" / "hud_batching" / "consumer" / "MixinDrawContext.java",
        base / "injection" / "mixins" / "hud_batching" / "MixinGameRendererHud.java",
        base / "injection" / "mixins" / "map_atlas_generation" / "MixinMapRenderer.java",
        base / "injection" / "mixins" / "map_atlas_generation" / "MixinMapRenderer_MapTexture.java",
        base / "feature" / "map_atlas_generation" / "MapAtlasTexture.java",
        base / "injection" / "mixins" / "fast_buffer_upload" / "MixinVertexBuffer.java",
    ]
    missing = [p.name for p in files if not p.exists()]
    tomb = [p.name for p in files
            if p.exists() and "Tombstones_" in p.read_text(encoding="utf-8", errors="replace")]
    check("IFPORT sources exist and avoid tombstones", not missing and not tomb,
          f"missing={missing} tomb={tomb}")
    draw_src = (base / "feature" / "core" / "BatchableBufferSource.java").read_text(
        encoding="utf-8", errors="replace")
    guard = ("vanilla draw path owns" in draw_src
             and draw_src.count("this.releaseOwned(") <= 1)
    check("IFPORT draw path does not double-close the builder allocator", guard,
          f"releaseOwned calls={draw_src.count('this.releaseOwned(')}")
    iris_ok = ("IrisCompat.IRIS_LOADED" in draw_src
               and "iris compat active" in draw_src
               and "skipExtension" in draw_src)
    check("IFPORT keeps the Iris compatibility branch wired", iris_ok,
          "BatchableBufferSource must call IrisCompat and log the branch")
    provider_src = (base / "injection" / "mixins" / "core"
                    / "MixinVertexConsumerProvider.java").read_text(
        encoding="utf-8", errors="replace")
    fallback_ok = ("SimpleImmediate" in provider_src
                   and "disable_universal_batching" in provider_src)
    check("IFPORT keeps the universal-batching fallback (SimpleImmediate)", fallback_ok,
          "MixinVertexConsumerProvider must fall back to SimpleImmediate")
    hud_src = (base / "feature" / "batching" / "HudBatchingBufferSource.java").read_text(
        encoding="utf-8", errors="replace")
    lit_ok = ("LightingState" in hud_src
              and "WrappedRenderLayer" in hud_src
              and "renderingItem" in hud_src)
    check("IFPORT keeps the item per-lighting variants wired", lit_ok,
          "HudBatchingBufferSource must wrap item layers per LightingState")
    strips = data.get("mixinStrips") or []
    map_strips = [c for s in strips for c in (s.get("classes") or []) if "MapRenderer" in c]
    check("IFPORT no longer strips the map atlas mixins", not map_strips, str(map_strips))
    addition_names = {a.get("mixinClass") for a in additions}
    map_configs = {"map_atlas_generation.MixinMapRenderer",
                   "map_atlas_generation.MixinMapRenderer_MapTexture"}
    check("IFPORT re-registers both map atlas mixins", map_configs <= addition_names,
          str(sorted(addition_names)))
    by_target = {r.get("targetClass"): r for r in reps}
    renderer_rep = by_target.get(
        "net/raphimc/immediatelyfast/injection/mixins/map_atlas_generation/MixinMapRenderer", {})
    texture_rep = by_target.get(
        "net/raphimc/immediatelyfast/injection/mixins/map_atlas_generation/MixinMapRenderer_MapTexture", {})
    atlas_helper = "net/raphimc/immediatelyfast/feature/map_atlas_generation/MapAtlasTexture"
    map_reps = (bool(renderer_rep and texture_rep)
                and (renderer_rep.get("alsoEmbed") or []) == [atlas_helper])
    check("IFPORT replaces both map mixins and embeds MapAtlasTexture", map_reps,
          f"renderer={bool(renderer_rep)} texture={bool(texture_rep)}")
    renderer_src = (base / "injection" / "mixins" / "map_atlas_generation"
                    / "MixinMapRenderer.java").read_text(encoding="utf-8", errors="replace")
    texture_src = (base / "injection" / "mixins" / "map_atlas_generation"
                   / "MixinMapRenderer_MapTexture.java").read_text(encoding="utf-8", errors="replace")
    import re

    def code_only(text: str) -> str:
        text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
        return re.sub(r"//[^\n]*", "", text)

    renderer_code = code_only(renderer_src)
    texture_code = code_only(texture_src)
    map_source_ok = (
        "class_9209" in renderer_code
        and "mapId.comp_2315()" in renderer_code
        and "net.lenni0451" not in texture_code
        and "Objects.allocate" not in texture_code
        and "method_1344" not in texture_code
        and "method_60803" in texture_code
        # package-private target constructor stores a field before super(); the capture uses an
        # after-super injection so Mixin accepts the instance handler
        and "Ljava/lang/Object;<init>()V" in texture_code
        and "shift = At.Shift.AFTER" in texture_code
        and "immediatelyFast$dummyTexture" in texture_code
    )
    check("IFPORT map sources use the 1.21.1 signatures and drop lenni allocate", map_source_ok,
          "MixinMapRenderer.class_9209 / MapTexture method_60803 + after-super capture")
    atlas_src = (base / "feature" / "map_atlas_generation" / "MapAtlasTexture.java").read_text(
        encoding="utf-8", errors="replace")
    atlas_ok = ("class_2960.method_60655" in atlas_src
                and "method_4616" in atlas_src
                and "method_4615" in atlas_src)
    check("IFPORT embeds the 1.21.1 MapAtlasTexture factories", atlas_ok,
          "MapAtlasTexture must use the Identifier factory and register/unregister")
    build_src = (ROOT / "tools" / "build_immediatelyfast_port.py").read_text(
        encoding="utf-8", errors="replace")
    widen_ok = ("widen_stub" in build_src
                and "net/minecraft/class_330$class_331" in build_src
                and (ROOT / "tools" / "widen_stub.py").exists())
    check("IFPORT build widens the package-private MapTexture stub", widen_ok,
          "javac needs class_330$class_331 public in the compile-only stub")
    vertex_src = (base / "injection" / "mixins" / "fast_buffer_upload"
                  / "MixinVertexBuffer.java").read_text(encoding="utf-8", errors="replace")
    vertex_code = code_only(vertex_src)
    vertex_config = any("MixinVertexBuffer" in (a.get("mixinClass") or "") for a in additions)
    vertex_rep = any("MixinVertexBuffer" in (r.get("targetClass") or "") for r in reps)
    vertex_ok = (
        vertex_config and vertex_rep
        and "method_60829" in vertex_code
        and "method_43443" in vertex_code
        and "usage == 35044" in vertex_code
        and "GL15C.glBufferSubData" in vertex_code
        and "fast-buffer-upload subdata" in vertex_code
    )
    check("IFPORT re-registers MixinVertexBuffer with the 1.21.1 60829 entry point", vertex_ok,
          f"config={vertex_config} replacement={vertex_rep}")
    try:
        evidence = json.loads((ROOT / "runs" / "p178-vertex-upload" / "result.json").read_text(
            encoding="utf-8"))
        diffs = evidence["pixel_diff"]
        evidence_ok = (
            evidence.get("passed") is True
            and evidence["phases"]["on1"]["fast_upload_markers"] > 0
            and evidence["phases"]["off1"]["fast_upload_markers"] == 0
            and diffs["off1_on1"]["changed_ratio"] <= diffs["off_off2_control"]["changed_ratio"]
        )
        detail = (f"off/on={diffs['off1_on1']['changed_ratio']:.6f} "
                  f"control={diffs['off_off2_control']['changed_ratio']:.6f}")
    except Exception as exc:  # noqa: BLE001 - missing/invalid evidence is a failure
        evidence_ok = False
        detail = repr(exc)
    check("IFPORT vertex A/B evidence stays within the off/off control", evidence_ok, detail)
    registered = ([a.get("mixinClass") or "" for a in additions]
                  + [r.get("targetClass") or "" for r in reps])
    dead_ok = not any(
        name in entry
        for entry in registered
        for name in ("MixinBufferBuilder", "MixinFontManager")
    )
    check("IFPORT leaves the upstream-removed BufferBuilder/FontManager mixins inert",
          dead_ok, str([e for e in registered if "Mixin" in e]))
    closed_ok = ("isClosed()" in atlas_src
                 and "boolean closed" in atlas_src
                 and "atlasTexture.isClosed()" in texture_src
                 and "skip-closed" in texture_src)
    check("IFPORT map atlas skips a closed image during world exit", closed_ok,
          "MapAtlasTexture.isClosed + MapTexture updateAtlasTexture guard")
    p183_result = json.loads((ROOT / "runs" / "p183-trash-key" / "result.json").read_text(encoding="utf-8"))
    p183_run = (ROOT / "runs" / "p183-trash-key" / "run.py").read_text(encoding="utf-8", errors="replace")
    p183_ok = (all(p183_result.get(k) for k in ("key_seen", "run_seen", "provider_seen", "server_empty"))
               and "extended = 0x0001" in p183_run and "DEBUG_KEY key=261" in p183_run)
    check("TRASH the real empty-trash Delete key reaches the provider and server", p183_ok,
          "p183 result flags + extended-key injection")
    p184_result = json.loads((ROOT / "runs" / "p184-trash-delete-all" / "result.json").read_text(encoding="utf-8"))
    p184_run = (ROOT / "runs" / "p184-trash-delete-all" / "run.py").read_text(encoding="utf-8", errors="replace")
    p184_ok = (all(p184_result.get(k) for k in ("shift_seen", "delete_seen", "server_zero", "client_zero"))
               and "press_shift_delete" in p184_run and "mods=1" in p184_run)
    check("TRASH Shift+Delete deletes same-item stacks across slots", p184_ok,
          "p184 result flags + shift-delete injection")
    p185_result = json.loads((ROOT / "runs" / "p185-trash-undelete-right" / "result.json").read_text(encoding="utf-8"))
    p185_run = (ROOT / "runs" / "p185-trash-undelete-right" / "run.py").read_text(encoding="utf-8", errors="replace")
    p185_ok = (all(p185_result.get(k) for k in ("right_seen", "carried_one", "client_trash_4", "server_trash_4"))
               and "focus_window" in p185_run and "right_click" in p185_run)
    check("TRASH empty-cursor right-click takes one item and leaves four", p185_ok,
          "p185 result flags + focus-first origin + right-click injection")
    p186_result = json.loads((ROOT / "runs" / "p186-shulker-grid-client-item" / "result.json").read_text(encoding="utf-8"))
    p186_wrapper = (ROOT / "java" / "src" / "shulkerpreview" / "java" / "mcbridgepreview"
                    / "ComponentPreviewProvider.java").read_text(encoding="utf-8", errors="replace")
    shulker_rule = (ROOT / "rules" / "fabric-1.21.1" / "shulker-nbt.json").read_text(encoding="utf-8", errors="replace")
    p186_ok = (p186_result.get("sbt_seen") and p186_result.get("container")
               and "method_59714" in p186_wrapper
               and "shulker.legacy.get-nbt" in shulker_rule
               and "shulker.legacy.set-nbt" in shulker_rule)
    check("SBT grid preview reaches the tooltip with component wrapper and t2/t4 bridges", p186_ok,
          "p186 SBT_WRAP show=true nonAir=1 + wrapper/rule sources")
    p187_result = json.loads((ROOT / "runs" / "p187-grid-draw-probe" / "result.json").read_text(encoding="utf-8"))
    p187_markers = p187_result.get("grid_markers", {})
    p187_provider = (ROOT / "java" / "src" / "shulkerpreview" / "java" / "mcbridgepreview"
                     / "ComponentPreviewProvider.java").read_text(encoding="utf-8", errors="replace")
    p187_bridge = (ROOT / "java" / "src" / "bridge" / "java" / "top" / "mcbridge1201" / "bridge"
                   / "ShulkerBoxNbtBridge.java").read_text(encoding="utf-8", errors="replace")
    p187_ok = (p187_markers.get("drawitems", 0) > 0
               and p187_markers.get("drawitem", 0) > 0
               and p187_markers.get("serverbox", 0) > 0
               and "diamondx5" in p187_result.get("drawitems_line", "")
               and "method_57353().method_57829" in p187_provider
               and "method_57379(class_9334" not in p187_bridge
               and "method_57353().method_57829" in p187_bridge)
    check("SBT grid draws item icons and serves the server-synced box (set-as-get fixed)", p187_ok,
          "p187 drawitems/drawitem/serverbox markers + component reads via getComponents().get")
    p188_result = json.loads((ROOT / "runs" / "p188-atlas-overflow" / "result.json").read_text(encoding="utf-8"))
    p188_log = (ROOT / "runs" / "p188-atlas-overflow" / "client.log").read_text(encoding="utf-8", errors="replace")
    p188_ok = (p188_result.get("joined") and p188_result.get("exit_seen")
               and not p188_result.get("errors") and not p188_result.get("crash")
               and p188_log.count("map-atlas create id=1") == 1
               and "map-atlas assign map=1025 packed=65536" in p188_log
               and "map-atlas bind map=map/1025 texture=immediatelyfast:map_atlas/1" in p188_log
               and "atlas1-pixel-check mismatches=0" in p188_log
               and "map-atlas clear atlases=2" in p188_log)
    check("map atlas overflow creates the second atlas, encodes tiles and cleans up both", p188_ok,
          "p188 create id=1 exactly once, packed 65536, bind map_atlas/1, pixel-check 0, clear atlases=2")
    p189_result = json.loads((ROOT / "runs" / "p189-trash-creative" / "result.json").read_text(encoding="utf-8"))
    p189_server = (ROOT / "runs" / "p189-trash-creative" / "server.log").read_text(encoding="utf-8", errors="replace")
    p189_fix = (ROOT / "java" / "src" / "trashcreative" / "java" / "mcbridgecreative"
                / "TrashSlotCreativeFixMixin.java").read_text(encoding="utf-8", errors="replace")
    p189_ok = (p189_result.get("creative_delete_seen", 0) >= 2
               and p189_result.get("delete_all_seen")
               and any(d.startswith("slot=36 all=true") for d in p189_result.get("server_deletes", []))
               and p189_server.count("menu=class_1723") >= 4
               and "class_481" in p189_fix and "callIsHovering" in p189_fix)
    check("TRASH creative delete keys work via the 1.21.1 companion (hover null upstream)", p189_ok,
          "p189 creative delete + delete_all on the InventoryMenu + companion source")
    p190_result = json.loads((ROOT / "runs" / "p190-trash-multi" / "result.json").read_text(encoding="utf-8"))
    p190_server = (ROOT / "runs" / "p190-trash-multi" / "server.log").read_text(encoding="utf-8", errors="replace")
    a_states = p190_result.get("a_server_states", [])
    p190_ok = (p190_result.get("a_took_one") and p190_result.get("a_emptied")
               and p190_result.get("b_server_constant_diamondx3")
               and p190_result.get("b_client_constant_diamondx3")
               and p190_server.count("MULTI_SEED") == 1
               and any("trash=minecraft:diamondx4" in s for s in a_states)
               and a_states and "trash=empty" in a_states[-1])
    check("TRASH multi-client: per-player isolation with A draining and B untouched", p190_ok,
          "p190 A 5->4->empty while B server/client stay constant")
    p191_result = json.loads((ROOT / "runs" / "p191-trash-residual" / "result.json").read_text(encoding="utf-8"))
    p191_server = (ROOT / "runs" / "p191-trash-residual" / "server.log").read_text(encoding="utf-8", errors="replace")
    p191_client = (ROOT / "runs" / "p191-trash-residual" / "client.log").read_text(encoding="utf-8", errors="replace")
    p191_companion = (ROOT / "java" / "src" / "trashcreative" / "java" / "mcbridgecreative"
                      / "TrashSlotCreativeFixMixin.java").read_text(encoding="utf-8", errors="replace")
    p191_ok = (p191_result.get("main_inv_deleted") and p191_result.get("list_ignored")
               and any(d.startswith("slot=18 ") for d in p191_result.get("server_deletes", []))
               and "class_484" in p191_companion
               and "RES_CANVAS trashComponent=null" in p191_client)
    check("TRASH creative inventory tab: main slots delete, list slots are upstream-ignored", p191_ok,
          "p191 SERVER_DELETE slot=18 + list no-op + companion class_484 identity mapping")
    p192_result = json.loads((ROOT / "runs" / "p192-trash-multi-active" / "result.json").read_text(encoding="utf-8"))
    p192_server = (ROOT / "runs" / "p192-trash-multi-active" / "server.log").read_text(encoding="utf-8", errors="replace")
    p192_ok = (p192_result.get("b_took_one") and p192_result.get("b_emptied")
               and p192_result.get("c_constant") and p192_result.get("c_client_untouched")
               and p192_result.get("a_had_five") and p192_result.get("a_rejoined")
               and p192_result.get("a_reset_after_rejoin")
               and p192_server.count("ACTIVE_SEED") == 1)
    check("TRASH three clients: B drains its own trash, C untouched, A rejoin resets (upstream)", p192_ok,
          "p192 B 4->3->empty, C constant, A rejoin trash=empty after diamondx5")
    p193_result = json.loads((ROOT / "runs" / "p193-shulker-grid-residual" / "result.json").read_text(encoding="utf-8"))
    p193_client = (ROOT / "runs" / "p193-shulker-grid-residual" / "client.log").read_text(encoding="utf-8", errors="replace")
    p193_server = (ROOT / "runs" / "p193-shulker-grid-residual" / "server.log").read_text(encoding="utf-8", errors="replace")
    p193_ok = (p193_result.get("client_multi_items2") and p193_result.get("full_render")
               and p193_result.get("server_multi_items2") and p193_result.get("real_hover_path")
               and "type=FULL" in p193_client
               and "first=minecraft:diamondx3" in p193_client
               and "first=minecraft:emeraldx4" in p193_client
               and "DRAWTOOLTIP" in p193_client and "PreviewTooltipData" in p193_client
               and "P193_SERVER_AIM" in p193_client
               and "P193_BOX_SLOT listPos=10" in p193_client
               and "Replaced a slot" in p193_server
               and "minecraft:emerald" in p193_server and "count: 4" in p193_server)
    check("SBT grid residuals: multi-item, FULL, real mouse hover and server box", p193_ok,
          "p193 4/4 flags + client/server markers")
    p194_result = json.loads((ROOT / "runs" / "p194-atlas-third" / "result.json").read_text(encoding="utf-8"))
    p194_log = (ROOT / "runs" / "p194-atlas-third" / "client.log").read_text(encoding="utf-8", errors="replace")
    p194_ok = (p194_result.get("joined") and p194_result.get("logs_ok")
               and p194_result.get("exit_seen") and p194_result.get("required_maps_ok")
               and p194_result.get("map_world_rendered")
               and not p194_result.get("errors") and not p194_result.get("crash")
               and p194_log.count("map-atlas create id=2") == 1
               and "map-atlas assign map=2049 packed=131072" in p194_log
               and "map-atlas assign map=2050 packed=131328" in p194_log
               and "map-atlas bind map=map/2049 texture=immediatelyfast:map_atlas/2" in p194_log
               and "atlas1-pixel-check mismatches=0" in p194_log
               and "atlas2-pixel-check mismatches=0" in p194_log
               and "map-atlas clear atlases=3" in p194_log)
    check("map atlas third: 2048+ maps, atlas 2, cross-atlas frame, cleanup", p194_ok,
          "p194 create id=2 once, packed 131072/131328, bind /2, pixel 0/0, clear atlases=3")
    p195 = json.loads((ROOT / "runs" / "p195-delivery-validation" / "result.json").read_text(encoding="utf-8"))
    p195_portable = (ROOT / "runs" / "p195-delivery-validation" / "portable-test.log").read_text(encoding="utf-8", errors="replace")
    p195_ok = (p195.get("portable", {}).get("ok") and "RESULT: OK" in p195_portable
               and p195.get("panel_smoke", {}).get("ok")
               and (ROOT / "runs" / "p195-delivery-validation" / "panel-smoke.png").exists()
               and p195.get("panel_smoke", {}).get("versions", 0) >= 100
               and p195.get("panel_smoke", {}).get("pcl2_auto_detect") is False
               and p195.get("pcl2_present") is False
               and p195.get("panel_asset", {}).get("complete") is False)
    check("p195 delivery: v0.5.6 portable fresh root OK + panel smoke (PCL2 absent)", p195_ok,
          "p195 portable RESULT OK + panel 103 versions + PCL2/asset boundaries")
    p196_result = json.loads((ROOT / "runs" / "p196-shulker-grid27" / "result.json").read_text(encoding="utf-8"))
    p196_client = (ROOT / "runs" / "p196-shulker-grid27" / "client.log").read_text(encoding="utf-8", errors="replace")
    p196_ok = (p196_result.get("client_multi_items2") and p196_result.get("full_render")
               and p196_result.get("server_multi_items2") and p196_result.get("real_hover_path")
               and "items=27" in p196_client
               and "type=FULL" in p196_client
               and "P196_CLIENT_BOX slot=9 27x" in p196_client
               and "P196_SERVER_AIM" in p196_client)
    check("p196 shulker grid 27-slot full grid", p196_ok,
          "p196 items=27 + FULL + server box + real hover")
    p197_result = json.loads((ROOT / "runs" / "p197-preview-key" / "result.json").read_text(encoding="utf-8"))
    p197_client = (ROOT / "runs" / "p197-preview-key" / "client.log").read_text(encoding="utf-8", errors="replace")
    p197_ok = (p197_result.get("config_rebound") and p197_result.get("keys_transitions")
               and p197_result.get("compact_on_j") and p197_result.get("full_on_jk")
               and p197_result.get("compact_after_k")
               and p197_result.get("no_preview_after_release")
               and p197_result.get("real_hover_path")
               and "previewCode=74" in p197_client and "fullCode=75" in p197_client
               and "P197_TYPE FULL" in p197_client
               and "GRID_DRAWITEMS" in p197_client and "items=27" in p197_client)
    check("p197 shulker preview keys rebound via config (J/K)", p197_ok,
          "p197 config 74/75 + COMPACT/FULL/COMPACT/NO_PREVIEW + 27 items")
    import subprocess
    pcl_readme = (ROOT / "share" / "pcl-onclick" / "README.md").read_text(encoding="utf-8", errors="replace")
    pcl_panel = (ROOT / "tools" / "pcl_panel.py").read_text(encoding="utf-8", errors="replace")
    pcl_install = (ROOT / "tools" / "from_source_install.py").read_text(encoding="utf-8", errors="replace")
    pcl_help = subprocess.run([sys.executable, str(ROOT / "tools" / "from_source_install.py"), "--help"],
                              capture_output=True, text=True, timeout=60)
    pcl_ok = ("mcbridge-pcl-panel.exe" in pcl_readme and "mcbridge-pcl-setup.exe" in pcl_readme
              and "ttk.Combobox" in pcl_panel and "ttk.Progressbar" in pcl_panel
              and "detect_pcl_root" in pcl_panel
              and "--version-type" in pcl_install and "latest-snapshot" in pcl_install
              and pcl_help.returncode == 0
              and "--version-type" in pcl_help.stdout and "--list" in pcl_help.stdout)
    check("PCL one-click panel/version picker contract", pcl_ok,
          f"help rc={pcl_help.returncode}")
    mlaunch_src = (ROOT / "launcher" / "mclaunch.py").read_text(encoding="utf-8", errors="replace")
    path_fix = "sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))"
    portable_ok = (path_fix in mlaunch_src
                   and mlaunch_src.index(path_fix) < mlaunch_src.index("import fetch"))
    check("PORTABLE mclaunch puts its directory on sys.path before importing fetch", portable_ok,
          "embedded CPython ._pth does not add the script directory")


def test_text_encoding_guard() -> None:
    """The docs must stay clean UTF-8: no GBK double-encoding, no '?' artifacts.

    Guards against the p195 corruption (UTF-8 bytes read as cp936 and re-saved)
    re-entering the repository through a future save with the wrong codec.
    """
    guard = ROOT / "tools" / "check_text_encoding.py"
    check("encoding guard present", guard.exists(), str(guard))
    if not guard.exists():
        return
    rc, out = run([sys.executable, "-B", str(guard)])
    check("encoding guard: tracked docs clean", rc == 0,
          out.strip().splitlines()[-1] if out.strip() else f"rc={rc}")

    tmp = WORK / "encoding-guard"
    tmp.mkdir(parents=True, exist_ok=True)
    original = (
        "# 标题（2026-10-28）\n"
        "\n"
        "正文说明，使用 `code` 与 [链接](x.md)，以及 10 份样本。\n"
    )
    good = tmp / "good.md"
    good.write_text(original, encoding="utf-8")
    rc, out = run([sys.executable, "-B", str(guard), str(good)])
    check("encoding guard: clean sample passes", rc == 0, out[-200:])

    # the exact damage: UTF-8 bytes decoded as cp936 with '?' fallback, re-saved
    raw = original.encode("utf-8")
    damaged = []
    i = 0
    while i < len(raw):
        c = raw[i]
        if c < 0x80:
            damaged.append(chr(c))
            i += 1
        elif i + 1 < len(raw) and 0x40 <= raw[i + 1] <= 0xFE and raw[i + 1] != 0x7F:
            pair = bytes(raw[i:i + 2])
            try:
                damaged.append(pair.decode("gbk"))
            except UnicodeDecodeError:
                damaged.append("?")
            i += 2
        else:
            damaged.append("?")
            i += 1
    bad = tmp / "bad.md"
    bad.write_text("".join(damaged), encoding="utf-8")
    rc, out = run([sys.executable, "-B", str(guard), str(bad)])
    lines = [l for l in out.strip().splitlines() if ": " in l]
    check("encoding guard: corrupted sample fails", rc == 1,
          out.strip().splitlines()[-1] if out.strip() else f"rc={rc}")
    check("encoding guard: corrupted sample reports findings", len(lines) >= 1,
          lines[0] if lines else "no findings")

    # the escaped-control-character family: a writer that interprets the two-character
    # sequences instead of keeping the letters turns "tools/" into TAB+"ools/" and splits
    # "(runs/" into "(CRuns/". Both were really in docs/remaining-work.md. A TAB inside a
    # ``` fence stays legal, so the guard must not fire there.
    ctl = tmp / "control.md"
    ctl.write_bytes(
        "- 见 \tools/pcl_panel.py 的用法\r\n"
        "- 证据 (\runs/p195-delivery-validation/)\r\n"
        "```\n\tindented code keeps its tab\n```\n".encode("utf-8"))
    rc, out = run([sys.executable, "-B", str(guard), str(ctl)])
    check("encoding guard: escaped TAB/CR damage fails", rc == 1,
          out.strip().splitlines()[-1] if out.strip() else f"rc={rc}")
    check("encoding guard: names control-tab and control-cr",
          "control-tab" in out and "control-cr" in out, out[-240:])
    check("encoding guard: TAB inside a code fence is not a finding",
          out.count("control-tab") == 1, f"control-tab hits={out.count('control-tab')}")

    # an exemption may only ever point at a document that still exists, so a renamed or
    # deleted report cannot leave a stale "allow the damage" entry behind
    spec = importlib.util.spec_from_file_location("check_text_encoding", guard)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    stale = [rel for rel in module.EXEMPT if not (ROOT / rel).exists()]
    check("encoding guard: exemption list points at real docs", not stale,
          ", ".join(stale) or f"{len(module.EXEMPT)} entr(ies)")


def test_eol_determinism() -> None:
    """p201: runs/SHA256SUMS.txt must still match after a fresh clone.

    The manifest hashes raw bytes. On this machine core.autocrlf=true and there was
    no .gitattributes, so git rewrote 532 of the 1289 hashed files to CRLF on
    checkout while the worktree here kept LF: check_hashes passed here and would
    fail anywhere else. Two invariants hold the promise up:
      * .gitattributes pins "* -text", so checkout never rewrites bytes;
      * every listed path is tracked and its worktree bytes equal the blob bytes
        (uncommitted edits excepted - those are the author's own work in progress).
    """
    attrs = ROOT / ".gitattributes"
    check("p201: .gitattributes exists", attrs.exists(), str(attrs))
    if attrs.exists():
        rules = [l.strip() for l in attrs.read_text(encoding="utf-8").splitlines()
                 if l.strip() and not l.strip().startswith("#")]
        pinned = [r for r in rules if r.split()[0] == "*" and "-text" in r.split()[1:]]
        check("p201: pins * -text so checkout never rewrites bytes",
              bool(pinned), str(rules[:3]))

    audit = ROOT / "runs" / "p201-eol-determinism" / "audit_eol.py"
    check("p201: audit script present", audit.exists(), str(audit))
    if not audit.exists():
        return
    rc, out = run([sys.executable, "-B", str(audit), "--json"])
    try:
        data = json.loads(out)
    except ValueError:
        check("p201: audit produced json", False, out[-200:])
        return
    check("p201: audit read the whole manifest", data.get("total", 0) > 1000,
          str(data.get("total")))

    # porcelain -z: "XY path\0" - a path with uncommitted work is allowed to differ
    proc_status = run(["git", "status", "--porcelain", "-z"])[1]
    dirty = {e[3:] for e in proc_status.split("\0") if len(e) > 3}
    unexpected = [p for p in data.get("drifted", []) if p not in dirty]
    check("p201: every hashed file's bytes survive a checkout", not unexpected,
          ", ".join(unexpected[:5]) or f"{len(data.get('drifted', []))} drifted, all uncommitted")
    check("p201: no hashed path is untracked (a clean clone must be able to check it)",
          not data.get("missing_or_untracked"),
          ", ".join(data.get("missing_or_untracked") or [])[:200])


def test_download_policy() -> None:
    """Offline checks for the download-source policy (mirrors, retries, checksums)."""
    sys.path.insert(0, str(ROOT / "launcher"))
    try:
        import mclaunch
    except Exception as exc:  # noqa: BLE001
        check("DOWNLOAD import mclaunch", False, str(exc))
        return
    import hashlib
    import shutil
    import urllib.error

    mclaunch._JSON_CACHE.clear()
    mclaunch._SIDECAR_CACHE.clear()
    mclaunch.set_source_mode("auto")
    mclaunch.SOURCE_HEALTH.clear()
    mclaunch.SOURCE_HEALTH_PATH = None
    # fetch uses a urllib3 pool when available, which would bypass with_fake()'s urlopen patch;
    # force the urllib path for deterministic offline checks
    try:
        mclaunch._fetch._POOL = None
        mclaunch._fetch.urllib3 = None
    except Exception:  # noqa: BLE001 - older fetch module without a pool
        pass

    workdir = WORK / "download-policy"
    if workdir.exists():
        shutil.rmtree(workdir)
    workdir.mkdir(parents=True)

    loader_url = ("https://maven.fabricmc.net/net/fabricmc/fabric-loader/0.19.5/"
                  "fabric-loader-0.19.5.jar")
    api_url = ("https://maven.fabricmc.net/net/fabricmc/fabric-api/fabric-api/"
               "0.102.0+1.21.1/fabric-api-0.102.0+1.21.1.jar")
    manifest_url = "https://piston-meta.mojang.com/mc/game/version_manifest_v2.json"
    check("DOWNLOAD fabric-loader has the verified BMCL maven fallback",
          any(u.startswith("https://bmclapi2.bangbang93.com/maven/net/fabricmc/fabric-loader/")
              for u in mclaunch.mirror_urls(loader_url)))
    inter_url = ("https://maven.fabricmc.net/net/fabricmc/intermediary/1.21.1/"
                 "intermediary-1.21.1.jar")
    check("DOWNLOAD intermediary has the verified BMCL maven fallback",
          any(u.startswith("https://bmclapi2.bangbang93.com/maven/net/fabricmc/intermediary/")
              for u in mclaunch.mirror_urls(inter_url)))
    check("DOWNLOAD fabric-api stays official (no verified mirror)",
          len(mclaunch.mirror_urls(api_url)) == 1, str(mclaunch.mirror_urls(api_url)))
    check("DOWNLOAD metadata uses the BMCL meta mirror",
          any(u.startswith("https://bmclapi2.bangbang93.com/mc/game/")
              for u in mclaunch.mirror_urls(manifest_url)))

    class FakeResp:
        status = 200
        headers = {}

        def __init__(self, data: bytes):
            self._data = data
            self._pos = 0

        def close(self):
            return None

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self, n=-1):
            if n is None or n < 0:
                n = len(self._data) - self._pos
            chunk = self._data[self._pos:self._pos + n]
            self._pos += len(chunk)
            return chunk

    orig = mclaunch.urllib.request.urlopen

    def with_fake(fake, fn):
        mclaunch.urllib.request.urlopen = fake
        try:
            return fn()
        finally:
            mclaunch.urllib.request.urlopen = orig

    def url_of(req):
        return req.full_url if hasattr(req, "full_url") else str(req)

    # metadata: official fails, BMCL mirror returns JSON
    def fake_meta(req, timeout=None):
        if "piston-meta.mojang.com" in url_of(req):
            raise urllib.error.URLError("tls timeout")
        return FakeResp(b'{"ok": 1}')

    data = with_fake(fake_meta, lambda: mclaunch.http_json(manifest_url, retries=1, max_age=0,
                                                           hedge_delay=0.1))
    check("DOWNLOAD http_json falls back to the mirror", data == {"ok": 1}, str(data))

    # a slow official host must not block t= mirror: the request is hedged
    def fake_hedge(req, timeout=None):
        if "piston-meta.mojang.com" in url_of(req):
            time.sleep(0.6)
            return FakeResp(b'{"slow": 1}')
        return FakeResp(b'{"fast": 1}')

    hedge_start = time.time()
    hedged = with_fake(fake_hedge, lambda: mclaunch.http_json(
        manifest_url, max_age=0, hedge_delay=0.1))
    hedged_elapsed = time.time() - hedge_start
    check("DOWNLOAD hedges a slow metadata host with the mirror",
          hedged == {"fast": 1} and hedged_elapsed < 0.5,
          f"{hedged_elapsed:.2f}s {hedged}")

    # metadata cache: the second call must not touch the network; max_age=0 bypasses it
    cache_calls = {"n": 0}

    def fake_cached(req, timeout=None):
        cache_calls["n"] += 1
        return FakeResp(b'{"cached": true}')

    cache_url = "https://meta.fabricmc.net/v2/unit-cache-test"
    first = with_fake(fake_cached, lambda: mclaunch.http_json(cache_url, retries=1))
    second = with_fake(fake_cached, lambda: mclaunch.http_json(cache_url, retries=1))
    check("DOWNLOAD caches metadata for the TTL",
          cache_calls["n"] == 1 and first == second == {"cached": True}, str(cache_calls["n"]))
    with_fake(fake_cached, lambda: mclaunch.http_json(cache_url, retries=1, max_age=0))
    check("DOWNLOAD max_age=0 bypasses the metadata cache", cache_calls["n"] == 2,
          str(cache_calls["n"]))

    # 404 is not retried: the mirror is tried immediately
    mclaunch.SOURCE_HEALTH.clear()
    dest = workdir / "asset.bin"
    calls: list[str] = []

    def fake_404(req, timeout=None):
        u = url_of(req)
        calls.append(u)
        if "resources.download.minecraft.net" in u:
            raise urllib.error.HTTPError(u, 404, "Not Found", {}, None)
        return FakeResp(b"payload")

    payload_sha1 = hashlib.sha1(b"payload").hexdigest()
    final = with_fake(fake_404, lambda: mclaunch.download(
        "https://resources.download.minecraft.net/ab/" + "a" * 40, dest,
        sha1=payload_sha1, retries=3))
    check("DOWNLOAD 404 skips to the mirror without retries",
          "bmclapi2.bangbang93.com" in final and dest.read_bytes() == b"payload"
          and len(calls) == 2 and not dest.with_suffix(".bin.part").exists(), str(calls))

    # transient errors are retried on the same source
    mclaunch.SOURCE_HEALTH.clear()
    dest2 = workdir / "retry.bin"
    attempts = {"n": 0}

    def fake_flaky(req, timeout=None):
        if "libraries.minecraft.net" in url_of(req):
            attempts["n"] += 1
            if attempts["n"] < 3:
                raise urllib.error.URLError("timeout")
        return FakeResp(b"x")

    with_fake(fake_flaky, lambda: mclaunch.download(
        "https://libraries.minecraft.net/x/y.jar", dest2, retries=3))
    check("DOWNLOAD retries transient failures", attempts["n"] == 3 and dest2.exists(),
          str(attempts["n"]))

    # checksum mismatch retries, then uses the mirror
    dest3 = workdir / "hash.bin"
    good = b"good"

    def fake_hash(req, timeout=None):
        if "resources.download.minecraft.net" in url_of(req):
            return FakeResp(b"bad")
        return FakeResp(good)

    final3 = with_fake(fake_hash, lambda: mclaunch.download(
        "https://resources.download.minecraft.net/cd/" + "b" * 40, dest3,
        sha1=hashlib.sha1(good).hexdigest(), retries=2))
    check("DOWNLOAD verifies hashes and falls back", dest3.read_bytes() == good
          and "bmclapi2.bangbang93.com" in final3, dest3.read_bytes()[:8].hex())

    # maven sidecar helper (cached after the first successful lookup)
    mclaunch._SIDECAR_CACHE.clear()
    side_calls = {"n": 0}

    def fake_sidecar(req, timeout=None):
        side_calls["n"] += 1
        return FakeResp(b"A" * 40 + b"\n")

    sidecar_url = ("https://maven.fabricmc.net/net/fabricmc/fabric-loader/0.19.5/"
                   "fabric-loader-0.19.5.jar")
    digest = with_fake(fake_sidecar, lambda: mclaunch.sha1_sidecar(sidecar_url))
    again = with_fake(fake_sidecar, lambda: mclaunch.sha1_sidecar(sidecar_url))
    check("DOWNLOAD reads and caches maven sha1 sidecars",
          digest == again == "a" * 40 and side_calls["n"] == 1,
          f"{digest} calls={side_calls['n']}")

    check("DOWNLOAD records the source it actually used",
          any(e.get("mirror") for e in mclaunch.DOWNLOAD_EVENTS),
          str(len(mclaunch.DOWNLOAD_EVENTS)))

    # byte progress + source go through Progress (the GUI shows them)
    prog = mclaunch.Progress()
    dest4 = workdir / "progress.bin"
    with_fake(lambda req, timeout=None: FakeResp(b"abcdef"),
              lambda: mclaunch.download(
                  "https://libraries.minecraft.net/progress.jar", dest4,
                  sha1=hashlib.sha1(b"abcdef").hexdigest(), progress=prog))
    snap = prog.snapshot()
    check("DOWNLOAD reports bytes and source through Progress",
          snap["bytes_done"] == 6 and snap["source"].startswith("https://")
          and isinstance(snap["speed"], (int, float)), str(snap)[:160])

    p2 = mclaunch.Progress()
    p2._last_t = time.time() - 1.0
    p2.add_bytes(1000)
    check("DOWNLOAD Progress computes a transfer speed",
          p2.snapshot()["speed"] > 0, str(p2.snapshot()["speed"]))

    # maven hot path: a local sidecar file must avoid network entirely
    cached_jar = workdir / "cached.jar"
    cached_jar.write_bytes(b"cached")
    cached_jar.with_suffix(".jar.sha1").write_text(
        hashlib.sha1(b"cached").hexdigest() + "\n", encoding="ascii")

    def no_net(req, timeout=None):
        raise AssertionError("network used for a cached maven artifact")

    with_fake(no_net, lambda: mclaunch.download_maven(
        "https://maven.fabricmc.net/unit/cached.jar", cached_jar))
    check("DOWNLOAD maven hot path uses the local sidecar",
          cached_jar.read_bytes() == b"cached")

    # source modes + persisted host health
    backup_mode = mclaunch.SOURCE_MODE
    backup_health = dict(mclaunch.SOURCE_HEALTH)
    backup_path = mclaunch.SOURCE_HEALTH_PATH
    try:
        mclaunch.SOURCE_HEALTH.clear()
        mclaunch.set_source_mode("official")
        check("DOWNLOAD official mode disables mirrors",
              mclaunch.ordered_candidates(loader_url) == [loader_url],
              str(mclaunch.ordered_candidates(loader_url)))
        mclaunch.set_source_mode("mirror")
        mirror_first = mclaunch.ordered_candidates(loader_url)[0]
        check("DOWNLOAD mirror mode puts mirrors first",
              mirror_first.startswith("https://bmclapi2.bangbang93.com/"), mirror_first)
        mclaunch.set_source_mode("auto")
        mclaunch.SOURCE_HEALTH.clear()
        check("DOWNLOAD auto mode starts with the official URL",
              mclaunch.ordered_candidates(loader_url)[0] == loader_url)
        mirror_url = mclaunch.mirror_urls(loader_url)[1]
        mclaunch._record_health(mirror_url, False)
        mclaunch._record_health(mirror_url, False)
        ordered = mclaunch.ordered_candidates(loader_url)
        check("DOWNLOAD a recently failing host is ordered last",
              ordered[0] == loader_url and ordered[-1] == mirror_url, str(ordered))

        health_file = workdir / "health.json"
        mclaunch.SOURCE_HEALTH_PATH = health_file
        mclaunch.SOURCE_HEALTH.clear()
        mclaunch._record_health(mirror_url, False)
        mclaunch.SOURCE_HEALTH.clear()
        loaded = mclaunch.load_source_health(health_file)
        check("DOWNLOAD persists and reloads host health", loaded >= 1
              and "bmclapi2.bangbang93.com" in mclaunch.SOURCE_HEALTH,
              str(mclaunch.SOURCE_HEALTH))

        # canary observations merge into the same cache (failures accumulate, success resets)
        merge_file = workdir / "health-merge.json"
        mclaunch.SOURCE_HEALTH_PATH = merge_file
        mclaunch.SOURCE_HEALTH.clear()
        merge_host = "bmclapi2.bangbang93.com"
        mclaunch.merge_source_health({merge_host: {"ok": False}})
        mclaunch.merge_source_health({merge_host: {"ok": False}})
        fails = mclaunch.SOURCE_HEALTH[merge_host]["fails"]
        mclaunch.merge_source_health({merge_host: {"ok": True}})
        reset = mclaunch.SOURCE_HEALTH[merge_host]["fails"] == 0
        check("DOWNLOAD canary health merges into the cache",
              fails == 2 and reset and merge_file.exists(), f"{fails} {reset}")
    finally:
        mclaunch.SOURCE_HEALTH_PATH = backup_path
        mclaunch.SOURCE_HEALTH.clear()
        mclaunch.SOURCE_HEALTH.update(backup_health)
        mclaunch.set_source_mode(backup_mode)


def test_map_atlas_layout_evidence() -> None:
    """p200: the atlas layout evidence must stay self-consistent.

    The numbers in runs/p200-atlas-layout/README.md are the claim (2050 ids, every one at the slot
    the allocator reported, three 4096^2 images, three maps side by side). This re-derives them
    from the committed log and the screenshot check, so an edited log, a stale screenshot or a
    report that drifted from its own evidence fails here.
    """
    run = ROOT / "runs" / "p200-atlas-layout"
    log = run / "client.log"
    check("p200: client.log present", log.exists(), str(log))
    if not log.exists():
        return
    text = log.read_text(encoding="utf-8", errors="replace")

    m = re.search(r"tile-sweep ids=(\d+) mapping-mismatch=(\d+)"
                  r".*?pixel-verified=(\d+) pixel-mismatch=(\d+)", text)
    check("p200: tile-sweep line present", m is not None, "")
    if m:
        ids, mapping_bad, verified, pixel_bad = (int(g) for g in m.groups())
        check("p200: 2050 ids swept", ids == 2050, str(ids))
        check("p200: every id sits at the expected atlas slot", mapping_bad == 0, str(mapping_bad))
        check("p200: every id verified by its own content",
              verified == ids and pixel_bad == 0, f"{verified}/{ids}, mismatch={pixel_bad}")

    images = re.findall(r"atlas(\d) image 4096x4096 last-pixel-ok=true past-end-throws=true"
                        r" bytes=(\d+)", text)
    check("p200: three 4096^2 atlas images", [i for i, _ in images] == ["0", "1", "2"], str(images))
    check("p200: 192 MiB of atlas images",
          sum(int(b) for _, b in images) == 201326592, str([b for _, b in images]))
    check("p200: all three atlases cleared on exit",
          "map-atlas clear atlases=3" in text, "")
    check("p200: no atlas/GL failure marker",
          not re.search(r"Image is not allocated|OutOfMemoryError|Uncaught exception", text), "")

    layout = run / "layout-check.json"
    check("p200: layout-check.json present", layout.exists(), str(layout))
    if not layout.exists():
        return
    data = json.loads(layout.read_text(encoding="utf-8"))
    check("p200: screenshot check passed", data.get("passed") is True,
          json.dumps(data.get("problems"), ensure_ascii=False)[:160])
    blocks = data.get("blocks") or []
    check("p200: three map blocks on screen", len(blocks) == 3, str(len(blocks)))
    if len(blocks) != 3:
        return
    check("p200: blocks are 128 * guiScale = 256 px",
          all(b.get("w") == 256 and b.get("h") == 256 for b in blocks),
          str([(b.get("w"), b.get("h")) for b in blocks]))
    steps = [blocks[i + 1]["x"] - blocks[i]["x"] for i in range(2)]
    check("p200: blocks spaced by 136 * guiScale = 272 px", steps == [272, 272], str(steps))
    offsets = {tuple(o) for o in (data.get("offsets") or [])}
    check("p200: one window offset for all three blocks", len(offsets) == 1, str(data.get("offsets")))
    check("p200: three distinct block colours",
          len({tuple(b["rgb"]) for b in blocks}) == 3, str([b["rgb"] for b in blocks]))


def _png_size(path: Path) -> tuple[int, int] | None:
    """Width/height straight out of the PNG IHDR, so the check needs no Pillow."""
    try:
        head = path.read_bytes()[:33]
    except OSError:
        return None
    if len(head) < 24 or head[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    return int.from_bytes(head[16:20], "big"), int.from_bytes(head[20:24], "big")


def test_hover_and_heterogeneous_nbt() -> None:
    """p202: the hover came from the window system, and the 27 slots really differ.

    Every number in runs/p202-hover-nbt/README.md is re-derived here from the committed log,
    harness log, screenshot check and the PNG header. The two claims being guarded:

    * hover: the probe never writes mouse state (its accessors are getters only), so the only way
      P202_HOVER_OK can name slot 10 with keysSent=false is that a real cursor position arrived
      through GLFW -> Mouse -> Screen.render -> focusedSlot;
    * heterogeneity: 27 stacks with 27 different component maps, 27 grid indices drawn, 27
      different cell images.
    """
    run = ROOT / "runs" / "p202-hover-nbt"
    log_path = run / "client.log"
    check("p202: client.log present", log_path.exists(), str(log_path))
    if not log_path.exists():
        return
    text = log_path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()

    # --- the hover
    hover = [ln for ln in lines if "P202_HOVER_OK" in ln]
    check("p202: slot 10 reported hovered", len(hover) == 1, f"{len(hover)} lines")
    if hover:
        match = re.search(r"index=(-?\d+)", hover[0])
        check("p202: the hovered slot is inventory slot 10",
              match is not None and int(match.group(1)) == 10,
              match.group(1) if match else "no index")
        check("p202: no synthetic key was held when the hover appeared",
              "keysSent=false" in hover[0], hover[0][-80:])
        values = dict(re.findall(r"(glfw|raw|mouse|target)=([\d.]+,[\d.]+)", hover[0]))
        check("p202: glfw/raw/mouse/target all agree", len(set(values.values())) == 1
              and len(values) == 4, str(values))
    check("p202: the probe never needed its glfwSetCursorPos fallback",
          "P202_FALLBACK tick=" not in text, "")

    # --- the cursor was moved from outside the process
    harness_path = run / "harness.log"
    check("p202: harness.log present", harness_path.exists(), str(harness_path))
    moves = [ln for ln in harness_path.read_text(encoding="utf-8", errors="replace").splitlines()
             if ln.startswith("OSMOVE")] if harness_path.exists() else []
    check("p202: three OS cursor moves were issued", len(moves) == 3, str(len(moves)))
    if moves:
        check("p202: every move was accepted by the OS",
              all("accepted=1" in ln for ln in moves), moves[0][-60:])
        check("p202: the point under the cursor was the game window",
              all("underIsGame=True" in ln for ln in moves), "")
        check("p202: the first two moves injected input rather than warping",
              "mechanism=sendinput" in moves[0] and "mechanism=sendinput" in moves[1], moves[0])
        target = re.search(r"P202_TARGET gx=[-\d.]+ gy=[-\d.]+ scale=[-\d.]+ "
                           r"winx=([\d.]+) winy=([\d.]+)", text)
        requested = re.search(r"targetWin=\(([\d.]+),([\d.]+)\)", moves[0])
        check("p202: the harness moved to the coordinates the probe announced",
              target is not None and requested is not None
              and target.groups() == requested.groups(),
              f"{target.groups() if target else None} vs {requested.groups() if requested else None}")

    window = re.search(r"P202_WINDOW handle=\d+ m4480=(\d+) m4486=(\d+) m4502=(\d+) m4507=(\d+)",
                       text)
    check("p202: the game window is 1280x720 with guiScale 2",
          window is not None and (int(window.group(1)), int(window.group(4))) == (1280, 720)
          and (int(window.group(2)), int(window.group(3))) == (640, 360),
          window.groups() if window else "missing")

    # --- 27 heterogeneous stacks, read back on the client
    nbt = [ln for ln in lines if "P202_NBT seq=" in ln]
    check("p202: 27 stacks were read out of the synced box", len(nbt) == 27, str(len(nbt)))
    names = {m.group(1) for ln in nbt if (m := re.search(r"name=(\S+)", ln))}
    items = {m.group(1) for ln in nbt if (m := re.search(r"item=(minecraft:[a-z_]+)", ln))}
    check("p202: all 27 custom names differ", len(names) == 27, str(len(names)))
    check("p202: all 27 item ids differ", len(items) == 27, str(len(items)))
    summary = next((ln for ln in lines if "P202_NBT_SUM" in ln), "")
    check("p202: the probe's own component count agrees",
          "stacks=27 distinctComponents=27 distinctItems=27 distinctNames=27" in summary,
          summary[-80:])

    # --- what reached the renderer
    draws = [ln for ln in lines if "P202_DRAWITEM call=" in ln]
    indices = {int(m.group(1)) for ln in draws if (m := re.search(r"index=(-?\d+)", ln))}
    payloads = {ln.split("comps=", 1)[1] for ln in draws if "comps=" in ln}
    check("p202: every cell 0..26 was drawn", set(range(27)) <= indices, str(sorted(indices)))
    check("p202: 27 different payloads reached the renderer", len(payloads) == 27,
          str(len(payloads)))
    check("p202: FULL drew 27 items", "type=FULL items=27" in text, "")

    # --- the screenshot check, and the screenshot it describes
    grid_path = run / "grid-check.json"
    check("p202: grid-check.json present", grid_path.exists(), str(grid_path))
    if not grid_path.exists():
        return
    grid = json.loads(grid_path.read_text(encoding="utf-8"))
    check("p202: the committed grid check passed", grid.get("passed") is True,
          str(grid.get("checks")))
    cell = grid.get("cell_size")
    check("p202: the measured pitch is exactly one cell, in both axes",
          cell == 36 and grid.get("pitch", {}).get("columns") == cell
          and grid.get("pitch", {}).get("rows") == cell, str(grid.get("pitch")))
    check("p202: 27 different cells, none blank", grid.get("distinct_cells") == 27
          and grid.get("blank_cells") == 0,
          f"{grid.get('distinct_cells')} distinct / {grid.get('blank_cells')} blank")
    origin, base = grid.get("lattice_origin") or [0, 0], grid.get("base_origin") or [0, 0]
    check("p202: the lattice sits within one cell of the panel origin the probe logged",
          all(abs(o - b) < cell for o, b in zip(origin, base)), f"{origin} vs {base}")
    size = _png_size(run / "after-full.png")
    probe = grid.get("probe", {})
    check("p202: the PNG in the repo is the one the check described",
          size is not None and list(size) == grid.get("image_size"),
          f"{size} vs {grid.get('image_size')}")
    frame = grid.get("frame_offset") or [0, 0]
    if size and probe:
        # PrintWindow adds an 8 px border on left/right/bottom and a 31 px title bar on top, so the
        # extra width is 2*frame_x and the extra height is frame_x + frame_y (bottom = side border)
        check("p202: client area + frame accounts for the PNG size",
              size[0] - probe.get("client_w", 0) == round(2 * frame[0])
              and size[1] - probe.get("client_h", 0) == round(frame[0] + frame[1]),
              f"{size} frame={frame}")

    # --- the result flags, and the control that corrected the earlier claim
    result = json.loads((run / "result.json").read_text(encoding="utf-8"))
    check("p202: hover came from the OS cursor, not the fallback",
          result.get("os_cursor_hover") is True and result.get("glfw_cursor_fallback") is False,
          str(result.get("os_cursor_hover")))
    check("p202: the box was placed with per-slot components (not the plain fallback)",
          result.get("box_mode") == "rich", str(result.get("box_mode")))
    control_path = run / "repeat" / "run3-control-warp.log"
    check("p202: control log present", control_path.exists(), str(control_path))
    if control_path.exists():
        control = control_path.read_text(encoding="utf-8", errors="replace")
        check("p202: control (SetCursorPos only, window raised) also hovered",
              "P202_HOVER_OK" in control and "P202_FALLBACK tick=" not in control, "")
        check("p202: the control used only the pointer warp",
              "mechanism=sendinput" not in control and "mechanism=setcursorpos" in control, "")


def test_trash_concurrent_same_tick() -> None:
    """p203: two players' trash writes landed in the same server tick, and stayed apart.

    The claim is a server-side statement, so everything is recomputed from server.log: the tick
    number is the probe's own counter (incremented at the end of every server tick), and the write
    is stamped at TrashHelper.setTrashItem, the only place the per-player value changes. Client
    logs are used only for the fire instant and for what each client shows afterwards.
    """
    run = ROOT / "runs" / "p203-trash-concurrent"
    server_path = run / "server.log"
    check("p203: server.log present", server_path.exists(), str(server_path))
    if not server_path.exists():
        return
    server = server_path.read_text(encoding="utf-8", errors="replace")

    sets = []
    for line in server.splitlines():
        match = re.search(r"P203_SET side=(\S+) thread=(.+?) tick=(-?\d+) wall=(\d+) "
                          r"seeding=(\w+) user=(\S+) stack=(\S+)", line)
        if match:
            sets.append({"side": match.group(1), "thread": match.group(2),
                         "tick": int(match.group(3)), "wall": int(match.group(4)),
                         "seeding": match.group(5), "user": match.group(6),
                         "stack": match.group(7)})
    seeds = [s for s in sets if s["seeding"] == "true"]
    writes = [s for s in sets if s["seeding"] == "false"]
    check("p203: the probe's own seed is stamped and marked", len(seeds) == 2, str(len(seeds)))
    check("p203: the seed wrote 5 and 4 diamonds",
          sorted(s["stack"] for s in seeds)
          == ["minecraft:diamondx4", "minecraft:diamondx5"],
          str([s["stack"] for s in seeds]))
    check("p203: joins reset the trash to empty before any player action",
          [s["stack"] for s in writes if s["wall"] < (seeds[0]["wall"] if seeds else 0)]
          == ["empty", "empty"], str([s["stack"] for s in writes]))

    result = json.loads((run / "result.json").read_text(encoding="utf-8"))
    fire = result.get("fire_instant_ms")
    check("p203: result.json carries the shared fire instant", isinstance(fire, int), str(fire))
    if not isinstance(fire, int):
        return
    window = [s for s in writes if fire - 500 <= s["wall"] <= fire + 5000]
    by_user = {s["user"]: s for s in window}
    check("p203: both players wrote inside the fire window", len(by_user) == 2, str(sorted(by_user)))
    if len(by_user) != 2:
        return
    left, right = by_user.get("GridUser"), by_user.get("TrashB")
    check("p203: the two writes carry the same server tick",
          left is not None and right is not None and left["tick"] == right["tick"],
          f"{left and left['tick']} vs {right and right['tick']}")
    check("p203: both writes happened on the server thread",
          all(s["thread"] == "Server thread" for s in window),
          str([s["thread"] for s in window]))
    check("p203: the two writes are milliseconds apart, not ticks",
          left is not None and right is not None and abs(left["wall"] - right["wall"]) < 50,
          str(abs(left["wall"] - right["wall"]) if left and right else None))
    check("p203: the delete wrote empty and the right-click wrote three",
          left is not None and right is not None and left["stack"] == "empty"
          and right["stack"] == "minecraft:diamondx3",
          f"{left and left['stack']} / {right and right['stack']}")

    stamps = [ln for ln in server.splitlines() if "P203_S2C" in ln
              and "wall=" in ln and fire - 500 <= int(ln.split("wall=")[1].split()[0]) <= fire + 5000]
    check("p203: two serverbound messages were stamped in that window", len(stamps) == 2,
          str(len(stamps)))
    if len(stamps) == 2:
        ticks = {int(ln.split("tick=")[1].split()[0]) for ln in stamps}
        check("p203: the packets arrived in the same tick as the writes",
              ticks == {left["tick"]}, str(ticks))
        check("p203: the two actions use different messages",
              "MessageDeleteFromSlot" in stamps[0] and "MessageTrashSlotClick" in stamps[1]
              or "MessageDeleteFromSlot" in stamps[1] and "MessageTrashSlotClick" in stamps[0],
              " / ".join(ln.rsplit("message=", 1)[-1] for ln in stamps))

    states = {}
    for line in server.splitlines():
        match = re.search(r"P203_SERVER tick=(\d+) user=(\S+) trash=(\S+)", line)
        if match:
            states.setdefault(match.group(2), []).append((int(match.group(1)), match.group(3)))
    last_a = states.get("GridUser", [(-1, "")])[-1]
    last_b = states.get("TrashB", [(-1, "")])[-1]
    check("p203: the server ends with A empty and B holding three",
          last_a[1] == "empty" and last_b[1] == "minecraft:diamondx3",
          f"{last_a} / {last_b}")
    before = [t for t, v in states.get("GridUser", []) if v == "minecraft:diamondx5"]
    check("p203: A really held five before the action", bool(before), str(len(before)))
    check("p203: both states were re-read after the write",
          last_a[0] > left["tick"] and last_b[0] > right["tick"],
          f"{last_a[0]} / {last_b[0]} after tick {left['tick']}")

    for role, expect in (("a", "trash=empty"), ("b", "trash=minecraft:diamondx3")):
        path = run / f"client-{role}.log"
        check(f"p203: client-{role}.log present", path.exists(), str(path))
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        fire_line = [ln for ln in text.splitlines() if "P203_FIRE" in ln]
        check(f"p203: client {role.upper()} fired on the shared instant",
              len(fire_line) == 1 and f"epochMs={fire}" in fire_line[0]
              and "driftMs=0" in fire_line[0], fire_line[0][-60:] if fire_line else "none")
        check(f"p203: client {role.upper()} shows its own result",
              any(expect in ln for ln in text.splitlines() if f"P203_TRASH role={role.upper()}" in ln),
              "")
    b_log = (run / "client-b.log").read_text(encoding="utf-8", errors="replace")
    check("p203: B's cursor holds exactly one diamond",
          any("carried=minecraft:diamondx1" in ln for ln in b_log.splitlines()
              if "P203_TRASH role=B" in ln), "")

    checks = result.get("checks", {})
    check("p203: every recorded check is true",
          bool(checks) and all(checks.values()), str(checks))

    repeat_path = run / "repeat" / "round1-server.log"
    check("p203: round1 server log present", repeat_path.exists(), str(repeat_path))
    if repeat_path.exists():
        repeat = repeat_path.read_text(encoding="utf-8", errors="replace")
        ticks: dict[int, set[str]] = {}
        for line in repeat.splitlines():
            match = re.search(r"P203_SET side=SERVER thread=Server thread tick=(-?\d+) "
                              r"wall=\d+ seeding=false user=(\S+) stack=\S+", line)
            if match:
                ticks.setdefault(int(match.group(1)), set()).add(match.group(2))
        shared = sorted(t for t, users in ticks.items() if len(users) == 2)
        check("p203: an independent earlier round also shared one tick",
              bool(shared), f"ticks={shared} all={sorted(ticks)}")


def test_cross_platform_delivery() -> None:
    """p208: the shipped package in a scrubbed environment, and the platform audit.

    Every number here is recomputed from the evidence files or from the code, so a
    changed claim without a changed measurement fails.
    """
    run = ROOT / "runs" / "p208-cross-platform"

    def load(name: str):
        path = run / name
        if not path.exists():
            check(f"p208: {name} present", False, str(path))
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    before = load("behaviour-before.json")
    after = load("behaviour-after.json")
    audit_before = load("audit-before.json")
    audit_after = load("audit.json")
    shipped = load("clean-host-shipped.json")
    current = load("clean-host-current.json")
    if not all((before, after, audit_before, audit_after, shipped, current)):
        return

    def probe(doc, name):
        return next((p for p in doc["probes"] if p["name"] == name), {})

    # 1. The failing baseline is kept. Without it "it was broken" is a story.
    check("p208: the pre-fix probe run really failed",
          before["passed"] == 2 and before["total"] == 6,
          f"{before['passed']}/{before['total']}")
    check("p208: every probe passes after the fix",
          after["passed"] == 6 and after["total"] == 6,
          f"{after['passed']}/{after['total']}")

    # 2. Each defect, measured before and after.
    b = probe(before, "default_root_no_appdata")
    a = probe(after, "default_root_no_appdata")
    check("p208: unset APPDATA used to give a relative game root",
          b.get("actual") == ".minecraft" and not b.get("ok"), str(b.get("actual")))
    check("p208: the game root is absolute now",
          bool(a.get("ok")) and Path(a.get("actual", "")).is_absolute(), str(a.get("actual")))

    b = probe(before, "find_java_home_posix")
    a = probe(after, "find_java_home_posix")
    check("p208: JAVA_HOME used to be ignored on POSIX",
          not b.get("ok") and not str(b.get("actual", "")).endswith("bin/java"),
          str(b.get("actual")))
    check("p208: JAVA_HOME's bin/java is used now",
          bool(a.get("ok")) and Path(a.get("actual", "")).name == "java", str(a.get("actual")))

    check("p208: macOS used to be sent to xdg-open",
          probe(before, "open_folder_darwin").get("actual") == "xdg-open", "")
    check("p208: macOS gets open now",
          probe(after, "open_folder_darwin").get("actual") == "open", "")
    check("p208: the linux and windows openers are unchanged",
          all(probe(d, "open_folder_linux").get("ok")
              and probe(d, "open_folder_win32").get("ok")
              for d in (before, after)), "")

    check("p208: the dead Windows java constant was detected",
          not probe(before, "java_fallback_unused").get("ok"), "")
    check("p208: the dead constant is gone",
          bool(probe(after, "java_fallback_unused").get("ok")), "")

    # 3. The audit: fewer hits, and the leftovers are exactly the known ones.
    cb, ca = audit_before["counts"], audit_after["counts"]
    check("p208: the audit found 28 hits with 24 unguarded before",
          cb["delivery_hits"] == 28 and cb["delivery_hits_bare"] == 24,
          f"{cb['delivery_hits']}/{cb['delivery_hits_bare']}")
    check("p208: 22 hits with 4 unguarded after",
          ca["delivery_hits"] == 22 and ca["delivery_hits_bare"] == 4,
          f"{ca['delivery_hits']}/{ca['delivery_hits_bare']}")
    bare = sorted((r["path"], h["code"]) for r in audit_after["static"]
                  if r["kind"] == "delivery" for h in r["hits"] if not h["handled"])
    # Line numbers drift with unrelated edits, so match on file and content instead.
    check("p208: the 4 remaining hits are the known Windows-only packaging spots",
          len(bare) == 4
          and sorted({path for path, _ in bare}) == ["launcher/server.py",
                                                     "tools/build_portable.py",
                                                     "tools/test_portable.py"]
          and all("python.exe" in code or "APPDATA" in code for _, code in bare), str(bare))
    check("p208: all delivery modules import under the posix simulation",
          ca["delivery_modules_ok"] == ca["delivery_modules_imported"] == 4,
          f"{ca['delivery_modules_ok']}/{ca['delivery_modules_imported']}")
    check("p208: the audit states that no POSIX kernel was involved",
          any("POSIX kernel" in c for c in audit_after["caveats"]), "")

    # 4. The scrubbed-environment run: the scrub first, then the package.
    for label, doc in (("shipped", shipped), ("current sources", current)):
        failed = [k for k, v in doc["checks"].items() if not v]
        check(f"p208: clean host ({label}) passes every check",
              doc["passed"] == doc["total"] == 8 and not failed, str(failed))
        check(f"p208: clean host ({label}) proves the scrub removed python and java",
              doc["detail"]["path_lookup"]["python"] is None
              and doc["detail"]["path_lookup"]["java"] is None, "")
        prefix = doc["detail"]["interpreter"]["prefix"]
        check(f"p208: clean host ({label}) ran the bundled interpreter",
              "p208-clean-host" in prefix and "pkg" in prefix, prefix)
        check(f"p208: clean host ({label}) shipped no jar",
              doc["detail"]["package"]["jars"] == [], str(doc["detail"]["package"]["jars"]))
        check(f"p208: clean host ({label}) starts from run.bat only (portable is Windows-only)",
              doc["detail"]["package"]["launchers"] == ["run.bat"],
              str(doc["detail"]["package"]["launchers"]))
        status = doc["detail"]["status"]
        check(f"p208: clean host ({label}) reports an empty root and no JVM, not a crash",
              status["ok"] and status["versions"] == 0 and status["java"] is None
              and bool(status["java_error"]), json.dumps(status, ensure_ascii=False))

    check("p208: the shipped run used the zip's own sources",
          shipped["launcher_sources"].startswith("as shipped"), shipped["launcher_sources"])
    check("p208: the second run overlaid the current sources",
          current["launcher_sources"].startswith("current worktree over"), current["launcher_sources"])
    check("p208: the overlay replaced every launcher module in the package",
          sorted(current["overlaid"]) == ["backend.py", "fetch.py", "mclaunch.py", "server.py"],
          str(current["overlaid"]))
    check("p208: the three files this change touched are among them",
          {"server.py", "mclaunch.py", "backend.py"} <= set(current["overlaid"]), "")

    # 5. The build script refuses to ship a package without its dependencies.
    log = run / "build-blocked.log"
    text = log.read_text(encoding="utf-8", errors="replace") if log.exists() else ""
    check("p208: building without the deps is refused",
          "refusing to build: minecraft_launcher_lib" in text, text[-160:])
    check("p208: the refused build does not print done",
          "done" not in text.splitlines()[-1] if text.strip() else False, "")

    spec = importlib.util.spec_from_file_location("p208_build_portable",
                                                  ROOT / "tools" / "build_portable.py")
    build_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(build_mod)
    raised = False
    try:
        build_mod.require_vendored([], False)
    except RuntimeError:
        raised = True
    check("p208: require_vendored rejects an empty dependency set", raised, "")
    build_mod.require_vendored([build_mod.REQUIRED_DEP], False)
    build_mod.require_vendored([], True)
    check("p208: require_vendored accepts the dep, and the explicit override", True, "")

    # 6. The helpers themselves, on the live modules.
    sys.path.insert(0, str(ROOT / "launcher"))
    import mclaunch  # noqa: E402
    import server  # noqa: E402
    check("p208: the JVM binary name follows the platform",
          mclaunch.java_binary("win32") == "java.exe"
          and mclaunch.java_binary("linux") == "java"
          and mclaunch.java_binary("darwin") == "java", "")

    real_popen = server.subprocess.Popen
    real_startfile = getattr(server.os, "startfile", None)
    try:
        def boom(*a, **kw):
            raise FileNotFoundError("xdg-open")
        server.subprocess.Popen = boom
        check("p208: a missing opener returns False instead of raising",
              server.open_in_explorer(ROOT, platform="linux") is False, "")
        opened = []
        server.os.startfile = lambda p, *a, **kw: opened.append(p)
        check("p208: Windows still opens through startfile",
              server.open_in_explorer(ROOT, platform="win32") is True and bool(opened), "")
    finally:
        server.subprocess.Popen = real_popen
        if real_startfile is not None:
            server.os.startfile = real_startfile


def test_real_wheel_input() -> None:
    """p204: a real OS wheel and a real keystroke reached the Mod Menu screen.

    The claim is an input claim, so it is re-derived from three independent places instead of
    trusting one:

    * client.log - the scroll amount (read from the widget) after each notch, the per-event
      P204_SCROLL lines logged at Mouse.onMouseScroll, and the chars the focused text field took;
    * harness.log - what was injected, where the cursor was, and whether that point belonged to
      the game window at the time;
    * scroll-check.json - the scrollbar thumb measured off the screenshots, which is the widget's
      own rendering of the same scroll amount.

    Also guarded: the probe must not be able to set the scroll amount at all, the two controls must
    stay clean (no event outside the window, no list movement over the pane), and the Cloth Config
    finding stays on record (its stack trace is the reason that half of the task is not "untested"
    but "unreachable").
    """
    run = ROOT / "runs" / "p204-wheel-input"
    log_path = run / "client.log"
    check("p204: client.log present", log_path.exists(), str(log_path))
    if not log_path.exists():
        return
    text = log_path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()

    # --- the staircase, straight out of the log
    states = [dict(re.findall(r"(\w+)=([^ ]+)", ln.split("P204_SCROLL_STATE ", 1)[1]))
              for ln in lines if "P204_SCROLL_STATE " in ln]
    check("p204: the list state was logged", len(states) >= 11, str(len(states)))
    scrolls = [float(s["scroll"]) for s in states]
    steps = [x for x in scrolls if x > 0]
    check("p204: nine notches stepped by itemHeight/2 = 18",
          steps[:8] == [18.0, 36.0, 54.0, 72.0, 90.0, 108.0, 126.0, 144.0], str(steps[:9]))
    maximum = float(states[0]["max"]) if states else -1
    check("p204: the ninth notch clamped at max scroll", max(scrolls) == maximum == 147.0,
          f"max seen {max(scrolls)} / max_scroll {maximum}")
    check("p204: the list started at 0", scrolls[0] == 0.0, str(scrolls[0]))

    # --- every notch arrived as its own window event
    events = [ln.split("P204_SCROLL ", 1)[1] for ln in lines if "P204_SCROLL n=" in ln]
    dy = [float(re.search(r"dy=(-?[\d.]+)", e).group(1)) for e in events if "dy=" in e]
    # control B's two messages come first (-1 and -8), then one message per notch over the list
    check("p204: the test phase delivered exactly one message per notch",
          dy[-9:] == [-1.0] * 9 and len(dy) == 11, str(dy))
    check("p204: the control and the test account for all 18 wheel units",
          abs(sum(dy) + 18.0) < 1e-9, str(sum(dy)))
    check("p204: no scroll event was delivered as a positive delta",
          all(v <= 0 for v in dy), str(dy))

    # --- the controls
    harness_path = run / "harness.log"
    check("p204: harness.log present", harness_path.exists(), str(harness_path))
    harness = harness_path.read_text(encoding="utf-8", errors="replace") if harness_path.exists() else ""
    control_a = re.search(r"CONTROL_A outside=\(\d+,\s*\d+\) underIsGame=(True|False) accepted=(\d+) "
                          r"scroll ([\d.]+) -> ([\d.]+) eventsDelta=(\d+)", harness)
    check("p204: control A (wheel outside the window) was sent", control_a is not None, "")
    if control_a:
        check("p204: control A pointed outside the game window",
              control_a.group(1) == "False", control_a.group(1))
        check("p204: control A produced no scroll event and no movement",
              control_a.group(5) == "0" and control_a.group(3) == control_a.group(4),
              control_a.group(0)[-60:])
    control_b = re.search(r"CONTROL_B pane=\(\d+,\s*\d+\) accepted=(\d+) "
                          r"scroll ([\d.]+) -> ([\d.]+) eventsDelta=(\d+)", harness)
    check("p204: control B (wheel over the right pane) was sent", control_b is not None, "")
    if control_b:
        check("p204: control B delivered an event but left the list alone",
              int(control_b.group(4)) > 0 and control_b.group(2) == control_b.group(3),
              control_b.group(0)[-60:])
    moves = [ln for ln in harness.splitlines() if ln.startswith("MOVE listCenter")]
    check("p204: the cursor was really over the list for the test phase",
          bool(moves) and all("underIsGame=True" in ln for ln in moves), str(len(moves)))
    check("p204: the game window was the foreground window before typing",
          "ok=True" in harness and "foreground=" in harness, "")

    # --- the keyboard
    chars = [ln.split("P204_CHAR ", 1)[1] for ln in lines if "P204_CHAR n=" in ln]
    typed = "".join(re.search(r"c=(\S)", c).group(1) for c in chars if "c=" in c)
    check("p204: four characters reached the focused text field", len(chars) == 4, str(len(chars)))
    check("p204: the characters are exactly what was typed", typed == "menu", typed)
    final = states[-1] if states else {}
    check("p204: the search box holds the typed text", final.get("text") == '"menu"', str(final))
    check("p204: the list filtered down to one entry",
          final.get("entries") == "1" and final.get("max") == "0",
          f"{final.get('entries')} entries / max {final.get('max')}")
    check("p204: the run ended on its own marker",
          any("P204_DONE" in ln and 'text="menu"' in ln for ln in lines), "")

    # --- what the screenshots say
    check_path = run / "scroll-check.json"
    check("p204: scroll-check.json present", check_path.exists(), str(check_path))
    if check_path.exists():
        visual = json.loads(check_path.read_text(encoding="utf-8"))
        check("p204: the committed screenshot check passed", visual.get("passed") is True,
              str(visual.get("checks")))
        predicted = visual.get("predicted_one_notch_shift")
        measured = visual.get("measured_one_notch_shift")
        check("p204: the scrollbar thumb moved by the predicted 18/147 of the free track",
              predicted is not None and measured is not None and abs(measured - predicted) <= 3,
              f"predicted {predicted} / measured {measured}")
        free = visual.get("free_track_px") or 0
        check("p204: at max scroll the thumb sits at the bottom",
              free and abs((visual.get("measured_full_shift") or 0) - free) <= 3,
              f"{visual.get('measured_full_shift')} vs {free}")
        check("p204: the filtered list no longer draws a scrollbar",
              (visual.get("shots", {}).get("list-filtered", {}).get("has_thumb")) is False, "")

    # --- the probe cannot move the list
    probe_src = ROOT / "probes" / "p204-wheel-input" / "src" / "p204probe"
    sources = {p.name: p.read_text(encoding="utf-8", errors="replace")
               for p in probe_src.rglob("*.java")}
    def stripped(source: str) -> str:
        """Drop comments before looking for a call: the probe's own javadoc says it does NOT
        call setScrollAmount, and a substring search would count that sentence as the call."""
        import re as _re

        without_block = _re.sub(r"/\*.*?\*/", "", source, flags=_re.S)
        return _re.sub(r"//[^\n]*", "", without_block)

    code = "\n".join(stripped(v) for v in sources.values())
    check("p204: the probe never calls setScrollAmount",
          not re.search(r"method_(60321|25307)\s*\(", code)
          and "setScrollAmount(" not in code, str(sorted(sources)))
    accessors = (sources.get("WidgetAccessor.java", "") + sources.get("ListAccessor.java", ""))
    check("p204: the geometry accessors are getters only",
          "@Accessor" in accessors and "p204$set" not in accessors
          and "void p204$" not in accessors, "")

    # --- the repeat run, and the Cloth Config finding
    repeat = run / "repeat" / "result.json"
    check("p204: the independent repeat run is on record", repeat.exists(), str(repeat))
    if repeat.exists():
        again = json.loads(repeat.read_text(encoding="utf-8"))
        check("p204: the repeat passed the same checks",
              all((again.get("checks") or {}).values()) and again.get("passed") is True,
              str(again.get("checks")))
        again_steps = [s["scroll"] for s in again.get("wheel_steps") or []]
        check("p204: the repeat produced the same staircase",
              again_steps[:8] == [18.0, 36.0, 54.0, 72.0, 90.0, 108.0, 126.0, 144.0],
              str(again_steps))
    check("p204: the Cloth Config failure is on record with its frame",
          "ConfigBuilderImpl.<init>" in text
          and "does not have member field 'net.minecraft.class_2960 field_44669'" in text, "")
    check("p204: the Cloth failure is attributed to Mod Menu's config probe",
          "ModsScreen.method_25426" in text and "ModMenu.getConfigScreen" in text, "")


def test_modmenu_rows() -> None:
    """p205: the Mod Menu list really paints rows, and the fix is the entry-call argument order.

    Two things are guarded here. The first is the defect itself: the bridge used to pass
    (context, index, left, top, ...) to Entry.render, whose parameters are (y, x), so every icon and
    name was laid out at the wrong place while the row backdrop - which uses left/top directly -
    still painted. The second is that the claim is measured, not asserted: the numbers come from the
    two committed runs (same client, same mods, same cursor, different bridge) and from the
    screenshot check, not from prose.
    """
    run = ROOT / "runs" / "p205-modmenu-rows"
    bridge_path = (ROOT / "java" / "src" / "bridge" / "java" / "top" / "mcbridge1201" / "bridge"
                   / "ModMenuListRenderBridge.java")
    check("p205: bridge source present", bridge_path.exists(), str(bridge_path))
    if not bridge_path.exists():
        return
    source = bridge_path.read_text(encoding="utf-8")
    code = re.sub(r"//[^\n]*", "", re.sub(r"/\*.*?\*/", "", source, flags=re.S))

    check("p205: the entry call passes y before x",
          len(re.findall(r"entryCall\(entry, \"method_(25343|49568)\", context, i, top, left",
                         code)) == 2,
          str(re.findall(r"entryCall\([^)]*", code)[:2]))
    check("p205: the old swapped order is gone", "context, i, left, top" not in code, "")
    check("p205: the row width comes from getRowWidth (method_25322), not the widget width",
          "method_25322" in code and "method_25368" not in code, "")
    check("p205: the row height is itemHeight - 4 like vanilla",
          "itemHeight - 4" in code, "")
    check("p205: the visibility test uses the widget top and bottom",
          "method_46427" in code and "method_55443" in code, "")
    check("p205: Entry.drawBorder is called before Entry.render", "method_49568" in code, "")
    check("p205: hovered is decided by getEntryAtPosition, not a rectangle guess",
          "method_25308" in code and "isHovered" in code, "")
    # p206 added two more reports (selection change, highlight rectangle), so the invariant is no
    # longer "one println" but "every println sits behind the same flag".
    check("p205: every debug line is behind -Dmcbridge.listrender.debug",
          code.count("System.out") == code.count("if (DEBUG")
          and 'Boolean.getBoolean("mcbridge.listrender.debug")' in code,
          f'{code.count("System.out")} prints vs {code.count("if (DEBUG")} guards')

    # --- the two runs
    checks_path = run / "rows-check.json"
    check("p205: rows-check.json present", checks_path.exists(), str(checks_path))
    if not checks_path.exists():
        return
    report = json.loads(checks_path.read_text(encoding="utf-8"))
    before = report["before"]["before_scroll"]
    after = report["after"]["before_scroll"]
    check("p205: the baseline list is completely blank",
          before["bright"] == 0 and before["saturated"] == 0 and before["icon_bands"] == 0,
          json.dumps(before))
    check("p205: the fixed list shows at least five row icons",
          after["icon_bands"] >= 5, str(after["icon_bands"]))
    check("p205: the fixed list has thousands of legible text pixels",
          after["bright"] > 5000, str(after["bright"]))
    check("p205: the two runs differ only in the bridge (same mods, same window)",
          report["before"]["p205_lines"] == [] and report["after"]["p205_lines"] != [],
          str(report["before"]["p205_lines"]))
    check("p205: the debug line reports ModListWidget with 11 entries and 36 px rows",
          any("class=ModListWidget count=11" in line and "itemHeight=36" in line
              for line in report["after"]["p205_lines"]),
          str(report["after"]["p205_lines"])[:200])
    shift = report["after"]["shift"]
    check("p205: the rows move up by exactly the scroll delta when wheeled",
          shift["best_dy"] == -36 and report["after"]["expected_device_shift"] == 36.0,
          json.dumps(shift))
    check("p205: the blank list has no rows to move",
          report["before"]["before_scroll"]["icon_bands"] == 0, "")
    check("p205: every screenshot check passed",
          report["passed"] is True and all(report["checks"].values()),
          json.dumps({k: v for k, v in report["checks"].items() if not v}))

    # --- the jar that carried the fix
    build_log = run / "build.log"
    check("p205: build.log present", build_log.exists(), str(build_log))
    if build_log.exists():
        text = build_log.read_text(encoding="utf-8", errors="replace")
        before_sha = re.search(r"BEFORE .*sha256=([0-9a-f]{64})", text)
        after_sha = re.search(r"AFTER .*sha256=([0-9a-f]{64})", text)
        check("p205: the injected class is not the old one",
              before_sha and after_sha and before_sha.group(1) != after_sha.group(1),
              f"{before_sha.group(1) if before_sha else None} -> "
              f"{after_sha.group(1) if after_sha else None}")
        check("p205: the build reports the jar it wrote",
              "OUT " in text and "modmenu-rows.jar" in text, "")
    for label in ("before", "after"):
        result_path = run / label / "result.json"
        check(f"p205: {label}/result.json present", result_path.exists(), str(result_path))
        if result_path.exists():
            result = json.loads(result_path.read_text(encoding="utf-8"))
            check(f"p205: {label} ran with the debug flag on the command line",
                  result.get("jvm_flags") == ["-Dmcbridge.listrender.debug=true"],
                  str(result.get("jvm_flags")))

    # --- the launcher had to learn extra_jvm to make that flag reach the JVM
    launcher = ROOT / "launcher" / "mclaunch.py"
    launcher_text = launcher.read_text(encoding="utf-8")
    check("p205: build_command honours extra_jvm in both command paths",
          launcher_text.count('list(extra_jvm or [])') == 2, "")
    client = ROOT / "work" / "launcher-e2e"
    if (client / "versions").exists():
        sys.path.insert(0, str(ROOT / "launcher"))
        import mclaunch  # noqa: PLC0415

        cmd, _, _ = mclaunch.build_command("fabric-loader-0.19.5-1.21.1", client, "RowUser", "2G",
                                           extra_jvm=["-Dmcbridge.listrender.debug=true"])
        check("p205: the flag lands immediately after -Xmx",
              "-Dmcbridge.listrender.debug=true" in cmd
              and cmd.index("-Dmcbridge.listrender.debug=true") == cmd.index("-Xmx2G") + 1,
              str(cmd[:4]))
    else:
        SKIPPED.append("p205 build_command")


def test_modmenu_selection() -> None:
    """p206: a real click selects a row and the bridge now draws a highlight for it.

    Three claims are guarded, and each one is measured rather than asserted:

    * the old jar selects the row too but paints nothing (92 changed pixels, no band);
    * the new jar lights up exactly one row, at the position the row geometry predicts;
    * the description panel is empty because the redirect replaced the method body that *built* the
      description rows - the bytecode evidence for that lives in runs/p206-modmenu-select/bytecode/.
    """
    run = ROOT / "runs" / "p206-modmenu-select"
    bridge_path = (ROOT / "java" / "src" / "bridge" / "java" / "top" / "mcbridge1201" / "bridge"
                   / "ModMenuListRenderBridge.java")
    report_path = run / "highlight-check.json"
    check("p206: the screenshot check is committed", report_path.exists(), str(report_path))
    check("p206: the bridge source is present", bridge_path.exists(), str(bridge_path))
    if not (report_path.exists() and bridge_path.exists()):
        return

    report = json.loads(report_path.read_text(encoding="utf-8"))
    control, fixed = report["control"], report["fix"]
    check("p206: the committed check passed", report.get("passed") is True,
          str(report.get("failed")))

    # --- the two runs really are a matched pair ------------------------------------------------
    p205 = json.loads((ROOT / "runs" / "p205-modmenu-rows" / "after" / "result.json")
                      .read_text(encoding="utf-8"))
    check("p206: the control run is the p205 jar",
          control["jar_sha256"] == p205["modmenu_sha256"],
          f'{control["jar_sha256"][:16]} vs {p205["modmenu_sha256"][:16]}')
    check("p206: the two runs use different jars", control["jar_sha256"] != fixed["jar_sha256"], "")
    check("p206: both runs clicked the same device pixel",
          control["click"]["device"] == fixed["click"]["device"],
          f'{control["click"]["device"]} vs {fixed["click"]["device"]}')

    # --- the defect and the fix, recomputed from the two result.json files ----------------------
    check("p206: the control jar selects the row but reports no selection (it predates the line)",
          control["selection_before"] is None and control["selection_after"] is None,
          str((control["selection_before"], control["selection_after"])))
    check("p206: the fixed jar moved the selection from row 0 to the clicked row",
          (fixed["selection_before"] or {}).get("selected") == 0
          and (fixed["selection_after"] or {}).get("selected") == fixed["click"]["row"],
          str((fixed["selection_before"], fixed["selection_after"])))
    check("p206: the click also gave the list focus",
          (fixed["selection_before"] or {}).get("focused") is False
          and (fixed["selection_after"] or {}).get("focused") is True,
          str(fixed["selection_after"]))

    # --- geometry: where the highlight should be, and where it actually is ---------------------
    geo = fixed["geometry"]
    row = fixed["click"]["row"]
    item = fixed["mod_list"]["itemHeight"]
    list_top = fixed["probe_list"]["gui"][1]
    scale, (_ox, y_off) = geo["scale"], geo["offsets"]
    predicted_top = y_off + int((list_top + row * item - 2) * scale)
    predicted_bottom = y_off + int((list_top + row * item + item - 4 + 2) * scale)
    gained = fixed["gained"]
    lost = fixed["lost"]
    check("p206: the fixed jar changed more pixels than the control",
          fixed["changed_pixels"] > 3 * max(control["changed_pixels"], 1),
          f'{fixed["changed_pixels"]} vs {control["changed_pixels"]}')
    check("p206: the control jar produced no highlight band",
          not control["gained"] and not control["lost"],
          str((control["gained"], control["lost"])))
    check("p206: the fixed jar gained exactly one band and lost exactly one",
          len(gained) == 1 and len(lost) == 1, str((gained, lost)))
    if len(gained) == 1:
        top, bottom = gained[0]
        centre = (top + bottom) / 2
        height = bottom - top + 1
        check("p206: the gained band sits on the clicked row",
              abs(centre - (predicted_top + predicted_bottom) / 2) <= 12,
              f'centre {centre} vs {(predicted_top + predicted_bottom) / 2}')
        check("p206: the gained band is about one row tall",
              abs(height - (predicted_bottom - predicted_top)) <= 16,
              f'height {height} vs {predicted_bottom - predicted_top}')
    check("p206: the lost band sits on row 0, where the selection used to be",
          len(lost) == 1
          and abs((lost[0][0] + lost[0][1]) / 2
                  - (y_off + (list_top + item - 4 - 2) * scale / 2
                     + (list_top - 2) * scale / 2)) <= 12,
          str(lost))

    # --- the bridge draws what it says --------------------------------------------------------
    source = bridge_path.read_text(encoding="utf-8")
    code = re.sub(r"//[^\n]*", "", re.sub(r"/\*.*?\*/", "", source, flags=re.S))
    check("p206: the bridge draws the selection once per selected row",
          len(re.findall(r"drawSelection\(list, context, top, rowWidth, rowHeight,", code)) == 1, "")
    check("p206: the selection colour is the vanilla pair plus a documented wash",
          "0xFFFFFFFF" in code and "0xFF808080" in code and "0xFF000000" in code
          and "0x40FFFFFF" in code, "")
    check("p206: no diagnostic colours were left in the bridge",
          "TEMP" not in code and "FFFF00FF" not in code and "FFFF0000" not in code, "")
    check("p206: the bridge never sets the scroll amount (p204's rule still holds)",
          not re.search(r"method_(60321|25307)\s*\(", code), "")

    # --- why the description panel is empty ---------------------------------------------------
    redirected = (run / "bytecode" / "render-redirected.txt").read_text(encoding="utf-8")
    original = (run / "bytecode" / "render-original.txt").read_text(encoding="utf-8")
    check("p206: the description render is a bare redirect in the patched jar",
          "ModMenuListRenderBridge.renderList" in redirected and "DescriptionEntry" not in redirected,
          "")
    check("p206: the redirect replaced a body that built the description rows",
          original.count("DescriptionEntry") >= 20 and "method_25339" in original
          and original.count("Tombstones_modmenu_7_2_2") >= 4,
          f'{original.count("DescriptionEntry")} constructions, '
          f'{original.count("Tombstones_modmenu_7_2_2")} tombstone sites')
    for label, data in (("control", control), ("fixed", fixed)):
        check(f"p206: the {label} run reports an empty description list on every frame",
              bool(data["description_counts"]) and all(c == 0 for c in data["description_counts"]),
              str(data["description_counts"]))
    check("p206: the check records the empty panel instead of calling it untested",
          report["checks"].get("description_panel_is_empty_in_both_runs") is True, "")

    # --- the harness re-raises instead of quietly clicking into the terminal -------------------
    harness = (run / "run.py").read_text(encoding="utf-8")
    check("p206: the harness retries the window raise and records underIsGame",
          "for attempt in range(1, 4)" in harness and "underIsGame" in harness, "")


def test_modmenu_description() -> None:
    """p207: the description panel finally has rows, because the working prefix of the body is kept.

    p206 diagnosed the empty panel but left it empty: the redirect replaced the whole render body,
    and the first ~1397 bytes of that body are the part that *builds* the description rows. p207
    adds a second redirect mode - keep everything before the removed-API tail, replace only the tail
    - and applies it. Four things are guarded, and again each one is read back from a committed
    artefact rather than asserted:

    * the patcher can do the cut and refuses three specific unsafe ones;
    * both description rules keep the prefix, and the whole-body rule is gone;
    * the two runs differ only in `modmenu.jar` and only the panel changed: 0 rows -> 13 rows;
    * the panel now reports its real box (x=328) instead of x=0, which also fixes where clicks land.
    """
    run = ROOT / "runs" / "p207-description-panel"
    patcher = ROOT / "java" / "src" / "main" / "java" / "top" / "mcbridge1201" / "rules" / "JarPatcher.java"
    rule_set = ROOT / "java" / "src" / "main" / "java" / "top" / "mcbridge1201" / "rules" / "RuleSet.java"
    bridge = (ROOT / "java" / "src" / "bridge" / "java" / "top" / "mcbridge1201" / "bridge"
              / "ModMenuListRenderBridge.java")
    legacy = bridge.parent / "LegacyParentWidget.java"
    rules = ROOT / "rules" / "fabric-1.21.1" / "modmenu-list-render.json"
    verdict_path = run / "description-check.json"
    # Every input must exist: silently skipping a missing one would turn a regression into a pass.
    missing = [str(p) for p in (patcher, rule_set, bridge, legacy, rules, verdict_path) if not p.exists()]
    check("p207: every input of this check is committed", not missing, ", ".join(missing))
    if missing:
        return

    def code_of(path: Path) -> str:
        text = path.read_text(encoding="utf-8")
        return re.sub(r"//[^\n]*", "", re.sub(r"/\*.*?\*/", "", text, flags=re.S))

    # --- 1. the new redirect mode ---------------------------------------------------------------
    patcher_code = code_of(patcher)
    rule_set_code = code_of(rule_set)
    check("p207: the rule model has a keep-the-prefix mode",
          "keepPrefixBeforeTombstones" in rule_set_code, "")
    check("p207: keeping the prefix goes through its own routine, not the wholesale replacement",
          "if (r.keepPrefixBeforeTombstones)" in patcher_code
          and "keepPrefixThenCall(cn, mn, r)" in patcher_code
          and patcher_code.index("keepPrefixThenCall(cn, mn, r)")
          < patcher_code.index("mn.instructions.clear()"),
          "")
    check("p207: the cut prefers a label that a jump or a handler targets",
          "entries.contains(label)" in patcher_code
          and "entryLabel != null ? entryLabel : anyLabel" in patcher_code,
          "a plain line-number label in the tail would keep a dead statement")
    check("p207: the three unsafe cuts are refused instead of shipped",
          "jumps past the cut to" in patcher_code
          and "still references \" + TOMBSTONE_PREFIX" in patcher_code
          and "so cutting it would drop a state change" in patcher_code,
          "")
    check("p207: a body with no tombstone is refused, not silently left alone",
          "found no reference to \" + TOMBSTONE_PREFIX" in patcher_code, "")

    java_test = ROOT / "java" / "src" / "test" / "java" / "top" / "mcbridge1201" / "JarPatcherKeepPrefixTest.java"
    check("p207: the new mode has its own regression test", java_test.exists(), str(java_test))
    if java_test.exists():
        test_code = java_test.read_text(encoding="utf-8")
        check("p207: that test covers success and both refusals",
              test_code.count("@Test") == 3
              and "keepsTheWorkingPrefixAndReplacesOnlyTheTombstoneTail" in test_code
              and "refusesWhenKeptCodeJumpsIntoTheReplacedTail" in test_code
              and "refusesWhenThereIsNoTombstoneReference" in test_code,
              f'{test_code.count("@Test")} tests')
        check("p207: the success case asserts the prefix's field write survives",
              "writesCol" in test_code and "writesLast" in test_code
              and "no removed-API call may survive the patch" in test_code, "")

    # --- 2. the rules that use it ---------------------------------------------------------------
    spec = json.loads(rules.read_text(encoding="utf-8"))
    by_id = {r["id"]: r for r in spec["bodyRedirects"]}
    check("p207: the rule that replaced the whole description body is gone",
          "modmenu.description.render-body" not in by_id, str(sorted(by_id)))
    tails = [by_id.get("modmenu.description.render-tail"),
             by_id.get("modmenu.description.render-tail-renamed")]
    check("p207: the description tail is redirected under both names a jar can carry",
          all(tails) and [t["name"] for t in tails] == ["method_25394", "method_48579"],
          str([t["name"] for t in tails if t]))
    check("p207: both description rules keep the prefix and call the same bridge method",
          all(t and t.get("keepPrefixBeforeTombstones") is True
              and t["bridgeMethod"] == "renderDescription" for t in tails),
          str([(t or {}).get("keepPrefixBeforeTombstones") for t in tails]))
    check("p207: the mod list redirect is untouched by this change",
          by_id["modmenu.list.render-body"].get("keepPrefixBeforeTombstones") is None
          and by_id["modmenu.list.render-body"]["bridgeMethod"] == "renderList", "")
    check("p207: the rule note says why the prefix matters",
          "only its tail is replaced" in spec["note"] and "count=0" in by_id[
              "modmenu.description.render-tail"]["evidence"], "")

    # --- 3. the bridge follows the panel to where the screen put it -----------------------------
    bridge_code = code_of(bridge)
    check("p207: the panel geometry comes from the 1.20.1 fields when they exist",
          all(f in bridge_code for f in ("field_19088", "field_19087", "field_19085", "field_19086"))
          and "boolean legacy = panel && fieldOrNull(type, \"field_19088\") != null" in bridge_code,
          "")
    check("p207: an absent legacy field is a nil answer, not a crash",
          "fieldOrNull" in bridge_code and "return null" in bridge_code, "")
    check("p207: the panel is one backdrop, the list keeps its per-row bands",
          "if (!panel)" in bridge_code
          and "context.method_25294(boxLeft, widgetTop, boxRight, widgetBottom, PANEL_BACKDROP)"
          in bridge_code,
          "")
    check("p207: the scrollbar only draws when there is something to scroll",
          # p209 moved this guard into a named flag so the "nothing to scroll" case could be
          # reported instead of returning silently; the condition itself is unchanged.
          ("maxScroll <= 0 || viewHeight < 12" in bridge_code
           or "boolean drawn = maxScroll > 0 && viewHeight >= 12" in bridge_code)
          and "method_25331" in bridge_code and "P207_SCROLL" in bridge_code, "")
    check("p207: every debug line is still behind -Dmcbridge.listrender.debug",
          bridge_code.count("System.out") == bridge_code.count("if (DEBUG")
          and 'Boolean.getBoolean("mcbridge.listrender.debug")' in bridge_code,
          f'{bridge_code.count("System.out")} prints vs {bridge_code.count("if (DEBUG")} guards')
    legacy_code = code_of(legacy)
    check("p207: setLeftPos also moves the widget's own x, so clicks land on the panel",
          re.search(r"method_25333\(int left\)[^}]*method_46421\(left\)", legacy_code, flags=re.S)
          is not None, "")

    # --- 4. what the two runs actually measured -------------------------------------------------
    report = json.loads(verdict_path.read_text(encoding="utf-8"))
    before = json.loads((run / "before" / "result.json").read_text(encoding="utf-8"))
    after = json.loads((run / "after" / "result.json").read_text(encoding="utf-8"))
    check("p207: the committed verdict passed every one of its checks",
          all(c["ok"] for c in report["checks"]) and len(report["checks"]) >= 17,
          str([c["name"] for c in report["checks"] if not c["ok"]]))
    check("p207: the two runs are the p206 jar and the new jar",
          before["modmenu_sha256"] == "8cbb82df59be78b430d9f935df304f794494e58d4df4698a97fc77251456dd09"
          and before["modmenu_sha256"] != after["modmenu_sha256"],
          f'{before["modmenu_sha256"][:12]} vs {after["modmenu_sha256"][:12]}')
    check("p207: both runs clicked the same row at the same device pixel",
          before["click"] == after["click"] and after["click"]["row"] == 3,
          f'{before["click"]} vs {after["click"]}')
    check("p207: only the description panel changed; the mod list kept its geometry",
          before["mod_list"] == after["mod_list"] and after["mod_list"]["count"] == 11,
          f'{before["mod_list"]} vs {after["mod_list"]}')
    check("p207: the control panel had no rows at all",
          (before.get("description") or {}).get("count") == 0, str(before.get("description")))
    check("p207: the fixed panel has the selected mod's rows",
          (after.get("description") or {}).get("count", 0) >= 10,
          f'count={(after.get("description") or {}).get("count")}')
    check("p207: the panel now reports its real box instead of x=0",
          report["control"]["description"]["box"] == [0, 108, 312, 216]
          and report["fix"]["description"]["box"] == [328, 108, 312, 216],
          f'{report["control"]["description"]["box"]} -> {report["fix"]["description"]["box"]}')
    check("p207: the panel read its layout from the legacy fields, as designed",
          "legacy=true" in (report["fix"]["panel_line"] or ""),
          str(report["fix"]["panel_line"]))
    check("p207: the fix paints text bands where the control had almost none",
          report["fix"]["bands"] >= 5 and report["control"]["bands"] <= 1
          and report["fix"]["ink"] > report["control"]["ink"] * 5,
          f'{report["control"]["bands"]}/{report["control"]["ink"]} -> '
          f'{report["fix"]["bands"]}/{report["fix"]["ink"]}')
    check("p207: exactly the three rebuilt classes differ from the p206 jar",
          report["differing_entries"] == [
              "com/terraformersmc/modmenu/gui/widget/DescriptionListWidget.class",
              "top/mcbridge1201/bridge/LegacyParentWidget.class",
              "top/mcbridge1201/bridge/ModMenuListRenderBridge.class"],
          str(report["differing_entries"]))
    check("p207: the body that was cut is byte-identical to the p206 record",
          any(c["name"] == "pre_redirect_body_matches_the_p206_record" and c["ok"]
              for c in report["checks"]), "")
    check("p207: the scrollbar branch is recorded as not exercised, not as passing",
          report["scrollbar_lines"] == []
          and "scrollbar not drawn in this run" in
          (run / "verify_description.py").read_text(encoding="utf-8"),
          str(report["scrollbar_lines"]))
    build_log = (run / "build.log").read_text(encoding="utf-8", errors="replace")
    check("p207: the build proved the renamed rule matched exactly once",
          "modmenu.description.render-tail-renamed applied 1 time(s)" in build_log, "")
    check("p207: the build refuses a class with debug prints or no tombstone as 'pristine'",
          "carries a println; refusing to ship it" in (run / "build.py").read_text(encoding="utf-8")
          and "has no tombstone reference" in (run / "build.py").read_text(encoding="utf-8"), "")


def test_modmenu_scroll() -> None:
    """p209: the scrollbar branch finally runs, and a real wheel drives the description panel.

    p207 recorded "scrollbar not drawn in this run (maxScroll=0)" and left the drawing code
    unexercised. This guards both halves of closing that gap:

    * a narrower window makes the same text wrap until the panel scrolls, so the branch runs;
    * the wheel moves the panel when it is over the panel and the mod list when it is over the mod
      list - measured in one run, in both directions, because "the wheel goes to what is under the
      cursor" cannot be shown by one direction.

    The control is the p207 jar at the same window size: it scrolls too (so p209 adds no behaviour),
    but its debug line cannot say when it did *not* scroll, which is what the new fields fix.
    """
    run = ROOT / "runs" / "p209-description-scroll"
    bridge = (ROOT / "java" / "src" / "bridge" / "java" / "top" / "mcbridge1201" / "bridge"
              / "ModMenuListRenderBridge.java")
    verdict_path = run / "scroll-check.json"
    missing = [str(p) for p in (bridge, verdict_path, run / "build.log", run / "run.py",
                                run / "verify_scroll.py") if not p.exists()]
    check("p209: every input of this check is committed", not missing, ", ".join(missing))
    if missing:
        return

    bridge_code = re.sub(r"//[^\n]*", "", re.sub(r"/\*.*?\*/", "", bridge.read_text(encoding="utf-8"),
                                                 flags=re.S))
    check("p209: the scrollbar decision is a named flag, not an early return",
          "boolean drawn = maxScroll > 0 && viewHeight >= 12" in bridge_code
          and "if (drawn) {" in bridge_code, "")
    check("p209: the scroll line reports the case where nothing scrolls",
          'String state = scroll + ":" + maxScroll + ":" + drawn' in bridge_code
          and "LAST_SCROLL_STATE" in bridge_code and '" drawn=" + drawn' in bridge_code, "")
    check("p209: the mod list line reports its own scroll, so the wheel routing is measurable",
          '" scroll=" + scroll + " max=" + maxScroll' in bridge_code
          and 'method_25331' in bridge_code, "")
    check("p209: the extra reflective reads are behind the debug gate",
          re.search(r"if \(DEBUG\) \{\s*double scroll = \(double\) invoke\(type, list, "
                    r"\"method_25341\"\)", bridge_code) is not None, "")
    check("p209: every debug line is still behind -Dmcbridge.listrender.debug",
          bridge_code.count("System.out") == bridge_code.count("if (DEBUG")
          and 'Boolean.getBoolean("mcbridge.listrender.debug")' in bridge_code,
          f'{bridge_code.count("System.out")} prints vs {bridge_code.count("if (DEBUG")} guards')

    build_log = (run / "build.log").read_text(encoding="utf-8", errors="replace")
    check("p209: the build swapped exactly one class and said so",
          "DIFF changed=top/mcbridge1201/bridge/ModMenuListRenderBridge.class added=none "
          "removed=none" in build_log, "")

    report = json.loads(verdict_path.read_text(encoding="utf-8"))
    check("p209: the committed verdict passed every one of its checks",
          all(c["ok"] for c in report["checks"]) and len(report["checks"]) >= 23,
          str([c["name"] for c in report["checks"] if not c["ok"]]))
    check("p209: the jar differs from the p207 one only in the bridge",
          report["changed_entries"] == ["top/mcbridge1201/bridge/ModMenuListRenderBridge.class"],
          str(report["changed_entries"]))

    # --- the control (p207 jar, same window, same notches) --------------------------------------
    control = report["control"]
    c_scan = {e["row"]: e for e in control["scan"]}
    check("p209: the p207 jar scrolls the panel too, so this is evidence and not new behaviour",
          control["before"]["desc"]["scroll"] == 0.0
          and control["after_panel_wheel"]["desc"]["scroll"] > 0,
          f'{control["before"]["desc"]["scroll"]} -> '
          f'{control["after_panel_wheel"]["desc"]["scroll"]}')
    check("p209: the p207 line reports the previous row's max after an empty selection",
          c_scan[6]["description_count"] == 0 and c_scan[6]["max"] == c_scan[5]["max"] == 568,
          f'row6 count={c_scan[6]["description_count"]} max={c_scan[6]["max"]} '
          f'row5 max={c_scan[5]["max"]}')

    # --- the run ----------------------------------------------------------------------------
    fix = report["fix"]
    scan = {e["row"]: e for e in fix["scan"]}
    check("p209: exactly one of the seven visible rows needs to scroll",
          [r for r, e in scan.items() if e["drawn"]] == [5]
          and fix["chosen"]["max"] > 0 and fix["chosen"]["description_count"] >= 50,
          f'row5 max={scan[5]["max"]} rows={scan[5]["description_count"]}')
    check("p209: the empty row now says max=0 instead of repeating the previous line",
          scan[6]["max"] == 0 and scan[6]["drawn"] is False, str(scan[6]))
    check("p209: the wheel over the panel moves the panel and not the mod list",
          fix["after_panel_wheel"]["desc"]["scroll"] > fix["before"]["desc"]["scroll"]
          and fix["after_panel_wheel"]["mod"]["scroll"] == fix["before"]["mod"]["scroll"],
          f'panel {fix["before"]["desc"]["scroll"]} -> '
          f'{fix["after_panel_wheel"]["desc"]["scroll"]}, '
          f'list {fix["before"]["mod"]["scroll"]} -> {fix["after_panel_wheel"]["mod"]["scroll"]}')
    check("p209: the same wheel over the mod list moves the mod list and not the panel",
          fix["after_mod_wheel"]["mod"]["scroll"] > 0
          and fix["after_mod_wheel"]["desc"]["scroll"] == fix["after_panel_wheel"]["desc"]["scroll"],
          f'list {fix["after_mod_wheel"]["mod"]["scroll"]}, '
          f'panel {fix["after_mod_wheel"]["desc"]["scroll"]}')

    # --- pixels ---------------------------------------------------------------------------------
    thumb_before, thumb_after = fix["thumb_before"], fix["thumb_after"]
    check("p209: the pixels show one thumb at the panel edge, and it moved down",
          len(thumb_before) == 1 and len(thumb_after) == 1
          and thumb_after[0][0] > thumb_before[0][0],
          f"{thumb_before} -> {thumb_after}")
    check("p209: the thumb is the height the formula predicts",
          abs((thumb_before[0][1] - thumb_before[0][0] + 1) - 116) <= 4,
          str(thumb_before))
    check("p209: the text moved up by the scroll amount",
          fix["shift"]["best_dy"] < 0
          and abs(fix["shift"]["best_dy"] + 2 * (fix["after_panel_wheel"]["desc"]["scroll"]
                                                - fix["before"]["desc"]["scroll"])) <= 4,
          f'{fix["shift"]["best_dy"]} vs '
          f'{fix["after_panel_wheel"]["desc"]["scroll"] - fix["before"]["desc"]["scroll"]}')
    check("p209: the same measurement on the control run moves by its own scroll amount",
          control["shift"]["best_dy"] < 0
          and abs(control["shift"]["best_dy"] + 2 * (control["after_panel_wheel"]["desc"]["scroll"]
                                                     - control["before"]["desc"]["scroll"])) <= 4,
          f'{control["shift"]["best_dy"]}')

    # --- the traps this run had to document ----------------------------------------------------
    check("p209: the result records that the probe's target switches between the two lists",
          fix["probe_state_targets"] == [11, 78], str(fix["probe_state_targets"]))
    runner = (run / "run.py").read_text(encoding="utf-8")
    check("p209: the harness explains the probe's findList trap where it matters",
          "findList` picks" in runner or "picks the EntryListWidget with the largest `maxScroll`"
          in runner, "")
    check("p209: the harness re-clicks the chosen row before wheeling",
          "RESELECT" in runner and "reselected" in runner, "")
    verifier = (run / "verify_scroll.py").read_text(encoding="utf-8")
    check("p209: the verdict computes the thumb travel from its ratio, not 1:1",
          "travel = track - predicted" in verifier and "travel * (scroll_delta / max_scroll)"
          in verifier, "")
    check("p207: the README points at p209 for the scrollbar it never exercised",
          "runs/p209-description-scroll" in (ROOT / "runs" / "p207-description-panel"
                                            / "README.md").read_text(encoding="utf-8"), "")


def test_cloth_config() -> None:
    """p210: AppleSkin's Cloth Config screen opens on 1.21.1, draws its 13 rows, and a click moves it.

    The screen is drawn by a jar-in-jar (Cloth Config 11.1.136, a 1.20.1 build) that has to be
    taken out, patched against 1.21.1 and put back, so the thing that can silently rot is *the rule
    hit count*: a rule that stops matching ships the crash it exists to remove, and the client only
    says so five minutes into a launch. This reads the committed build log and asserts every rule
    in the rule files matched the expected number of times.

    Everything else here is the committed verdict (`cloth-check.json`, produced by
    `verify_cloth.py` from `before/` + `after3/`), the shipped jar's hash, and the regression test
    for the `onlyIfExtends` gate this run added to `JarPatcher` - the gate that failed loudly once
    already (renaming `method_25394` under `class_362` produced thirteen rows that never painted).
    """
    run = ROOT / "runs" / "p210-cloth-config"
    rules_dir = ROOT / "rules" / "fabric-1.21.1"
    rule_files = [rules_dir / "cloth-config.json", rules_dir / "cloth-config-render.json",
                  rules_dir / "render-widget-override.json"]
    verdict_path = run / "cloth-check.json"
    inputs = [run / "build.py", run / "run.py", run / "build_probe.py", run / "scan_refs.py",
              run / "verify_cloth.py", run / "README.md", run / "build.log", verdict_path,
              run / "before" / "result.json", run / "after3" / "result.json",
              run / "after3" / "client.log",
              ROOT / "java" / "src" / "test" / "java" / "top" / "mcbridge1201"
              / "JarPatcherMethodRenameTest.java"] + rule_files
    missing = [str(p.relative_to(ROOT)) for p in inputs if not p.exists()]
    check("p210: every input of this check is committed", not missing, ", ".join(missing))
    if missing:
        return

    # --- the rules parse, and each carries the fields the project requires ---------------------
    rule_ids: dict[str, str] = {}
    for path in rule_files:
        data = json.loads(path.read_text(encoding="utf-8"))
        for key in ("fieldRedirects", "callSiteAdaptations", "methodRedirects", "bodyRedirects",
                    "methodRenames", "superclassReplacements"):
            for rule in data.get(key) or []:
                rule_ids[rule["id"]] = key
                check(f"p210: {rule['id']} documents capability/risk/evidence ({path.name})",
                      all(rule.get(field) for field in ("capability", "risk", "evidence")), "")
    cloth_ids = {rid for rid in rule_ids if rid.startswith("cloth-config.")}
    check("p210: the two cloth rule files carry sixteen rules", len(cloth_ids) == 16,
          f"{len(cloth_ids)} rules: {sorted(cloth_ids)}")
    check("p210: the new demo rules are field+callSite adaptations, not body replacements",
          rule_ids.get("cloth-config.render.demo-enchantment") == "fieldRedirects"
          and rule_ids.get("cloth-config.render.demo-add-enchantment") == "callSiteAdaptations",
          str({k: rule_ids.get(k) for k in ("cloth-config.render.demo-enchantment",
                                            "cloth-config.render.demo-add-enchantment")}))
    render = json.loads(rule_files[1].read_text(encoding="utf-8"))
    notes = render.get("note", "")
    check("p210: the render rule file still records the screen it does not cover",
          "GlobalizedClothConfigScreen" in notes and "27" in notes, "note names the 27 stubs")

    # --- the build hit every rule the expected number of times --------------------------------
    build_log = (run / "build.log").read_text(encoding="utf-8", errors="replace")
    check("p210: the build validated all three rule files",
          "validated 3 rule file(s)" in build_log, "")
    expected = {rid: 1 for rid in cloth_ids}
    expected["cloth-config.render.buffer-accessor"] = 5   # 1 live t0 in method_25394, 1 dead in renderList
    expected["fabric.legacy.clickable-text-override"] = 8
    expected["fabric.legacy.render-widget-override"] = 6
    wrong = []
    for rid, count in sorted(expected.items()):
        match = re.search(rf"rule {re.escape(rid)} applied (\d+) time\(s\)", build_log)
        if not match:
            wrong.append(f"{rid}: not applied")
        elif int(match.group(1)) != count:
            wrong.append(f"{rid}: {match.group(1)} != {count}")
    check("p210: every rule matched exactly as often as the build says it must",
          not wrong, "; ".join(wrong))
    check("p210: the build wrote the jar this evidence came from",
          "OUT appleskin-cloth.jar sha256=" in build_log, "")

    # --- the committed verdict ----------------------------------------------------------------
    verdict = json.loads(verdict_path.read_text(encoding="utf-8"))
    failed_checks = [c["name"] for c in verdict["checks"] if not c["ok"]]
    check("p210: the committed verdict passed every one of its checks",
          not failed_checks and len(verdict["checks"]) >= 30,
          f"{len(verdict['checks'])} checks, failed: {failed_checks}")
    check("p210: the control run failed on the removed field and nowhere else",
          verdict["control"]["config"]["ok"] is False
          and "field_44669" in verdict["control"]["config"]["error"], "")
    check("p210: the fix run drew thirteen rows with nine toggles",
          verdict["fix"]["rows"] == 13
          and verdict["fix"]["kinds"].get("BooleanToggleBuilder$1") == 9,
          f"rows={verdict['fix']['rows']} kinds={verdict['fix']['kinds']}")
    check("p210: the click moved the value without the direct-press fallback",
          verdict["fix"]["toggle"]["flipped"] is True
          and verdict["fix"]["toggle"]["direct_press"] is False
          and "handled=true" in (verdict["fix"]["toggle_click"] or ""),
          str(verdict["fix"]["toggle"]))

    # --- provenance: the verdict, the run and the jar all name the same bytes -----------------
    after = json.loads((run / "after3" / "result.json").read_text(encoding="utf-8"))
    check("p210: the fix run recorded no mod error",
          after.get("client_errors") == [] and after.get("no_such_field") == 0
          and after.get("no_such_method") == 0,
          str(after.get("client_errors")))
    check("p210: the verdict and the run describe the same jar",
          verdict["fixed_sha256"] == after.get("appleskin_sha256"),
          f'{verdict["fixed_sha256"]} vs {after.get("appleskin_sha256")}')
    jar = ROOT / "work" / "client" / "appleskin-cloth.jar"
    if jar.exists():
        digest = __import__("hashlib").sha256(jar.read_bytes()).hexdigest()
        check("p210: the shipped jar is the one the evidence ran against",
              digest == verdict["fixed_sha256"], f"{digest} vs {verdict['fixed_sha256']}")
    else:
        SKIPPED.append("p210 shipped jar hash (run runs/p210-cloth-config/build.py first)")

    # --- the regression test that pins the onlyIfExtends gate ---------------------------------
    test_src = (ROOT / "java" / "src" / "test" / "java" / "top" / "mcbridge1201"
                / "JarPatcherMethodRenameTest.java").read_text(encoding="utf-8")
    cases = re.findall(r"void (\w+)\(\) throws Exception", test_src)
    check("p210: the onlyIfExtends gate has four regression cases", len(cases) == 4, str(cases))
    check("p210: the cases cover direct parent, deep ancestor, unrelated parent, unknown chain",
          all(fragment in test_src for fragment in (
              "renamesWhenTheDirectParentIsTheGatedType",
              "renamesWhenTheGatedTypeIsThreeLevelsUp",
              "doesNotRenameUnderAnUnrelatedParent",
              "doesNotRenameWhenTheAncestorCannotBeResolved")), "")
    check("p210: the test states the rule the gate protects",
          "onlyIfExtends" in test_src and "class_362" in test_src, "")
    patcher = (ROOT / "java" / "src" / "main" / "java" / "top" / "mcbridge1201" / "rules"
               / "JarPatcher.java").read_text(encoding="utf-8")
    check("p210: an unresolvable ancestor aborts the walk instead of answering yes",
          re.search(r"not knowing an ancestor is not\s*\*?\s*evidence of having it",
                    patcher) is not None
          and "cur = next;" in patcher, "")

    # --- docs moved with the behaviour --------------------------------------------------------
    remaining = (ROOT / "docs" / "remaining-work.md").read_text(encoding="utf-8")
    check("p210: remaining-work no longer says the Cloth screens cannot open",
          "Cloth-Config screens cannot open at all" not in remaining, "")
    status = (ROOT / "docs" / "FINAL-STATUS.md").read_text(encoding="utf-8")
    check("p210: FINAL-STATUS records the screen as open and the one screen left uncovered",
          "rows=13" in status and "GlobalizedClothConfigScreen" in status, "")
    distribution = (ROOT / "docs" / "distribution.md").read_text(encoding="utf-8")
    check("p210: distribution ships appleskin-cloth.jar",
          "appleskin-cloth.jar" in distribution, "")


def test_pcl2_detect() -> None:
    """p211: PCL2 is on this machine, and a dead desktop shortcut is no longer skipped in silence.

    p195/p137 recorded 任务 6 as blocked for lack of a PCL2 install. It was not missing: the
    recorded path (`D:\\我的世界\\.minecraft\\涟漪专用启动器`) had been deleted while the launcher
    itself still lived under a download folder, and the desktop shortcut still named the dead path.
    `pcl2_from_desktop()` dropped a shortcut whose target did not exist without a word, so
    `detect_pcl_root()` fell through to `%APPDATA%/.minecraft` and reported it as "detected" - which
    happens to be the right folder here, and would not be on a machine whose PCL2 uses a custom
    folder (runs/p211-pcl2-detect/).

    The resolver is tested on synthetic trees (the game-dir resolution) and with an injected
    desktop/resolver (the notes), because COM and a real desktop are exactly what a test cannot
    assume.
    """
    run = ROOT / "runs" / "p211-pcl2-detect"
    verify_path = run / "detect-check.json"
    missing = [str(p.relative_to(ROOT)) for p in
               (run / "probe_pcl.py", run / "panel_smoke.py", run / "verify_detect.py",
                verify_path, run / "before" / "probe.json", run / "after" / "probe.json",
                run / "panel-smoke.json", run / "panel-smoke.png",
                ROOT / "tools" / "from_source_install.py", ROOT / "tools" / "pcl_panel.py")
               if not p.exists()]
    check("p211: every input of this check is committed", not missing, ", ".join(missing))
    if missing:
        return

    sys.path.insert(0, str(ROOT / "tools"))
    import from_source_install as fs

    # --- the resolver, on synthetic trees -----------------------------------------------------
    base = WORK / "pcl2-detect"
    if base.exists():
        import shutil

        shutil.rmtree(base, ignore_errors=True)
    game_abs = base / "absolute-game"
    game_abs.mkdir(parents=True, exist_ok=True)
    launcher = base / "launcher"
    (launcher / "PCL").mkdir(parents=True, exist_ok=True)
    (launcher / "PCL" / "Setup.ini").write_text(
        f"LaunchFolderSelect:{game_abs}\\\nVersionArgumentIndie:0\n", encoding="utf-8")
    check("p211: an absolute LaunchFolderSelect is followed",
          fs.pcl2_game_dir(launcher) == Path(str(game_abs)), str(fs.pcl2_game_dir(launcher)))
    check("p211: the same holds when the caller passes the exe",
          fs.pcl2_game_dir(launcher / "plain craft launcher 2.exe") == Path(str(game_abs)), "")

    rel = base / "relative"
    (rel / "PCL").mkdir(parents=True, exist_ok=True)
    (rel / "PCL" / "Setup.ini").write_text("LaunchFolderSelect:$minecraft\n", encoding="utf-8")
    check("p211: a $-relative LaunchFolderSelect resolves inside the launcher folder",
          fs.pcl2_game_dir(rel) == rel / "minecraft", str(fs.pcl2_game_dir(rel)))

    portable = base / "portable"
    (portable / ".minecraft").mkdir(parents=True, exist_ok=True)
    check("p211: with no Setup.ini the portable .minecraft is used",
          fs.pcl2_game_dir(portable) == portable / ".minecraft", str(fs.pcl2_game_dir(portable)))

    nothing = base / "nothing"
    nothing.mkdir(parents=True, exist_ok=True)
    check("p211: a folder with neither config nor .minecraft yields None",
          fs.pcl2_game_dir(nothing) is None, str(fs.pcl2_game_dir(nothing)))

    # --- the notes, with an injected desktop and resolver -------------------------------------
    fake_desktop = base / "desktop"
    fake_desktop.mkdir(parents=True, exist_ok=True)
    (fake_desktop / "Plain Craft Launcher 2.lnk").write_text("not a real shortcut",
                                                             encoding="utf-8")
    dead = str(base / "deleted-launcher" / "Plain Craft Launcher 2.exe")
    resolved, notes = fs.pcl2_shortcut_scan(fake_desktop, resolve=lambda lnk: dead)
    check("p211: a shortcut whose target is gone reports the dead path instead of vanishing",
          resolved is None and any("已不存在" in n and dead in n for n in notes), str(notes))
    resolved, notes = fs.pcl2_shortcut_scan(fake_desktop, resolve=lambda lnk: None)
    check("p211: an unreadable shortcut says so", resolved is None
          and any("读不到" in n for n in notes), str(notes))
    empty_desktop = base / "empty-desktop"
    empty_desktop.mkdir(parents=True, exist_ok=True)
    resolved, notes = fs.pcl2_shortcut_scan(empty_desktop, resolve=lambda lnk: dead)
    check("p211: a desktop without a PCL shortcut says so",
          resolved is None and any("没有 PCL 快捷方式" in n for n in notes), str(notes))

    live = base / "live"
    (live / "PCL").mkdir(parents=True, exist_ok=True)
    (live / "PCL" / "Setup.ini").write_text(f"LaunchFolderSelect:{game_abs}\n", encoding="utf-8")
    resolved, notes = fs.pcl2_shortcut_scan(fake_desktop, resolve=lambda lnk: str(live))
    check("p211: a live shortcut still resolves without notes",
          resolved == Path(str(game_abs)) and notes == [], f"{resolved} {notes}")

    # --- the callers actually show the notes --------------------------------------------------
    install_src = (ROOT / "tools" / "from_source_install.py").read_text(encoding="utf-8")
    check("p211: detect_pcl_root can hand its notes to a caller",
          "def detect_pcl_root(notes: list[str] | None = None)" in install_src, "")
    check("p211: the CLI prints the notes rather than only the folder",
          install_src.count('print("PCL 检测:", note') == 2, "")
    panel_src = (ROOT / "tools" / "pcl_panel.py").read_text(encoding="utf-8")
    check("p211: the panel shows the notes next to the folder field",
          "detect_notes: list[str] = []" in panel_src and "self.note_label" in panel_src, "")

    # --- the evidence -------------------------------------------------------------------------
    verdict = json.loads(verify_path.read_text(encoding="utf-8"))
    failed_checks = [c["name"] for c in verdict["checks"] if not c["ok"]]
    check("p211: the committed verdict passed every one of its checks",
          not failed_checks and len(verdict["checks"]) >= 25,
          f"{len(verdict['checks'])} checks, failed: {failed_checks}")
    pcl2 = verdict["pcl2"]
    check("p211: the evidence names the launcher, its version and its game folder",
          pcl2["file_version"] == "2.13.1.1" and pcl2["game_dir"]
          and pcl2["launch_folder_select"], json.dumps(pcl2, ensure_ascii=False)[:160])
    check("p211: the stale shortcut is recorded as the p137 folder",
          "涟漪专用启动器" in (verdict["shortcut"]["target"] or "")
          and verdict["shortcut"]["target_exists"] is False, "")
    check("p211: before the fix nothing was reported, after it the miss is explained",
          verdict["before_notes"] == [] and any("已不存在" in n for n in verdict["after_notes"]),
          str(verdict["after_notes"])[:120])
    check("p211: the panel really rendered the note (widget + pixels)",
          verdict["panel"]["note_visible"] is True
          and Path(verdict["panel"]["screenshot"]).is_file(), verdict["panel"]["note_label"][:90])

    # --- docs moved with the finding ----------------------------------------------------------
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    check("p211: README no longer says PCL2 is missing on this machine",
          "PCL2 本机路径不存在" not in readme and "runs/p211-pcl2-detect" in readme, "")
    status = (ROOT / "docs" / "FINAL-STATUS.md").read_text(encoding="utf-8")
    check("p211: FINAL-STATUS carries the corrected environment fact",
          "2.13.1.1" in status and "runs/p211-pcl2-detect" in status, "")
    remaining = (ROOT / "docs" / "remaining-work.md").read_text(encoding="utf-8")
    check("p211: remaining-work stops calling 任务 6 blocked for lack of PCL2",
          "PCL2 本机路径不存在" not in remaining
          and "本机没有 PCL2" not in remaining, "")


def main() -> int:
    test_issue03()
    test_issue02()
    test_launcher()
    test_neoforge_install()
    test_loader_base_ensure()
    test_immediatelyfast_port()
    test_map_atlas_layout_evidence()
    test_hover_and_heterogeneous_nbt()
    test_trash_concurrent_same_tick()
    test_cross_platform_delivery()
    test_real_wheel_input()
    test_modmenu_rows()
    test_modmenu_selection()
    test_modmenu_description()
    test_modmenu_scroll()
    test_cloth_config()
    test_pcl2_detect()
    test_text_encoding_guard()
    test_eol_determinism()
    test_download_policy()
    failed = [name for name, ok, _ in RESULTS if not ok]
    print(f"\n{len(RESULTS) - len(failed)}/{len(RESULTS)} checks passed"
          + (f", skipped: {', '.join(SKIPPED)}" if SKIPPED else ""))
    if failed:
        return 1
    return 2 if SKIPPED else 0


if __name__ == "__main__":
    sys.exit(main())
