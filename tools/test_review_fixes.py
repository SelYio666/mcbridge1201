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

import json
import os
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

    p = subprocess.run(cmd, capture_output=True, text=True)
    return p.returncode, (p.stdout + p.stderr)


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


def main() -> int:
    test_issue03()
    test_issue02()
    test_launcher()
    test_neoforge_install()
    test_loader_base_ensure()
    test_immediatelyfast_port()
    test_download_policy()
    failed = [name for name, ok, _ in RESULTS if not ok]
    print(f"\n{len(RESULTS) - len(failed)}/{len(RESULTS)} checks passed"
          + (f", skipped: {', '.join(SKIPPED)}" if SKIPPED else ""))
    if failed:
        return 1
    return 2 if SKIPPED else 0


if __name__ == "__main__":
    sys.exit(main())
