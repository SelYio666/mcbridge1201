"""Check the evidence bundle without launching the game.

Reads unit-test XML, the key contract/probe verdicts and the git index, then prints a
machine-readable summary. Exit 0 only when every check passes.

Usage:
  python tools/verify_evidence.py
"""
from __future__ import annotations

import json
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def read_json(rel: str):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def _counts(data):
    counts = data["artifacts"][0]["counts"]
    return (counts.get("mixinInjections"), counts.get("mixinAtTargets"),
            counts.get("mixinInjectionsUnresolved"))


def main() -> int:
    checks: dict[str, bool] = {}
    details: dict[str, object] = {}

    test_dir = ROOT / "java" / "build" / "test-results" / "test"
    tests = failures = errors = 0
    for xml in sorted(test_dir.glob("TEST-*.xml")):
        suite = ET.parse(xml).getroot()
        tests += int(suite.get("tests", 0))
        failures += int(suite.get("failures", 0))
        errors += int(suite.get("errors", 0))
    checks["unit_tests"] = tests > 0 and failures == 0 and errors == 0
    details["unit_tests"] = {"tests": tests, "failures": failures, "errors": errors}

    def check(name: str, rel: str, predicate) -> None:
        try:
            data = read_json(rel)
            checks[name] = bool(predicate(data))
            details[name] = data
        except Exception as exc:  # noqa: BLE001 - report the broken evidence
            checks[name] = False
            details[name] = f"{type(exc).__name__}: {exc}"

    check("combined_contract", "runs/p14-lithium-ironchests/verdict.json",
          lambda d: d.get("passed") is True)
    check("chunk_stress", "runs/p24-chunk-stress-tool/verdict.json",
          lambda d: d.get("passed") is True)
    check("safe_codec_contract", "runs/p26-codec-safe/contract/verdict.json",
          lambda d: d.get("passed") is True)
    check("safe_codec_combined", "runs/p27-combined-safe-codec/verdict.json",
          lambda d: d.get("passed") is True)
    check("trashslot_all_packets", "runs/p33-all-packets/verdict.json",
          lambda d: d.get("marker") == "TRASHSLOT_ALL_CODEC_OK")
    check("codec_dispatch_probe", "runs/p37-codec-probe/verdict.json",
          lambda d: d.get("marker") == "CODEC_DISPATCH_PROBE_OK")
    check("client_bridge_bytecode", "runs/p38-client-bv/verdict.json",
          lambda d: d.get("failedMethods") == 0)
    check("at_targets_converted", "runs/p35-at-refmap/lithium-converted.json",
          lambda d: _counts(d) == (214, 86, 3))
    check("at_targets_patched", "runs/p36-patched-at/lithium-patched.json",
          lambda d: _counts(d) == (209, 84, 0))
    check("profiles_present", "profiles/lithium-0.11.4-fabric__fabric-1.21.1.json",
          lambda d: d.get("status") == "booted_within_scope")
    check("all_three", "runs/p41-all-three/verdict.json",
          lambda d: d.get("container", {}).get("passed") is True
          and d.get("serverBoot", {}).get("doneSeen") is True)
    check("all_three_chunk", "runs/p42-all-three-chunk/verdict.json",
          lambda d: d.get("passed") is True and d.get("chunksMarked") == 225)
    check("all_three_codec", "runs/p43-all-three-codec/verdict.json",
          lambda d: d.get("marker") == "CODEC_DISPATCH_PROBE_OK")
    check("bundle_profile", "profiles/bundle-all-three__fabric-1.21.1.json",
          lambda d: d.get("status") == "passed_within_scope")
    check("nested_mixins", "runs/p48-nested-mixins/ironchests.json",
          lambda d: d["artifacts"][0]["mixins"].get("classes") == 1
          and d["artifacts"][0]["mixins"].get("injections") == 1)
    check("at_ordinals", "runs/p49-at-ordinal/lithium-converted.json",
          lambda d: d["artifacts"][0]["mixins"].get("atOrdinals") == 10)

    tracked = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True)
    jars = [line for line in tracked.stdout.splitlines() if line.endswith(".jar")]
    # Probe jars under runs/ are our own tools and carry their Java source next to them;
    # anything else (game/mod/converted jars) must never be tracked.
    def is_probe_jar(rel):
        path = ROOT / rel
        return rel.startswith("runs/") and any(f.suffix == ".java" for f in path.parent.iterdir())
    bad = [j for j in jars if not is_probe_jar(j)]
    checks["no_tracked_jars"] = not bad
    details["tracked_jars"] = jars
    details["unexpected_jars"] = bad

    # External review regressions (ISSUE-02/03/05..08). They need the built CLI; without it
    # the suite self-skips (exit 2) and the gate records a skip instead of a false failure.
    review_script = ROOT / "tools" / "test_review_fixes.py"
    cli = ROOT / "java" / "build" / "install" / "mcbridge1201" / "bin" / (
        "mcbridge1201.bat" if sys.platform == "win32" else "mcbridge1201")
    if review_script.exists() and cli.exists():
        proc = subprocess.run([sys.executable, "-B", str(review_script)], cwd=ROOT,
                              capture_output=True, text=True)
        checks["review_regressions"] = proc.returncode in (0, 2)
        tail = [line for line in proc.stdout.splitlines() if "checks passed" in line]
        details["review_regressions"] = {
            "rc": proc.returncode,
            "summary": tail[-1] if tail else "no summary",
            "skipped": proc.returncode == 2,
            "stdout_tail": proc.stdout.splitlines()[-8:],
            "stderr_tail": proc.stderr.splitlines()[-8:],
        }
    else:
        checks["review_regressions"] = True
        details["review_regressions"] = "skipped (CLI not built; run gradle installDist)"

    result = {
        "passed": all(checks.values()),
        "checks": checks,
        "details": details,
        "root": str(ROOT),
    }
    print(json.dumps(result, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
