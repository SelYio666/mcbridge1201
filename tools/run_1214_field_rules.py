#!/usr/bin/env python3
"""B03 fifth slice: every field-based rule, verified at the constant-pool level.

Covers both field rule packages together:

* `interaction-result`: constants whose type became a record subtype (p256);
* `blockstate-properties`: fields whose type was **deleted** and replaced by a sibling, where the
  bridge returns the common supertype instead (p257).

The second one is the reason this tool exists in generic form. A redirect cannot declare a return
type that no longer exists, so the question "is every remaining mention of the old type gone?"
needs an exact answer - frames included. The tool therefore counts `CONSTANT_Class` entries too,
not just field references: a stack map frame that still named the deleted class would fail
verification even if every instruction was rewritten.

    python tools/run_1214_field_rules.py
"""
from __future__ import annotations

import argparse
import io
import json
import os
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import classpool  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
PROFILE = ROOT / "targets" / "fabric-1.21.4.json"
SAMPLE = ROOT / "work" / "corpus" / "ironchests" / "ironchests-5.0.2-fabric.jar"
DEFAULT_OUT = ROOT / "runs" / "p257-1214-field-rules"
BRIDGE_PREFIX = "top/mcbridge1201/bridge/"

# group -> {owner, bridge, oldDescriptor, members: {field: bridgeMethod}, deletedType?}
GROUPS = {
    "interaction-result": {
        "owner": "net/minecraft/class_1269",
        "oldDescriptor": "Lnet/minecraft/class_1269;",
        "bridge": "top/mcbridge1201/bridge/InteractionResultBridge1214",
        "members": {"field_5811": "field5811", "field_5812": "field5812",
                    "field_21466": "field21466"},
        "deletedType": None,
    },
    "blockstate-properties": {
        "owner": "net/minecraft/class_2741",
        "oldDescriptor": "Lnet/minecraft/class_2753;",
        "bridge": "top/mcbridge1201/bridge/BlockStatePropertiesBridge1214",
        "members": {"field_12481": "field12481", "field_12525": "field12525"},
        "deletedType": "net/minecraft/class_2753",
    },
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


def scan(jar: Path) -> dict:
    """Count stale field refs, stale class names and bridge refs, outer and nested."""
    stats = {"staleFields": 0, "staleTypes": 0, "bridgeRefs": 0, "entries": []}

    def scan_class(data: bytes) -> tuple[int, int, int]:
        stale_fields = 0
        stale_types = 0
        refs = classpool.fieldrefs(data)
        for g in GROUPS.values():
            stale_fields += len([r for r in refs
                                 if r[0] == g["owner"] and r[1] in g["members"]
                                 and r[2] == g["oldDescriptor"]])
            if g["deletedType"]:
                stale_types += len([c for c in classpool.class_names(data)
                                    if c == g["deletedType"]])
        bridge_refs = 0
        for g in GROUPS.values():
            bridge_refs += len([m for m in classpool.methodrefs(data, g["bridge"])
                                if m[1] in g["members"].values()])
        return stale_fields, stale_types, bridge_refs

    with zipfile.ZipFile(jar) as z:
        for name in z.namelist():
            if not name.endswith(".class") or name.startswith(BRIDGE_PREFIX):
                continue
            f, t, b = scan_class(z.read(name))
            if f or t or b:
                stats["entries"].append({"class": name, "staleFields": f,
                                         "staleTypes": t, "bridgeRefs": b})
            stats["staleFields"] += f
            stats["staleTypes"] += t
            stats["bridgeRefs"] += b
        for name in z.namelist():
            if not (name.startswith("META-INF/jars/") and name.endswith(".jar")):
                continue
            with zipfile.ZipFile(io.BytesIO(z.read(name))) as iz:
                f = t = b = 0
                for cn in iz.namelist():
                    if not cn.endswith(".class") or cn.startswith(BRIDGE_PREFIX):
                        continue
                    cf, ct, cb = scan_class(iz.read(cn))
                    f += cf
                    t += ct
                    b += cb
                if f or t or b:
                    stats["entries"].append({"jar": name, "staleFields": f,
                                             "staleTypes": t, "bridgeRefs": b})
                stats["staleFields"] += f
                stats["staleTypes"] += t
                stats["bridgeRefs"] += b
    return stats


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

    bridges = ROOT / "work" / "tmp" / f"bridges-{out.name}"
    if bridges.exists():
        shutil.rmtree(bridges)
    rc_build, _ = run([sys.executable, str(ROOT / "tools" / "build_bridges.py"),
                       "--profile", str(PROFILE), "--out", str(bridges)])
    majors = class_majors(bridges) if bridges.is_dir() else {}

    patched = out / "ironchests-5.0.2-1214-fields.jar"
    rc_patch, patch_log = run([cli, "patch", "--in", SAMPLE, "--out", patched,
                               "--profile", PROFILE, "--rules-from-profile",
                               "--bridge-dir", bridges, "--root", "."])
    applied = {}
    for line in patch_log.splitlines():
        m = re.search(r"rule (\S+) applied (\d+) time", line)
        if m:
            applied[m.group(1)] = int(m.group(2))

    before = scan(SAMPLE)
    after = scan(patched) if patched.is_file() else {"staleFields": -1, "staleTypes": -1,
                                                     "bridgeRefs": 0, "entries": []}

    per_group = {}
    for gid, g in GROUPS.items():
        hits = sum(v for k, v in applied.items() if gid.split("-")[0] in k)
        per_group[gid] = {
            "hits": hits,
            "ruleHits": {k: v for k, v in applied.items() if gid.split("-")[0] in k},
            "staleFieldsAfter": after["staleFields"],
        }

    checks = [
        {"id": "bridges-compile-at-65", "expect": [65], "got": sorted(majors)},
        {"id": "source-had-stale-field-refs", "expect": True, "got": before["staleFields"] > 0},
        {"id": "source-had-deleted-type", "expect": True, "got": before["staleTypes"] > 0},
        {"id": "all-field-rules-fired",
         "expect": True,
         "got": all(any(gid.split("-")[0] in k for k in applied) for gid in GROUPS)},
        {"id": "no-stale-field-ref-left", "expect": 0, "got": after["staleFields"]},
        {"id": "no-deleted-type-left-anywhere", "expect": 0, "got": after["staleTypes"]},
        {"id": "bridge-refs-present", "expect": True, "got": after["bridgeRefs"] > 0},
    ]
    for c in checks:
        c["passed"] = c["got"] == c["expect"]
        print(f"{'PASS' if c['passed'] else 'FAIL'} {c['id']} got={c['got']}")

    passed = all(c["passed"] for c in checks)
    result = {
        "workstream": "B03 fifth slice: all field rules, including a deleted-type replacement",
        "target": PROFILE.relative_to(ROOT).as_posix(),
        "rules": ["rules/fabric-1.21.4/interaction-result.json",
                  "rules/fabric-1.21.4/blockstate-properties.json"],
        "input": SAMPLE.relative_to(ROOT).as_posix(),
        "output": patched.relative_to(ROOT).as_posix(),
        "build": {"rc": rc_build, "majors": {str(k): v for k, v in majors.items()}},
        "patch": {"rc": rc_patch, "applied": applied,
                  "logTail": patch_log.strip().splitlines()[-6:]},
        "constantPool": {"before": before, "after": after},
        "groups": per_group,
        "checks": checks,
        "deletedTypeMethod": {
            "problem": "class_2753 no longer exists in 1.21.4, so a bridge cannot declare a"
                       " return type for it",
            "approach": "return the common supertype class_2769 and let COMPUTE_FRAMES rebuild"
                        " every frame, then assert that no CONSTANT_Class entry still names the"
                        " deleted type - instructions alone would not catch a stale frame",
        },
        "passed": passed,
        "scope": "linkage only: no 1.21.4 runtime, so behaviour is unverified",
    }
    (out / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                                     encoding="utf-8", newline="\n")
    print(f"\nfield rules: {'PASS' if passed else 'FAIL'} -> {out / 'result.json'}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
