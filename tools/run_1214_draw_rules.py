#!/usr/bin/env python3
"""B03 third slice: all three draw rules on the original ironchests jar.

p252 closed the nine-slice call; this adds the two plain blits that 1.21.4 re-signatured. The
whole draw path of the mod is now rewritten on a 1.20.1 jar without a CenturyBridge tombstone.

What it proves: the bridges compile at the target class level, every old draw call is gone, and
each call site points at a bridge. What it does NOT prove: that anything renders correctly - the
7-argument blit reproduces 1.20.1's convenience overload with texture 256x256, which is a
convention read from the vanilla forwarding shape, not a measurement.

    python tools/run_1214_draw_rules.py
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
DEFAULT_OUT = ROOT / "runs" / "p254-1214-draw-rules"

# rule id -> (old member, bridge class, classes that must stop calling the old member)
RULES = {
    "ironchests.draw-nine-sliced-1214": ("method_48587", "DrawContextTextureBridge1214",
                                         ["GeneratedScreenRenderer"]),
    "ironchests.blit-region-1214": ("method_25290", "DrawContextBlitBridge1214",
                                    ["TexturedScreenRenderer"]),
    "ironchests.blit-simple-1214": ("method_25302", "DrawContextBlitBridge1214",
                                    ["GeneratedScreenRenderer"]),
}
CLASSES = {
    "TexturedScreenRenderer": "tech.thatgravyboat.ironchests.client.ui.TexturedScreenRenderer",
    "GeneratedScreenRenderer": "tech.thatgravyboat.ironchests.client.ui.GeneratedScreenRenderer",
}


def java_home() -> str | None:
    env = os.environ.get("JAVA_HOME")
    if env and (Path(env) / "bin" / "javap.exe").exists():
        return env
    for cand in (ROOT.parent / ".toolchain" / "jdk", ROOT / ".toolchain" / "jdk"):
        if (cand / "bin" / "javap.exe").exists():
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
    javap = str(Path(home) / "bin" / "javap.exe")

    bridges = out / "bridges"
    if bridges.exists():
        shutil.rmtree(bridges)
    rc_build, build_log = run([sys.executable, str(ROOT / "tools" / "build_bridges.py"),
                               "--profile", str(PROFILE), "--out", str(bridges)])
    majors = class_majors(bridges) if bridges.is_dir() else {}

    patched = out / "ironchests-5.0.2-1214-draw.jar"
    rc_patch, patch_log = run([cli, "patch", "--in", SAMPLE, "--out", patched,
                               "--profile", PROFILE, "--rules-from-profile",
                               "--bridge-dir", bridges, "--root", "."])
    applied = {}
    for line in patch_log.splitlines():
        m = re.search(r"rule (\S+) applied (\d+) time", line)
        if m:
            applied[m.group(1)] = int(m.group(2))
    changed = None
    for line in patch_log.splitlines():
        m = re.search(r"classes changed=(\d+)", line)
        if m:
            changed = int(m.group(1))
    embedded = []
    if patched.is_file():
        with zipfile.ZipFile(patched) as z:
            embedded = [n for n in z.namelist() if n.startswith("top/mcbridge1201/bridge/")]

    # Old calls must be gone, new ones present, in every class that used them.
    per_class = {}
    for short, internal in CLASSES.items():
        before = run([javap, "-c", "-p", "-cp", str(SAMPLE), internal])[1]
        after = run([javap, "-c", "-p", "-cp", str(patched), internal])[1]
        (out / f"disassembly-{short}-before.txt").write_text(before, encoding="utf-8", newline="\n")
        (out / f"disassembly-{short}-after.txt").write_text(after, encoding="utf-8", newline="\n")
        old_members = [r[0] for r in RULES.values()]
        per_class[short] = {
            "oldCallsBefore": {m: before.count(m) for m in old_members if m in before},
            "oldCallsAfter": {m: after.count(m) for m in old_members if m in after},
            "bridgeCallsAfter": {b: after.count(b) for b in
                                 {r[1] for r in RULES.values()} if b in after},
        }

    # The patch recurses into META-INF/jars/; the outer-class disassembly cannot see those, so the
    # nested level is counted from the jar bytes directly.
    nested = {"oldCallsAfter": 0, "bridgePresent": 0, "entries": []}
    if patched.is_file():
        import io
        old_names = [r[0] for r in RULES.values()]
        with zipfile.ZipFile(patched) as z:
            for n in z.namelist():
                if not (n.startswith("META-INF/jars/") and n.endswith(".jar")):
                    continue
                with zipfile.ZipFile(io.BytesIO(z.read(n))) as iz:
                    hit_old = 0
                    hit_bridge = 0
                    for cn in iz.namelist():
                        if not cn.endswith(".class"):
                            continue
                        if cn.startswith("top/mcbridge1201/bridge/"):
                            # The bridge itself calls the NEW signature, so its constant pool
                            # mentions the same member names. Counting it as a leftover would
                            # report every correctly patched jar as broken.
                            continue
                        d = iz.read(cn)
                        hit_old += sum(1 for m in old_names if m.encode() in d)
                        hit_bridge += sum(1 for b in {r[1] for r in RULES.values()} if b.encode() in d)
                    if hit_old or hit_bridge:
                        nested["entries"].append({"jar": n, "oldCalls": hit_old,
                                                   "bridgeRefs": hit_bridge})
                        nested["oldCallsAfter"] += hit_old
                        nested["bridgePresent"] += hit_bridge
    old_left = (sum(sum(v["oldCallsAfter"].values()) for v in per_class.values())
                + nested["oldCallsAfter"])
    bridge_calls = sum(sum(v["bridgeCallsAfter"].values()) for v in per_class.values())
    expected = sum(applied.values())

    checks = [
        {"id": "bridges-compile-at-65", "expect": [65], "got": sorted(majors),
         "why": "both target bridges must be loadable by 1.21.4"},
        {"id": "all-three-rules-fired",
         "expect": {"ironchests.draw-nine-sliced-1214": 1,
                     "ironchests.blit-region-1214": 2,
                     "ironchests.blit-simple-1214": 3},
         "got": applied,
         "why": "nine-slice 1, region blit 2, simple blit 3 - the call sites measured with refs"},
        {"id": "three-classes-changed", "expect": 3, "got": changed,
         "why": "only the two renderers should move"},
        {"id": "both-bridges-embedded", "expect": 2,
         "got": len({n for n in embedded if n.endswith(".class")}),
         "why": "the patched jar carries every class it now calls"},
        {"id": "no-old-call-left", "expect": 0, "got": old_left,
         "why": "a leftover draw call would be a NoSuchMethodError at runtime"},
        {"id": "outer-classes-rewritten", "expect": 5, "got": bridge_calls,
         "why": "the two outer renderers hold 5 of the 6 rewritten call sites"},
        {"id": "nested-jar-rewritten", "expect": True,
         "got": nested["oldCallsAfter"] == 0 and nested["bridgePresent"] >= 1,
         "why": "the six-times-applied rule count includes one call inside ResourcefulLib; the" 
                " patched nested jar must reference the bridge and no longer the old member"},
    ]
    for c in checks:
        c["passed"] = c["got"] == c["expect"]
        print(f"{'PASS' if c['passed'] else 'FAIL'} {c['id']} got={c['got']} expect={c['expect']}")

    passed = all(c["passed"] for c in checks)
    result = {
        "workstream": "B03 third slice: both plain blits plus the nine-slice, on the original jar",
        "target": PROFILE.relative_to(ROOT).as_posix(),
        "rules": {k: {"old": v[0], "bridge": v[1]} for k, v in RULES.items()},
        "input": SAMPLE.relative_to(ROOT).as_posix(),
        "output": patched.relative_to(ROOT).as_posix(),
        "build": {"rc": rc_build, "majors": {str(k): v for k, v in majors.items()}},
        "patch": {"rc": rc_patch, "applied": applied, "classesChanged": changed,
                  "bridgeClasses": embedded, "logTail": patch_log.strip().splitlines()[-6:]},
        "bytecode": per_class,
        "nestedJars": nested,
        "callSiteBookkeeping": {"appliedTotal": expected, "outerVisible": bridge_calls,
                                 "nestedVisible": nested["bridgePresent"]},
        "checks": checks,
        "openAssumption": "blitSimple reproduces 1.20.1's 7-argument overload with region = the"
                          " destination size and texture = 256x256. That is the vanilla forwarding"
                          " convention, not a measurement; a texture atlas larger than 256 would"
                          " sample the wrong texels, and only a game run can falsify it.",
        "passed": passed,
        "scope": "bytecode only: no 1.21.4 runtime was started, so rendering correctness is"
                 " unverified.",
    }
    (out / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                                     encoding="utf-8", newline="\n")
    print(f"\napplied {applied}; old calls left {old_left}; bridge calls {bridge_calls}")
    print(f"draw rules: {'PASS' if passed else 'FAIL'} -> {out / 'result.json'}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
