#!/usr/bin/env python3
"""Exercise A03 (target-isolated bridge build) and A04 (cache key + stale-bridge guard).

    python tools/run_isolation_cache.py
    python tools/run_isolation_cache.py --out runs/p245-target-isolation-cache

Every case states what it must prove, and the run fails when a negative case passes or fails for a
different reason. Nothing here launches the game and no artifact is converted: this is about the
build and cache contract, not about gameplay.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORK = ROOT / "work" / "tmp" / "p245"
PROFILE = ROOT / "targets" / "fabric-1.21.1.json"
DEFAULT_OUT = ROOT / "runs" / "p245-target-isolation-cache"
BRIDGE_ABI = "mcbridge-bridge-1"


def ensure_java_home() -> str | None:
    env = os.environ.get("JAVA_HOME")
    if env and (Path(env) / "bin" / "java.exe").exists():
        return env
    for cand in (ROOT.parent / ".toolchain" / "jdk", ROOT / ".toolchain" / "jdk"):
        if (cand / "bin" / "java.exe").exists():
            os.environ["JAVA_HOME"] = str(cand)
            return str(cand)
    return None


def run(cmd: list, timeout=900) -> tuple[int, str]:
    p = subprocess.run([str(c) for c in cmd], cwd=ROOT, capture_output=True, text=True,
                       errors="replace", timeout=timeout)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8", newline="\n")


def class_majors(dir_path: Path) -> dict[int, int]:
    counts: dict[int, int] = {}
    for p in dir_path.rglob("*.class"):
        head = p.read_bytes()[:8]
        if len(head) < 8:
            continue
        major = (head[6] << 8) | head[7]
        counts[major] = counts.get(major, 0) + 1
    return counts


def profile_copy(name: str, mutate) -> Path:
    data = json.loads(PROFILE.read_text(encoding="utf-8"))
    mutate(data)
    p = WORK / name
    write_json(p, data)
    return p


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    args = ap.parse_args()
    out = Path(args.out)
    if not out.is_absolute():
        out = ROOT / out
    out.mkdir(parents=True, exist_ok=True)

    java_home = ensure_java_home()
    if java_home is None:
        write_json(out / "result.json", {"passed": False, "skipped": True,
                                         "reason": "no JDK found; set JAVA_HOME"})
        print("SKIP: no JDK found", file=sys.stderr)
        return 2

    if WORK.exists():
        shutil.rmtree(WORK)
    WORK.mkdir(parents=True)
    profile = json.loads(PROFILE.read_text(encoding="utf-8"))
    target_out = ROOT / profile["pipeline"]["output"]["bridgeClasses"]
    stub = ROOT / profile["indices"]["bridgeStub"]["path"]
    lib_args: list[str] = []
    for entry in profile["indices"]["libs"]:
        lib_args += ["--lib", str(ROOT / entry["path"])]
    bridge_py = str(ROOT / "tools" / "build_bridges.py")
    cache_py = str(ROOT / "tools" / "conversion_cache.py")
    source_jar = str(ROOT / "work" / "corpus" / "ironchests" / "ironchests-5.0.2-fabric.jar")
    cases: list[dict] = []

    def add(case_id, goal, expect, rc, extra=None):
        c = {"id": case_id, "goal": goal, "expect": expect, "rc": rc}
        c.update(extra or {})
        cases.append(c)
        print(f"  {case_id}: rc={rc} expected={expect.get('rc', 'n/a')}")

    # ---------------------------------------------------------------- A03
    rc, text = run([sys.executable, bridge_py, "--profile", str(PROFILE)])
    majors = class_majors(target_out) if target_out.is_dir() else {}
    add("a03-target-build", "profile mode compiles bridges into the target's own directory",
        {"rc": 0, "onlyMajor": 65, "dir": str(target_out.relative_to(ROOT)).replace("\\", "/")},
        rc, {"majors": {str(k): v for k, v in majors.items()},
             "outDir": str(target_out.relative_to(ROOT)).replace("\\", "/"),
             "classes": sum(majors.values()), "tail": text.strip().splitlines()[-2:]})

    legacy_out = WORK / "legacy-bridges"
    rc, text = run([sys.executable, bridge_py, "--stub", str(stub), "--out", str(legacy_out),
                    "--release", "21"] + lib_args)
    add("a03-legacy-entry", "the old --stub/--lib/--out invocation still works",
        {"rc": 0}, rc, {"tail": text.strip().splitlines()[-2:]})

    cases.append({"id": "a03-output-isolated",
                  "goal": "the target output dir differs from the legacy default work/bridges",
                  "expect": {"different": True}, "rc": 0,
                  "targetOut": str(target_out.relative_to(ROOT)).replace("\\", "/"),
                  "legacyOut": "work/bridges",
                  "different": target_out.resolve() != (ROOT / "work" / "bridges").resolve()})
    print("  a03-output-isolated: checked")

    java_too_new = profile_copy("profile-java25.json", lambda d: (
        d["target"].__setitem__("javaMajor", 25), d["target"].__setitem__("classMajorMax", 69)))
    rc, text = run([sys.executable, bridge_py, "--profile", str(java_too_new)])
    add("a03-java-unreachable", "a target above the local javac is refused, not approximated",
        {"rc": 2, "contains": "needs Java 25"}, rc, {"tail": text.strip().splitlines()[-1:]})

    bad_stub = profile_copy("profile-bad-stub.json",
                            lambda d: d["indices"]["bridgeStub"].__setitem__("sha256", "0" * 64))
    rc, text = run([sys.executable, bridge_py, "--profile", str(bad_stub)])
    add("a03-stub-unpinned", "a stub whose bytes differ from the frozen hash is refused",
        {"rc": 2, "contains": "profile froze"}, rc, {"tail": text.strip().splitlines()[-1:]})

    older = profile_copy("profile-java17.json", lambda d: (
        d["target"].__setitem__("javaMajor", 17), d["target"].__setitem__("classMajorMax", 61)))
    rc, text = run([sys.executable, bridge_py, "--profile", str(older)])
    add("a03-stub-newer-than-target", "a stub newer than the target Java level is refused",
        {"rc": 2, "contains": "above the target"}, rc, {"tail": text.strip().splitlines()[-1:]})

    abi = profile_copy("profile-abi.json",
                       lambda d: d["pipeline"].__setitem__("bridgeAbi", "mcbridge-bridge-0"))
    rc, text = run([sys.executable, bridge_py, "--profile", str(abi)])
    add("a03-bridge-abi", "a profile for another bridge ABI is refused",
        {"rc": 2, "contains": "bridge ABI"}, rc, {"tail": text.strip().splitlines()[-1:]})

    # ---------------------------------------------------------------- A04
    key_cmd = [sys.executable, cache_py, "key", "--profile", str(PROFILE), "--source", source_jar,
               "--bridge-dir", str(target_out), "--rules-from-profile"]
    rc1, k1 = run(key_cmd)
    rc2, k2 = run(key_cmd)
    k1, k2 = k1.strip(), k2.strip()
    add("a04-key-stable", "the same inputs give the same key",
        {"rc": 0, "same": True}, rc1, {"key": k1, "key2": k2, "same": k1 == k2 and rc1 == rc2 == 0})

    base = ["--profile", str(PROFILE), "--source", source_jar, "--bridge-dir", str(target_out),
            "--rules-from-profile"]
    rc, text = run([sys.executable, cache_py, "store"] + base + ["--artifact", source_jar])
    rc2, text2 = run([sys.executable, cache_py, "lookup"] + base)
    add("a04-store-then-hit", "a stored conversion is found again by its key",
        {"rc": 0}, rc2, {"storeRc": rc, "hit": "HIT" in text2, "tail": text2.strip().splitlines()[:2]})

    changed_target = profile_copy("profile-1214.json", lambda d: (
        d["target"].__setitem__("id", "fabric-1.21.4"),
        d["target"].__setitem__("minecraft", "1.21.4")))
    lookup_json = WORK / "lookup-target-changed.json"
    rc, text = run([sys.executable, cache_py, "lookup", "--profile", str(changed_target),
                    "--source", source_jar, "--bridge-dir", str(target_out), "--rules-from-profile",
                    "--json", str(lookup_json)])
    report = json.loads(lookup_json.read_text(encoding="utf-8")) if lookup_json.is_file() else {}
    add("a04-target-changed", "another target does not hit the old cache entry",
        {"rc": 1}, rc, {"hit": report.get("hit"), "reasons": report.get("reasons", [])})

    other_bridges = WORK / "bridges-stale"
    shutil.copytree(target_out, other_bridges)
    victim = sorted(other_bridges.rglob("*.class"))[0]
    victim.write_bytes(victim.read_bytes()[:20] + b"\x00" + victim.read_bytes()[21:])
    lookup_json = WORK / "lookup-bridge-changed.json"
    rc, text = run([sys.executable, cache_py, "lookup", "--profile", str(PROFILE),
                    "--source", source_jar, "--bridge-dir", str(other_bridges),
                    "--rules-from-profile", "--json", str(lookup_json)])
    report = json.loads(lookup_json.read_text(encoding="utf-8")) if lookup_json.is_file() else {}
    reasons = report.get("reasons", [])
    add("a04-bridge-changed", "a rebuilt bridge class invalidates the cache and says so",
        {"rc": 1, "reasonPrefix": "bridges"}, rc,
        {"hit": report.get("hit"), "reasons": reasons,
         "sawBridgeReason": any(r.startswith("bridges") for r in reasons)})

    rc, k_rules = run([sys.executable, cache_py, "key", "--profile", str(PROFILE),
                       "--source", source_jar, "--bridge-dir", str(target_out),
                       "--rules", "rules/fabric-1.21.1/container.json"])
    add("a04-rules-changed", "a different rule package gives a different key",
        {"rc": 0, "differentFromBase": True}, rc,
        {"key": k_rules.strip(), "differentFromBase": k_rules.strip() != k1})

    # stale bridge conflict: a jar carrying a different byte-image of a bridge class must be caught
    import zipfile
    candidates = sorted(p for p in target_out.rglob("*.class")
                        if "mcbridge1201/bridge" in p.as_posix())
    if not candidates:
        add("a04-bridge-conflict", "a jar embedding a different bridge byte image is reported",
            {"rc": 1, "contains": "MISMATCH"}, 2, {"tail": ["no bridge classes under target output"]})
    else:
        canonical = candidates[0]
        internal = canonical.relative_to(target_out).as_posix()
        bad_jar = WORK / "stale-bridge.jar"
        with zipfile.ZipFile(bad_jar, "w") as z:
            z.writestr("fabric.mod.json", "{}")
            z.writestr(internal, canonical.read_bytes()[:20] + b"\x01")
        rc, text = run([sys.executable, str(ROOT / "tools" / "check_bridge_consistency.py"),
                        "--bridge-dir", str(target_out), "--jar", str(bad_jar)])
        add("a04-bridge-conflict", "a jar embedding a different bridge byte image is reported",
            {"rc": 1, "contains": "MISMATCH"}, rc,
            {"class": internal, "tail": text.strip().splitlines()[-3:]})

    # ---------------------------------------------------------------- verdicts
    for c in cases:
        exp = c["expect"]
        ok = c["rc"] == exp.get("rc", 0)
        if "contains" in exp:
            ok = ok and any(exp["contains"] in line for line in c.get("tail", []))
        for flag in ("same", "different", "differentFromBase", "hit", "sawBridgeReason"):
            if flag in exp:
                ok = ok and bool(c.get(flag))
        if "onlyMajor" in exp:
            ok = ok and list(c.get("majors", {}).keys()) == [str(exp["onlyMajor"])]
        if "reasonPrefix" in exp:
            ok = ok and any(r.startswith(exp["reasonPrefix"]) for r in c.get("reasons", []))
        c["passed"] = ok

    for c in cases:
        print(f"{'PASS' if c['passed'] else 'FAIL'} {c['id']}")

    failed = [c["id"] for c in cases if not c["passed"]]
    result = {
        "workstreams": ["A03 target-isolated bridge build", "A04 cache key and stale-bridge guard"],
        "profile": str(PROFILE.relative_to(ROOT)).replace("\\", "/"),
        "targetOutput": str(target_out.relative_to(ROOT)).replace("\\", "/"),
        "javaHome": java_home,
        "cases": cases,
        "passed": not failed,
        "failed": failed,
        "scope": "build and cache contract only: no jar was converted and no game was launched",
    }
    write_json(out / "result.json", result)
    print(f"\ntarget isolation + cache: {'PASS' if not failed else 'FAIL'}"
          f" ({len(cases) - len(failed)}/{len(cases)} cases) -> {out / 'result.json'}")
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
