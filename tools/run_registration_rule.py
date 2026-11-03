#!/usr/bin/env python3
"""B03 first slice: prove the registry-key rule actually rewrites the fixture's registration site.

    python tools/run_registration_rule.py
    python tools/run_registration_rule.py --out runs/p249-registration-key-rule

What this can prove without a 1.21.4 instance: the patched class calls
`Settings.registryKey(RegistryKey)` and does it *before* the item constructor, with the key built
from the registry's own resource key and the id that is about to be registered. What it cannot
prove here: that a 1.21.4 runtime no longer raises "Item id not set" - that needs a game.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = ROOT / "fixtures" / "source-fabric-1.20.1" / "out" / "mcbfixture-1.0.0.jar"
PROFILE = ROOT / "targets" / "fabric-1.21.4.json"
RULE = ROOT / "rules" / "fabric-1.21.4" / "registration-key.json"
DEFAULT_OUT = ROOT / "runs" / "p249-registration-key-rule"
TARGET_CLASS = "mcbfixture/FixtureRegistry.class"

SETTER = "method_63686"
KEY_FACTORY = "method_29179"
REGISTRY_KEY = "method_30517"
ITEM_CTOR_OWNER = "net/minecraft/class_1792"


def sha256(path: Path) -> str:
    import hashlib
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


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


def run(cmd: list, timeout=600) -> tuple[int, str]:
    p = subprocess.run([str(c) for c in cmd], cwd=ROOT, capture_output=True, text=True,
                       errors="replace", timeout=timeout)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def instruction_index(disassembly: str, needle: str) -> int:
    """Bytecode offset of the first line mentioning `needle`, or -1."""
    for line in disassembly.splitlines():
        m = re.match(r"\s*(\d+):\s", line)
        if m and needle in line:
            return int(m.group(1))
    return -1


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
        print("need a JDK and the built CLI (gradle installDist)", file=sys.stderr)
        return 2
    for required in (FIXTURE, PROFILE, RULE):
        if not required.is_file():
            print(f"missing input: {required}", file=sys.stderr)
            return 2
    javap = Path(home) / "bin" / "javap.exe"

    patched = out / "fixture-1.21.4.jar"
    rc, text = run([cli, "patch", "--in", FIXTURE, "--out", patched,
                    "--profile", PROFILE, "--rules-from-profile", "--root", "."])
    patch_log = text.strip().splitlines()
    applied = None
    for line in patch_log:
        m = re.search(r"rule (\S+) applied (\d+) time", line)
        if m:
            applied = {"id": m.group(1), "count": int(m.group(2))}
    changed = None
    for line in patch_log:
        m = re.search(r"classes changed=(\d+)", line)
        if m:
            changed = int(m.group(1))

    dis_src = run([javap, "-c", "-p", "-cp", str(FIXTURE), "mcbfixture.FixtureRegistry"])[1]
    dis_patched = run([javap, "-c", "-p", "-cp", str(patched), "mcbfixture.FixtureRegistry"])[1]
    (out / "disassembly-before.txt").write_text(dis_src, encoding="utf-8", newline="\n")
    (out / "disassembly-after.txt").write_text(dis_patched, encoding="utf-8", newline="\n")

    before = {k: instruction_index(dis_src, token) for k, token in
              (("setter", SETTER), ("keyFactory", KEY_FACTORY), ("registryKey", REGISTRY_KEY))}
    after = {k: instruction_index(dis_patched, token) for k, token in
             (("setter", SETTER), ("keyFactory", KEY_FACTORY), ("registryKey", REGISTRY_KEY))}
    item_ctor = None
    for line in dis_patched.splitlines():
        m = re.match(r"\s*(\d+):\s.*invokespecial.*" + re.escape(ITEM_CTOR_OWNER) + r'."<init>"', line)
        if m:
            item_ctor = int(m.group(1))
            break

    checks = [
        {"id": "rule-fired", "expect": 1, "got": (applied or {}).get("count", 0),
         "why": "the fixture's registration site must be recognised"},
        {"id": "one-class-changed", "expect": 1, "got": changed,
         "why": "only the registration class should change"},
        {"id": "source-has-no-setter", "expect": -1, "got": before["setter"],
         "why": "a 1.20.1 source never calls the key setter"},
        {"id": "patched-calls-setter", "expect": ">=0", "got": after["setter"],
         "why": "the conversion has to add the call"},
        {"id": "key-built-before-setter", "expect": True,
         "got": after["keyFactory"] >= 0 and after["keyFactory"] < after["setter"],
         "why": "the key must exist before it is applied"},
        {"id": "registry-key-read-before-factory", "expect": True,
         "got": after["registryKey"] >= 0 and after["registryKey"] < after["keyFactory"],
         "why": "the resource key comes from the registry instance"},
        {"id": "setter-before-item-constructor", "expect": True,
         "got": item_ctor is not None and after["setter"] < item_ctor,
         "why": "the settings must be keyed before the item consumes them"},
    ]

    def ok(c):
        v, g = c["expect"], c["got"]
        if v == ">=0":
            return isinstance(g, int) and g >= 0
        return g == v

    for c in checks:
        c["passed"] = ok(c)
        print(f"{'PASS' if c['passed'] else 'FAIL'} {c['id']} got={c['got']} expect={c['expect']}")

    passed = all(c["passed"] for c in checks)
    result = {
        "workstream": "B03 first slice: registry-key injection",
        "target": {"profile": PROFILE.relative_to(ROOT).as_posix(),
                   "rule": RULE.relative_to(ROOT).as_posix()},
        "input": {"jar": FIXTURE.relative_to(ROOT).as_posix(), "sha256": sha256(FIXTURE)},
        "output": {"jar": patched.relative_to(ROOT).as_posix(), "sha256": sha256(patched)},
        "patch": {"rc": rc, "applied": applied, "classesChanged": changed, "log": patch_log[-6:]},
        "bytecode": {"before": before, "after": after, "itemCtorOffset": item_ctor},
        "checks": checks,
        "passed": passed,
        "scope": "bytecode verification only. No 1.21.4 runtime was started, so 'Item id not set'"
                 " is not proven gone; and one rule is not a conversion.",
    }
    (out / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                                     encoding="utf-8", newline="\n")
    print(f"\nregistration-key rule: {'PASS' if passed else 'FAIL'} -> {out / 'result.json'}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
