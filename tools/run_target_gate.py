#!/usr/bin/env python3
"""Exercise the target gate: one accepted run and the negatives that must be refused.

This is the executable form of A02's release criterion ("错目标、错 namespace、缺依赖负例失败").
It converts nothing and launches no game: every case is a dry run, so the evidence says what it
proves and nothing more.

    python tools/run_target_gate.py
    python tools/run_target_gate.py --out runs/p243-target-profile-gate

Each case records the exit code and the problem codes the CLI actually reported, and the run
fails when a negative case passes or reports a different reason than the one it aims at.
Exit 0 only when every case behaves as declared.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORK = ROOT / "work" / "tmp" / "p243-target-gate"
PROFILE = ROOT / "targets" / "fabric-1.21.1.json"
RULES = ROOT / "rules" / "fabric-1.21.1"
DEFAULT_OUT = ROOT / "runs" / "p243-target-profile-gate"


def cli_path() -> Path | None:
    base = ROOT / "java" / "build" / "install" / "mcbridge1201" / "bin"
    p = base / ("mcbridge1201.bat" if os.name == "nt" else "mcbridge1201")
    return p if p.exists() else None


def ensure_java_home() -> str | None:
    env = os.environ.get("JAVA_HOME")
    if env and (Path(env) / "bin" / ("java.exe" if os.name == "nt" else "java")).exists():
        return env
    for cand in (ROOT.parent / ".toolchain" / "jdk", ROOT / ".toolchain" / "jdk"):
        if (cand / "bin" / "java.exe").exists():
            os.environ["JAVA_HOME"] = str(cand)
            return str(cand)
    return None


def run(cmd: list[str]) -> tuple[int, str]:
    p = subprocess.run([str(c) for c in cmd], cwd=ROOT, capture_output=True, text=True,
                       errors="replace", timeout=600)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
                    newline="\n")


# --------------------------------------------------------------------------- fixtures

def minimal_rule(target: str, owner: str, rid: str) -> dict:
    return {
        "schemaVersion": "0.1-draft",
        "target": target,
        "fieldRedirects": [{
            "id": rid,
            "sourceOwner": owner,
            "sourceName": "field_1",
            "bridgeClass": "top/mcbridge1201/bridge/GateFixture",
            "bridgeMethod": "noop",
            "bridgeDesc": "()V",
            "capability": "fixture.only",
            "risk": "low",
            "evidence": "synthetic fixture for the target gate; it never matches a real class",
        }],
    }


def build_fixtures() -> dict:
    if WORK.exists():
        shutil.rmtree(WORK)
    WORK.mkdir(parents=True)

    base = json.loads(PROFILE.read_text(encoding="utf-8"))

    def write_profile(name: str, mutate) -> Path:
        data = json.loads(json.dumps(base))
        mutate(data)
        p = WORK / name
        write_json(p, data)
        return p

    owner_ok = "net/minecraft/class_1"
    write_json(WORK / "rule-other-target.json", minimal_rule("fabric-1.21.4", owner_ok, "gate.other-target"))
    write_json(WORK / "rule-official-ns.json", minimal_rule("fabric-1.21.1", "net/minecraft/world/entity/Entity", "gate.official-ns"))
    write_json(WORK / "rule-a.json", minimal_rule("fabric-1.21.1", owner_ok, "gate.a"))
    write_json(WORK / "rule-b.json", minimal_rule("fabric-1.21.1", owner_ok, "gate.b"))

    bad_hash = write_profile("profile-bad-index-hash.json",
                             lambda d: d["indices"]["clientJar"].__setitem__("sha256", "0" * 64))

    def drop_index(d):
        d["indices"]["clientJar"]["path"] = "work/tmp/p243-target-gate/no-such-client.jar"
    missing_index = write_profile("profile-missing-index.json", drop_index)

    def reorder(d):
        d["pipeline"]["ruleOrder"] = ["rule-b.json", "rule-a.json"]
    reordered = write_profile("profile-reordered-rules.json", reorder)

    bridges = WORK / "bridges-too-new"
    bridges.mkdir()
    (bridges / "TooNew.class").write_bytes(bytes([0xCA, 0xFE, 0xBA, 0xBE, 0, 0, 0, 69]))

    tiny = WORK / "tiny-input.jar"
    with zipfile.ZipFile(tiny, "w") as z:
        z.writestr("fixture.txt", "not a mod; the gate must refuse before touching it\n")

    return {
        "profile": base,
        "bad_hash": bad_hash,
        "missing_index": missing_index,
        "reordered": reordered,
        "bridges": bridges,
        "tiny_jar": tiny,
    }


# --------------------------------------------------------------------------- cases

def profile_check(cli: Path, profile: Path, extra: list[str], out_json: Path) -> tuple[int, str]:
    cmd = [cli, "profile-check", "--profile", profile, "--root", ".", "--json", out_json] + extra
    return run(cmd)


def case_positive(cli: Path, out: Path) -> dict:
    rc, text = profile_check(cli, PROFILE, ["--rules-from-profile"], out / "profile-check-positive.json")
    return {"id": "positive-frozen-profile", "goal": "the frozen profile accepts its own rule package",
            "expect": {"rc": 0, "codes_absent": ["rules.target-mismatch", "rules.namespace-mismatch",
                                                 "indices.hash-mismatch", "rules.order-mismatch"]},
            "rc": rc, "output": text.strip().splitlines()[-2:]}


def case_negative(cli: Path, out: Path, case_id: str, goal: str, profile: Path,
                  extra: list[str], want_code: str) -> dict:
    json_path = out / f"profile-check-{case_id}.json"
    rc, text = profile_check(cli, profile, extra, json_path)
    codes = []
    if json_path.is_file():
        report = json.loads(json_path.read_text(encoding="utf-8"))
        codes = [p["code"] for p in report.get("problems", []) if p.get("severity") == "error"]
    return {"id": case_id, "goal": goal, "expect": {"rc": 3, "code": want_code},
            "rc": rc, "errorCodes": sorted(set(codes)), "output": text.strip().splitlines()[-2:]}


def case_patch_refuses(cli: Path, out: Path, fx: dict) -> dict:
    """The conversion path must refuse before it writes anything."""
    out_jar = WORK / "must-not-exist.jar"
    if out_jar.exists():
        out_jar.unlink()
    rc, text = run([cli, "patch", "--in", fx["tiny_jar"], "--out", out_jar,
                    "--profile", fx["bad_hash"], "--rules-from-profile", "--root", "."])
    return {"id": "patch-refuses-before-writing", "goal": "patch --profile stops before writing a jar",
            "expect": {"rc": 2, "output_exists": False},
            "rc": rc, "outputExists": out_jar.exists(), "output": text.strip().splitlines()[-3:]}


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

    cli = cli_path()
    if cli is None:
        write_json(out / "result.json", {"passed": False, "skipped": True,
                                         "reason": "CLI not built; run gradle installDist"})
        print("SKIP: CLI not built (java/build/install/mcbridge1201)", file=sys.stderr)
        return 2
    java_home = ensure_java_home()
    if java_home is None:
        write_json(out / "result.json", {"passed": False, "skipped": True,
                                         "reason": "no JDK found; set JAVA_HOME"})
        print("SKIP: no JDK found", file=sys.stderr)
        return 2

    fx = build_fixtures()
    cases = [case_positive(cli, out)]

    neg = [
        ("wrong-target", "a rule package built for another target is refused", PROFILE,
         ["--rules", str(WORK / "rule-other-target.json")], "rules.target-mismatch"),
        ("wrong-namespace", "rules written in another namespace are refused", PROFILE,
         ["--rules", str(WORK / "rule-official-ns.json")], "rules.namespace-mismatch"),
        ("index-hash", "an index whose bytes differ from the frozen hash is refused", fx["bad_hash"],
         ["--rules-from-profile"], "indices.hash-mismatch"),
        ("index-missing", "a missing target index is refused", fx["missing_index"],
         ["--rules-from-profile"], "indices.missing"),
        ("bridge-class-version", "a bridge compiled above the target Java level is refused", PROFILE,
         ["--rules-from-profile", "--bridge-dir", str(fx["bridges"])], "bridge.class-version"),
    ]
    for case_id, goal, profile, extra, code in neg:
        cases.append(case_negative(cli, out, case_id, goal, profile, extra, code))

    # Order: the profile says rule-b then rule-a; the call passes a then b.
    cases.append(case_negative(cli, out, "rule-order",
                              "a rule package passed in another order than the profile's is refused",
                              fx["reordered"], ["--rules", str(WORK / "rule-a.json"),
                                                "--rules", str(WORK / "rule-b.json")],
                              "rules.order-mismatch"))
    cases.append(case_patch_refuses(cli, out, fx))

    for c in cases:
        exp = c["expect"]
        ok = c["rc"] == exp["rc"]
        if "code" in exp:
            ok = ok and exp["code"] in (c.get("errorCodes") or [])
        if "codes_absent" in exp:
            ok = ok and not (set(exp["codes_absent"]) & set(c.get("errorCodes") or []))
        if "output_exists" in exp:
            ok = ok and c.get("outputExists") == exp["output_exists"]
        c["passed"] = ok
        print(f"{'PASS' if ok else 'FAIL'} {c['id']}  rc={c['rc']} expected={exp['rc']}")

    passed = all(c["passed"] for c in cases)
    result = {
        "gate": "target-profile",
        "profile": str(PROFILE.relative_to(ROOT)).replace("\\", "/"),
        "cli": str(cli.relative_to(ROOT)).replace("\\", "/"),
        "javaHome": java_home,
        "cases": cases,
        "passed": passed,
        "scope": "dry runs only: no jar was converted and no game was launched",
    }
    write_json(out / "result.json", result)
    print(f"\ntarget gate: {'PASS' if passed else 'FAIL'} ({len(cases)} cases) -> {out / 'result.json'}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
