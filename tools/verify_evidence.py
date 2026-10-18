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

    tracked = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True)
    jars = [line for line in tracked.stdout.splitlines() if line.endswith(".jar")]
    checks["no_tracked_jars"] = not jars
    details["tracked_jars"] = jars

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
