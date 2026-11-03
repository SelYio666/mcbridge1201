#!/usr/bin/env python3
"""B03 fourth slice: InteractionResult constants via a bridge, verified at the constant-pool level.

1.21.4 declares InteractionResult's constants as record subtypes, so a 1.20.1
`GETSTATIC class_1269.field_5811 : Lclass_1269;` fails with NoSuchFieldError even though the value
would be assignable (runs/p255 measured that). Each access is redirected to
`InteractionResultBridge1214.field58xx()`, which reads the target field and widens it back.

Verification here is exact rather than textual: the tool parses each patched class's constant pool
and counts `Fieldref(class_1269, field_58xx, Lclass_1269;)` entries. A substring match on the class
bytes would also hit the bridge's own pool and the string tables, which is how p254 briefly
reported a correct jar as broken.

    python tools/run_1214_interaction_bridge.py
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import struct
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROFILE = ROOT / "targets" / "fabric-1.21.4.json"
SAMPLE = ROOT / "work" / "corpus" / "ironchests" / "ironchests-5.0.2-fabric.jar"
DEFAULT_OUT = ROOT / "runs" / "p256-1214-interaction-result"

OWNER = "net/minecraft/class_1269"
OWNER_DESC = "Lnet/minecraft/class_1269;"
FIELDS = ("field_5811", "field_5812", "field_21466")
BRIDGE = "top/mcbridge1201/bridge/InteractionResultBridge1214"
BRIDGE_METHODS = ("field5811", "field5812", "field21466")
BRIDGE_DESC = "()" + OWNER_DESC


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


# --------------------------------------------------------------------------- constant pool

def _items(data: bytes, count: int, pos: int):
    """Yield (index, tag, payload) for a class file constant pool."""
    out = {}
    i = 1
    while i < count:
        tag = data[pos]
        pos += 1
        if tag == 1:  # Utf8
            length = struct.unpack_from(">H", data, pos)[0]
            pos += 2
            out[i] = (1, data[pos:pos + length].decode("utf-8", errors="replace"))
            pos += length
        elif tag in (7, 8, 16, 19, 20):  # Class, String, MethodType, Module, Package
            out[i] = (tag, struct.unpack_from(">H", data, pos)[0])
            pos += 2
        elif tag in (15,):  # MethodHandle
            out[i] = (tag, struct.unpack_from(">BH", data, pos))
            pos += 3
        elif tag in (3, 4, 9, 10, 11, 12, 17, 18):
            out[i] = (tag, struct.unpack_from(">HH", data, pos))
            pos += 4
        elif tag in (5, 6):  # long / double take two slots
            pos += 8
            i += 1
        else:
            raise ValueError(f"unknown constant pool tag {tag} at {pos}")
        i += 1
    return out, pos


def fieldrefs(data: bytes) -> list[tuple[str, str, str]]:
    """Every Fieldref in a class, as (owner, name, descriptor)."""
    count = struct.unpack_from(">H", data, 8)[0]
    pool, _ = _items(data, count, 10)
    out = []
    for idx, (tag, payload) in pool.items():
        if tag != 9:
            continue
        class_idx, nat_idx = payload
        owner_entry = pool.get(class_idx)
        nat_entry = pool.get(nat_idx)
        if not owner_entry or not nat_entry:
            continue
        if nat_entry[0] != 12:
            continue
        name_idx, desc_idx = nat_entry[1]
        name_entry = pool.get(name_idx)
        desc_entry = pool.get(desc_idx)
        owner_utf8 = pool.get(owner_entry[1])
        if not (name_entry and desc_entry and owner_utf8):
            continue
        out.append((owner_utf8[1], name_entry[1], desc_entry[1]))
    return out


def methodrefs(data: bytes, owner: str) -> list[tuple[str, str]]:
    """Every Methodref on `owner`, as (name, descriptor)."""
    count = struct.unpack_from(">H", data, 8)[0]
    pool, _ = _items(data, count, 10)
    out = []
    for idx, (tag, payload) in pool.items():
        if tag not in (10, 11):
            continue
        class_idx, nat_idx = payload
        class_entry = pool.get(class_idx)
        nat_entry = pool.get(nat_idx)
        if not class_entry or not nat_entry or nat_entry[0] != 12:
            continue
        owner_utf8 = pool.get(class_entry[1])
        name_entry = pool.get(nat_entry[1][0])
        desc_entry = pool.get(nat_entry[1][1])
        if not (owner_utf8 and name_entry and desc_entry):
            continue
        if owner_utf8[1] == owner:
            out.append((name_entry[1], desc_entry[1]))
    return out


def scan_jar(jar: Path) -> dict:
    stale = 0
    bridged = 0
    stale_classes = []
    nested = {"stale": 0, "bridged": 0, "entries": []}
    with zipfile.ZipFile(jar) as z:
        for name in z.namelist():
            if not name.endswith(".class"):
                continue
            if name.startswith("top/mcbridge1201/bridge/"):
                continue  # the bridge itself reads the target fields - that is the point
            refs = fieldrefs(z.read(name))
            hits = [r for r in refs if r[0] == OWNER and r[1] in FIELDS and r[2] == OWNER_DESC]
            if hits:
                stale += len(hits)
                stale_classes.append(name)
            bridged += len([m for m in methodrefs(z.read(name), BRIDGE) if m[0] in BRIDGE_METHODS])
        for name in z.namelist():
            if not (name.startswith("META-INF/jars/") and name.endswith(".jar")):
                continue
            import io
            with zipfile.ZipFile(io.BytesIO(z.read(name))) as iz:
                s = b = 0
                for cn in iz.namelist():
                    if not cn.endswith(".class") or cn.startswith("top/mcbridge1201/bridge/"):
                        continue
                    refs = fieldrefs(iz.read(cn))
                    s += len([r for r in refs
                              if r[0] == OWNER and r[1] in FIELDS and r[2] == OWNER_DESC])
                    b += len([m for m in methodrefs(iz.read(cn), BRIDGE) if m[0] in BRIDGE_METHODS])
                if s or b:
                    nested["entries"].append({"jar": name, "stale": s, "bridged": b})
                nested["stale"] += s
                nested["bridged"] += b
    return {"staleFieldRefs": stale, "bridgeRefs": bridged,
            "classesWithStaleRefs": stale_classes, "nested": nested}


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

    bridges = out / "bridges"
    if bridges.exists():
        shutil.rmtree(bridges)
    rc_build, _ = run([sys.executable, str(ROOT / "tools" / "build_bridges.py"),
                       "--profile", str(PROFILE), "--out", str(bridges)])
    majors = class_majors(bridges) if bridges.is_dir() else {}

    patched = out / "ironchests-5.0.2-1214-ir.jar"
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

    before = scan_jar(SAMPLE)
    after = scan_jar(patched) if patched.is_file() else {}
    ir_total = sum(v for k, v in applied.items() if "interaction-result" in k)

    checks = [
        {"id": "bridge-compiles-at-65",
         "expect": [65], "got": sorted(majors)},
        {"id": "source-has-stale-field-refs", "expect": True,
         "got": before["staleFieldRefs"] > 0},
        {"id": "all-three-fields-redirected",
         "expect": True,
         "got": all(f"1214.interaction-result.{f.replace('_', '-')}" in applied
                    for f in FIELDS)},
        {"id": "no-stale-field-ref-left", "expect": 0,
         "got": after.get("staleFieldRefs", -1)
         + after.get("nested", {}).get("stale", 0)},
        # Constant pool entries are deduplicated per class: 29 calls collapse into 11 Methodref
        # entries. The patch log carries the call count; the pool only proves the reference exists.
        {"id": "bridge-refs-present", "expect": True,
         "got": (after.get("bridgeRefs", 0) + after.get("nested", {}).get("bridged", 0)) > 0},
    ]
    for c in checks:
        c["passed"] = c["got"] == c["expect"]
        print(f"{'PASS' if c['passed'] else 'FAIL'} {c['id']} got={c['got']} expect={c['expect']}")

    passed = all(c["passed"] for c in checks)
    result = {
        "workstream": "B03 fourth slice: InteractionResult constants via accessors",
        "target": PROFILE.relative_to(ROOT).as_posix(),
        "rule": "rules/fabric-1.21.4/interaction-result.json",
        "bridge": "java/src/bridge-1214/java/top/mcbridge1201/bridge/InteractionResultBridge1214.java",
        "input": SAMPLE.relative_to(ROOT).as_posix(),
        "output": patched.relative_to(ROOT).as_posix(),
        "build": {"rc": rc_build, "majors": {str(k): v for k, v in majors.items()}},
        "patch": {"rc": rc_patch, "applied": applied, "classesChanged": changed,
                  "logTail": patch_log.strip().splitlines()[-6:]},
        "constantPool": {"before": before, "after": after},
        "checks": checks,
        "method": "constant-pool Fieldref/Methodref parsing, not substring matching: the bridge and"
                  " string tables both contain the member names",
        "poolDeduplication": {"ruleHits": ir_total,
                              "bridgeMethodrefEntries": after.get("bridgeRefs", 0),
                              "why": "the constant pool holds one entry per distinct name+descriptor,"
                                     " so 29 call sites appear as 11 Methodref entries across 8"
                                     " classes"},
        "passed": passed,
        "scope": "linkage only: no 1.21.4 runtime, so behaviour is unverified. Whether each"
                 " constant still MEANS what 1.20.1 meant is not checked.",
    }
    (out / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                                     encoding="utf-8", newline="\n")
    print(f"\nInteractionResult bridge: {'PASS' if passed else 'FAIL'} -> {out / 'result.json'}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
