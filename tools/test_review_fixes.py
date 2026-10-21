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


def main() -> int:
    test_issue03()
    test_issue02()
    test_launcher()
    failed = [name for name, ok, _ in RESULTS if not ok]
    print(f"\n{len(RESULTS) - len(failed)}/{len(RESULTS)} checks passed"
          + (f", skipped: {', '.join(SKIPPED)}" if SKIPPED else ""))
    if failed:
        return 1
    return 2 if SKIPPED else 0


if __name__ == "__main__":
    sys.exit(main())
