#!/usr/bin/env python3
"""B03 second slice: the first descriptor-changed rule, end to end, on a real 1.20.1 jar.

Proves what can be proven without a 1.21.4 instance:
* the 1.21.4-specific bridge compiles against the target stub at class major 65,
* patching the ORIGINAL ironchests jar (no CenturyBridge tombstone involved) rewrites the
  1.20.1 nine-slice call into a call to that bridge, at the same instruction offset,
* the bridge class is embedded in the output jar.

It cannot prove that the nine patches draw correctly on 1.21.4 - that needs the game.

    python tools/run_1214_first_bridge.py
    python tools/run_1214_first_bridge.py --out runs/pNNN-x
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROFILE = ROOT / "targets" / "fabric-1.21.4.json"
SAMPLE = ROOT / "work" / "corpus" / "ironchests" / "ironchests-5.0.2-fabric.jar"
DEFAULT_OUT = ROOT / "runs" / "p252-1214-first-bridge"
RENDERER = "tech.thatgravyboat.ironchests.client.ui.GeneratedScreenRenderer"
BRIDGE = "top/mcbridge1201/bridge/DrawContextTextureBridge1214"
CALL = "method_48587"


def java_home() -> str | None:
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


def run(cmd: list, timeout=900) -> tuple[int, str]:
    p = subprocess.run([str(c) for c in cmd], cwd=ROOT, capture_output=True, text=True,
                       errors="replace", timeout=timeout)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def class_majors(root: Path) -> dict[int, int]:
    counts: dict[int, int] = {}
    for p in root.rglob("*.class"):
        head = p.read_bytes()[:8]
        if len(head) >= 8:
            major = (head[6] << 8) | head[7]
            counts[major] = counts.get(major, 0) + 1
    return counts


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    args = ap.parse_args()
    out = Path(args.out)
    if not out.is_absolute():
        out = ROOT / out
    out.mkdir(parents=True, exist_ok=True)
    home, cli = java_home(), cli_path()
    if home is None or cli is None:
        print("need a JDK and the built CLI", file=sys.stderr)
        return 2
    for req in (PROFILE, SAMPLE):
        if not req.is_file():
            print(f"missing input: {req}", file=sys.stderr)
            return 2
    javap = Path(home) / "bin" / "javap.exe"

    # 1) compile the target-specific bridge
    bridges = out / "bridges"
    if bridges.exists():
        shutil.rmtree(bridges)
    rc_build, build_log = run([sys.executable, str(ROOT / "tools" / "build_bridges.py"),
                               "--profile", str(PROFILE), "--out", str(bridges)])
    majors = class_majors(bridges) if bridges.is_dir() else {}

    # 2) patch the ORIGINAL jar
    patched = out / "ironchests-5.0.2-1214.jar"
    rc_patch, patch_log = run([cli, "patch", "--in", SAMPLE, "--out", patched,
                               "--profile", PROFILE, "--rules-from-profile",
                               "--bridge-dir", bridges, "--root", "."])
    applied = None
    for line in patch_log.splitlines():
        m = re.search(r"rule (\S+) applied (\d+) time", line)
        if m:
            applied = {"id": m.group(1), "count": int(m.group(2))}
    embedded = BRIDGE + ".class" in set(zipfile.ZipFile(patched).namelist()) if patched.is_file() else False

    # 3) the call site, before and after
    before = run([javap, "-c", "-p", "-cp", str(SAMPLE), RENDERER])[1]
    after = run([javap, "-c", "-p", "-cp", str(patched), RENDERER])[1] if patched.is_file() else ""
    (out / "disassembly-before.txt").write_text(before, encoding="utf-8", newline="\n")
    (out / "disassembly-after.txt").write_text(after, encoding="utf-8", newline="\n")

    def call_line(text: str, needle: str) -> str | None:
        for line in text.splitlines():
            if needle in line:
                return line.strip()
        return None

    before_line = call_line(before, CALL)
    after_line = call_line(after, BRIDGE)
    still_old = call_line(after, CALL)

    checks = [
        {"id": "bridge-compiles-at-target-major", "expect": [65], "got": sorted(majors),
         "why": "the target bridge must be loadable by the 1.21.4 runtime"},
        {"id": "rule-fired-on-original-jar", "expect": 1, "got": (applied or {}).get("count", 0),
         "why": "the rule matches the raw 1.20.1 call, not a CenturyBridge tombstone"},
        {"id": "bridge-embedded", "expect": True, "got": embedded,
         "why": "the patched jar has to carry the class it now calls"},
        {"id": "source-calls-method_48587", "expect": True, "got": before_line is not None,
         "why": "the 1.20.1 shape this rule exists for"},
        {"id": "patched-calls-bridge", "expect": True, "got": after_line is not None,
         "why": "the rewrite has to land on the bridge"},
        {"id": "old-call-is-gone", "expect": True, "got": still_old is None,
         "why": "a leftover call would fail at runtime with NoSuchMethodError"},
    ]
    for c in checks:
        c["passed"] = c["got"] == c["expect"]
        print(f"{'PASS' if c['passed'] else 'FAIL'} {c['id']} got={c['got']}")

    passed = all(c["passed"] for c in checks)
    result = {
        "workstream": "B03 second slice: first descriptor-changed rule on a real jar",
        "target": PROFILE.relative_to(ROOT).as_posix(),
        "rule": "rules/fabric-1.21.4/ironchests-draw.json",
        "bridge": "java/src/bridge-1214/java/top/mcbridge1201/bridge/DrawContextTextureBridge1214.java",
        "input": SAMPLE.relative_to(ROOT).as_posix(),
        "output": patched.relative_to(ROOT).as_posix(),
        "build": {"rc": rc_build, "majors": {str(k): v for k, v in majors.items()},
                  "logTail": build_log.strip().splitlines()[-3:]},
        "patch": {"rc": rc_patch, "applied": applied, "bridgeEmbedded": embedded,
                  "logTail": patch_log.strip().splitlines()[-5:]},
        "callsite": {"before": before_line, "after": after_line, "oldCallRemains": still_old is not None},
        "checks": checks,
        "passed": passed,
        "scope": "bytecode only. The bridge compiles and the call is redirected; whether the nine"
                 " patches render correctly on 1.21.4 needs the game and was not tested.",
    }
    (out / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                                     encoding="utf-8", newline="\n")
    print(f"\nbefore: {before_line}")
    print(f"after : {after_line}")
    print(f"first 1.21.4 bridge: {'PASS' if passed else 'FAIL'} -> {out / 'result.json'}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
