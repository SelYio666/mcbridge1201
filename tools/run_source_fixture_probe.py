#!/usr/bin/env python3
"""A05 (source-side fixture) and A06 (1.20.4 architecture probe) evidence.

    python tools/run_source_fixture_probe.py
    python tools/run_source_fixture_probe.py --out runs/p246-source-fixture-1204

A05 proves the fixture exists as a pinned artifact and that the bytecode shapes it claims are
really in it. A06 proves three separate things about switching target to 1.20.4: the environment
is pinned and readable at Java 17, the gate refuses to convert without a rule package, and a
1.20.1 source's remaining breakage is *located* rather than guessed at.

Nothing here launches a game. The fixture's source-side runtime baseline is reported as pending,
because this machine has no 1.20.1 Fabric instance to run it in.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = ROOT / "fixtures" / "source-fabric-1.20.1"
FIXTURE_JAR = FIXTURE / "out" / "mcbfixture-1.0.0.jar"
FIXTURE_MANIFEST = FIXTURE / "manifest.json"
PROFILE_1204 = ROOT / "targets" / "fabric-1.20.4.json"
PROFILE_1211 = ROOT / "targets" / "fabric-1.21.1.json"
RULES_1211 = ROOT / "rules" / "fabric-1.21.1"
DEFAULT_OUT = ROOT / "runs" / "p246-source-fixture-1204"
WORK = ROOT / "work" / "tmp" / "p246"


def ensure_java_home() -> str | None:
    env = os.environ.get("JAVA_HOME")
    if env and (Path(env) / "bin" / "java.exe").exists():
        return env
    for cand in (ROOT.parent / ".toolchain" / "jdk", ROOT / ".toolchain" / "jdk"):
        if (cand / "bin" / "java.exe").exists():
            os.environ["JAVA_HOME"] = str(cand)
            return str(cand)
    return None


def cli_path() -> Path | None:
    base = ROOT / "java" / "build" / "install" / "mcbridge1201" / "bin"
    p = base / ("mcbridge1201.bat" if os.name == "nt" else "mcbridge1201")
    return p if p.exists() else None


def run(cmd: list, timeout=1800) -> tuple[int, str]:
    p = subprocess.run([str(c) for c in cmd], cwd=ROOT, capture_output=True, text=True,
                       errors="replace", timeout=timeout)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8", newline="\n")


def class_majors(jar: Path) -> dict[int, int]:
    counts: dict[int, int] = {}
    with zipfile.ZipFile(jar) as z:
        for name in z.namelist():
            if not name.endswith(".class"):
                continue
            head = z.read(name)[:8]
            if len(head) < 8:
                continue
            major = (head[6] << 8) | head[7]
            counts[major] = counts.get(major, 0) + 1
    return counts


def jar_entry_bytes(jar: Path) -> dict[str, bytes]:
    with zipfile.ZipFile(jar) as z:
        return {n: z.read(n) for n in z.namelist() if n.endswith(".class")}


# Each shape is asserted against the constant pool of one class, which is where a class reference
# or a member name actually lives. A missing string means the fixture does not cover that shape.
SHAPES = [
    ("registration", "mcbfixture/FixtureRegistry.class",
     [b"net/minecraft/class_2378", b"method_10230", b"net/minecraft/class_7923", b"field_41178"]),
    ("constructor", "mcbfixture/FixtureRegistry.class",
     [b"net/minecraft/class_2960", b"<init>"]),
    ("item-nbt", "mcbfixture/FixtureData.class",
     [b"net/minecraft/class_1799", b"method_7969", b"net/minecraft/class_2487"]),
    ("gui-render-hook", "mcbfixture/FixtureScreen.class",
     [b"net/minecraft/class_332", b"method_25294", b"net/minecraft/class_437"]),
    ("mixin-inject", "mcbfixture/mixin/FixtureMixin.class",
     [b"org/spongepowered/asm/mixin/Mixin",
      b"org/spongepowered/asm/mixin/injection/Inject", b"method_7852"]),
    ("indy", "mcbfixture/FixtureIndy.class",
     [b"java/lang/invoke", b"LambdaMetafactory"]),
]


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
    WORK.mkdir(parents=True, exist_ok=True)

    java_home = ensure_java_home()
    cli = cli_path()
    if java_home is None or cli is None:
        write_json(out / "result.json", {"passed": False, "skipped": True,
                                         "reason": "need a JDK and the built CLI (gradle installDist)"})
        print("SKIP: need JDK + CLI", file=sys.stderr)
        return 2

    cases: list[dict] = []

    def add(case_id, goal, expect, rc, extra=None):
        c = {"id": case_id, "goal": goal, "expect": expect, "rc": rc}
        c.update(extra or {})
        cases.append(c)
        print(f"  {case_id}: rc={rc}")

    # ------------------------------------------------------------------ A05
    manifest = json.loads(FIXTURE_MANIFEST.read_text(encoding="utf-8")) if FIXTURE_MANIFEST.is_file() else {}
    actual_sha = sha256(FIXTURE_JAR) if FIXTURE_JAR.is_file() else None
    majors = class_majors(FIXTURE_JAR) if FIXTURE_JAR.is_file() else {}
    add("a05-fixture-pinned",
        "the fixture jar exists and matches the hash recorded in its manifest",
        {"ok": True}, 0,
        {"jar": str(FIXTURE_JAR.relative_to(ROOT)).replace("\\", "/") if FIXTURE_JAR.is_file() else None,
         "sha256": actual_sha, "manifestSha256": (manifest.get("input") or {}).get("sha256"),
         "size": FIXTURE_JAR.stat().st_size if FIXTURE_JAR.is_file() else None,
         "majors": {str(k): v for k, v in majors.items()},
         "ok": bool(actual_sha)
               and actual_sha == (manifest.get("input") or {}).get("sha256")
               and set(majors) == {61}})

    entries = jar_entry_bytes(FIXTURE_JAR) if FIXTURE_JAR.is_file() else {}
    shape_results = {}
    for name, entry, needles in SHAPES:
        data = entries.get(entry, b"")
        missing = [n.decode() for n in needles if n not in data]
        shape_results[name] = {"class": entry, "missing": missing}
    add("a05-shapes-present",
        "each claimed bytecode shape is present in the fixture's constant pools",
        {"allPresent": True}, 0,
        {"shapes": shape_results,
         "allPresent": all(not v["missing"] for v in shape_results.values())})

    plan_src = out / "static-1.20.1.json"
    rc, text = run([cli, "analyze", "--mods", FIXTURE / "out",
                    "--client-jar", "work/target/client-1.20.1.jar",
                    "--mappings", "work/target/intermediary-1.20.1-v2.jar",
                    "--api", "work/target/fabric-loader-0.19.5.jar",
                    "--target", "1.20.1", "--out", str(plan_src)])
    src_counts = {}
    if plan_src.is_file():
        plan = json.loads(plan_src.read_text(encoding="utf-8"))
        src_counts = (plan.get("artifacts") or [{}])[0].get("counts") or {}
    add("a05-static-clean-on-source",
        "the fixture has no static damage against its own 1.20.1 target",
        {"rc": 0, "missingClass": 0, "missingMember": 0}, rc,
        {"counts": src_counts,
         "missingClass": src_counts.get("missingClass"),
         "missingMember": src_counts.get("missingMember"),
         "tail": text.strip().splitlines()[-2:]})

    # ------------------------------------------------------------------ A06
    profile = json.loads(PROFILE_1204.read_text(encoding="utf-8"))
    stub_path = ROOT / profile["indices"]["bridgeStub"]["path"]
    stub_majors = class_majors(stub_path) if stub_path.is_file() else {}
    add("a06-stub-is-java17",
        "the 1.20.4 compile stub carries Java 17 class files (major 61)",
        {"rc": 0, "onlyMajor": 61}, 0,
        {"stub": str(stub_path.relative_to(ROOT)).replace("\\", "/"),
         "majors": {str(k): v for k, v in stub_majors.items()},
         "classes": sum(stub_majors.values())})

    json_1204 = out / "profile-check-1.20.4.json"
    rc, text = run([cli, "profile-check", "--profile", str(PROFILE_1204), "--root", ".",
                    "--json", str(json_1204)])
    codes = []
    if json_1204.is_file():
        report = json.loads(json_1204.read_text(encoding="utf-8"))
        codes = [p["code"] for p in report.get("problems", []) if p.get("severity") == "error"]
    add("a06-no-rule-package-refused",
        "a target with no rule package is refused instead of silently converting nothing",
        {"rc": 3, "code": "pipeline.rule-order-empty"}, rc,
        {"errorCodes": sorted(set(codes)), "tail": text.strip().splitlines()[-2:]})

    json_wrong = out / "profile-check-1.20.4-with-1211-rules.json"
    rule_args = []
    for rel in profile.get("pipeline", {}).get("ruleOrder") or []:
        rule_args += ["--rules", rel]
    if not rule_args:
        rule_args = ["--rules", "rules/fabric-1.21.1/container.json"]
    rc, text = run([cli, "profile-check", "--profile", str(PROFILE_1204), "--root", ".",
                    "--json", str(json_wrong)] + rule_args)
    codes = []
    if json_wrong.is_file():
        report = json.loads(json_wrong.read_text(encoding="utf-8"))
        codes = [p["code"] for p in report.get("problems", []) if p.get("severity") == "error"]
    add("a06-wrong-target-rules-refused",
        "a 1.21.1 rule package cannot be aimed at the 1.20.4 profile",
        {"rc": 3, "code": "rules.target-mismatch"}, rc,
        {"errorCodes": sorted(set(codes)), "tail": text.strip().splitlines()[-2:]})

    plan_1204 = out / "static-1.20.4.json"
    rc, text = run([cli, "analyze", "--mods", FIXTURE / "out",
                    "--client-jar", "work/target/client-1.20.4.jar",
                    "--mappings", "work/target/intermediary-1.20.4-v2.jar",
                    "--api", "work/target/fabric-loader-0.15.11.jar",
                    "--target", "1.20.4", "--out", str(plan_1204)])
    counts = {}
    missing_samples = {}
    if plan_1204.is_file():
        plan = json.loads(plan_1204.read_text(encoding="utf-8"))
        art = (plan.get("artifacts") or [{}])[0]
        counts = art.get("counts") or {}
        for key in ("missingClass", "missingMember", "descMismatch", "missingApiClass"):
            items = art.get(key) or []
            missing_samples[key] = [
                {"owner": i.get("owner"), "name": i.get("name"), "desc": i.get("desc")}
                for i in items[:8]
            ]
    add("a06-break-map",
        "the 1.20.1 fixture is statically diffed against the 1.20.4 index and the breakage is listed",
        {"rc": 0}, rc,
        {"counts": counts, "missing": missing_samples,
         "tail": text.strip().splitlines()[-2:]})

    bridge_out = WORK / "bridges-1204"
    rc, text = run([sys.executable, str(ROOT / "tools" / "build_bridges.py"),
                    "--profile", str(PROFILE_1204), "--out", str(bridge_out)])
    err_lines = [ln for ln in text.splitlines() if ln.strip()]
    compile_errors = len(re.findall(r"错误|error:", text))
    add("a06-bridges-are-target-specific",
        "the 1.21.1 bridge sources do not compile for 1.20.4 (they are a target asset, not a generic one)",
        {"rc_nonzero": True}, rc,
        {"compileErrorsSeen": compile_errors,
         "tail": err_lines[-4:],
         "bridgesProduced": sum(1 for _ in bridge_out.rglob("*.class")) if bridge_out.is_dir() else 0})

    # ------------------------------------------------------------------ verdicts
    for c in cases:
        exp = c["expect"]
        ok = True
        if "ok" in exp:
            ok = ok and bool(c.get("ok"))
        if "allPresent" in exp:
            ok = ok and bool(c.get("allPresent"))
        if "rc" in exp:
            ok = ok and c["rc"] == exp["rc"]
        if "rc_nonzero" in exp:
            ok = ok and c["rc"] != 0
        if "code" in exp:
            ok = ok and exp["code"] in (c.get("errorCodes") or [])
        if "missingClass" in exp:
            ok = ok and c.get("missingClass") == exp["missingClass"]
        if "missingMember" in exp:
            ok = ok and c.get("missingMember") == exp["missingMember"]
        if "onlyMajor" in exp:
            ok = ok and list(c.get("majors", {}).keys()) == [str(exp["onlyMajor"])]
        c["passed"] = ok

    for c in cases:
        print(f"{'PASS' if c['passed'] else 'FAIL'} {c['id']}")

    failed = [c["id"] for c in cases if not c["passed"]]
    result = {
        "workstreams": ["A05 source-side fixture", "A06 1.20.4 architecture probe"],
        "fixture": str(FIXTURE.relative_to(ROOT)).replace("\\", "/"),
        "profile1204": str(PROFILE_1204.relative_to(ROOT)).replace("\\", "/"),
        "javaHome": java_home,
        "cases": cases,
        "passed": not failed,
        "failed": failed,
        "scope": "static/build only. No game was launched: the fixture's source-side runtime "
                 "baseline is pending, not passed, and no 1.20.4 runtime probe was executed.",
    }
    write_json(out / "result.json", result)
    print(f"\nsource fixture + 1.20.4 probe: {'PASS' if not failed else 'FAIL'}"
          f" ({len(cases) - len(failed)}/{len(cases)}) -> {out / 'result.json'}")
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
