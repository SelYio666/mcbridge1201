#!/usr/bin/env python3
"""Probe whether the ResourcefulLib registration path can carry a registry key (B03, ironchests).

p248 found that ironchests registers through ResourcefulLib's wrapper, not through a direct
`Registry.register` call, so the `registrationKeys` rule (which needs the register call in the same
method) cannot fire. This probe reads the wrapper's bytecode to decide whether an injection point
exists at all, and if so where exactly.

It does NOT patch anything: it establishes the facts a rule would have to rely on.

    python tools/probe_resourceful_registration.py
"""
from __future__ import annotations

import argparse
import io
import json
import os
import re
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SAMPLE = ROOT / "work" / "corpus" / "ironchests" / "ironchests-5.0.2-fabric.jar"
DEFAULT_OUT = ROOT / "runs" / "p258-resourceful-registration-probe"
ENTRY_CLASS = "com.teamresourceful.resourcefullib.common.registry.fabric.FabricRegistryEntry"
REGISTRY_CLASS = "com.teamresourceful.resourcefullib.common.registry.fabric.FabricResourcefulRegistry"


def java_home() -> str | None:
    env = os.environ.get("JAVA_HOME")
    if env and (Path(env) / "bin" / "javap.exe").exists():
        return env
    for cand in (ROOT.parent / ".toolchain" / "jdk", ROOT / ".toolchain" / "jdk"):
        if (cand / "bin" / "javap.exe").exists():
            os.environ["JAVA_HOME"] = str(cand)
            return str(cand)
    return None


def extract_nested(jar: Path, out_dir: Path) -> Path | None:
    out_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(jar) as z:
        nested = [n for n in z.namelist()
                  if n.startswith("META-INF/jars/") and n.endswith(".jar")]
        if not nested:
            return None
        dst = out_dir / "resourcefullib.jar"
        dst.write_bytes(z.read(nested[0]))
        return dst


def javap_class(path: Path, internal: str) -> str:
    home = java_home()
    exe = Path(home) / "bin" / "javap.exe"
    p = subprocess.run([str(exe), "-c", "-p", "-cp", str(path), internal.replace("/", ".")],
                       capture_output=True, text=True, errors="replace")
    return (p.stdout or "") + (p.stderr or "")


def method_body(text: str, name: str) -> str:
    """The javap text of one method, from its signature to the next blank-line-separated block."""
    lines = text.splitlines()
    start = None
    for i, line in enumerate(lines):
        if re.search(r"\b" + re.escape(name) + r"\(", line) and line.strip().endswith(";"):
            start = i
            break
    if start is None:
        return ""
    out = [lines[start]]
    for line in lines[start + 1:]:
        if re.match(r"^  (public|private|protected|static|final).*\);$", line):
            break
        out.append(line)
    return "\n".join(out)


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
    if not SAMPLE.is_file():
        print(f"missing sample: {SAMPLE}", file=sys.stderr)
        return 2
    if java_home() is None:
        print("need a JDK for javap", file=sys.stderr)
        return 2

    rl = extract_nested(SAMPLE, ROOT / "work" / "tmp" / "resourceful-probe")
    if rl is None:
        print("no nested jar in the sample", file=sys.stderr)
        return 2

    entry_text = javap_class(rl, ENTRY_CLASS)
    registry_text = javap_class(rl, REGISTRY_CLASS)
    of_body = method_body(entry_text, "of")
    register_body = method_body(registry_text, "register")
    init_body = method_body(registry_text, "init")

    (out / "javap-FabricRegistryEntry.txt").write_text(entry_text, encoding="utf-8", newline="\n")
    (out / "javap-FabricResourcefulRegistry.txt").write_text(registry_text, encoding="utf-8", newline="\n")

    supplier_call = "java/util/function/Supplier.get"
    register_call = "class_2378.method_10230"
    facts = {
        "wrapperRegisterOnlyCollects": ("RegistryEntries.add" in register_body
                                        and register_call not in register_body),
        "wrapperInitIsEmpty": ("return" in init_body and register_call not in init_body
                               and "Supplier" not in init_body),
        "factoryEvaluatesSupplierBeforeRegistering": (supplier_call in of_body
                                                      and register_call in of_body),
        "factoryTakesTheIdAsLocal1": ("aload_1" in of_body),
        "factorySignature": re.search(r"public static .*of\((.*)\);", of_body or "").group(1)
        if re.search(r"public static .*of\((.*)\);", of_body or "") else None,
    }

    # Instruction order inside the factory: the id load must precede the supplier call.
    order = []
    for line in of_body.splitlines():
        m = re.match(r"\s*(\d+):\s+(\w+)", line)
        if m and "Supplier.get" in line:
            order.append(("supplier.get", int(m.group(1))))
        if m and register_call in line:
            order.append(("method_10230", int(m.group(1))))
        if m and re.search(r"\baload_1\b", line):
            order.append(("aload_1(id)", int(m.group(1))))
    supplier_at = next((o[1] for o in order if o[0] == "supplier.get"), None)
    id_before_supplier = [o for o in order if o[0] == "aload_1(id)" and f"{o[1]}" and
                          supplier_at is not None and o[1] < supplier_at]

    checks = [
        {"id": "register-does-not-register", "expect": True,
         "got": facts["wrapperRegisterOnlyCollects"],
         "why": "the wrapper's register() only collects entries; the key cannot be injected there"},
        {"id": "init-does-nothing", "expect": True, "got": facts["wrapperInitIsEmpty"],
         "why": "init() is empty, so registration is not deferred to init"},
        {"id": "factory-evaluates-then-registers", "expect": True,
         "got": facts["factoryEvaluatesSupplierBeforeRegistering"],
         "why": "FabricRegistryEntry.of is the only place that both calls the supplier and registers"},
        {"id": "id-available-before-supplier", "expect": True,
         "got": bool(id_before_supplier),
         "why": "the id must be readable (local 1) before Supplier.get(), or no context can be set"},
    ]
    for c in checks:
        c["passed"] = c["got"] == c["expect"]
        print(f"{'PASS' if c['passed'] else 'FAIL'} {c['id']} got={c['got']}")

    passed = all(c["passed"] for c in checks)
    result = {
        "workstream": "B03 probe: can the ResourcefulLib registration path carry a registry key?",
        "sample": SAMPLE.relative_to(ROOT).as_posix(),
        "facts": facts,
        "instructionOrder": order,
        "checks": checks,
        "injectionPoint": {
            "method": ENTRY_CLASS + ".of",
            "before": "invokeinterface java/util/function/Supplier.get",
            "whatToInsert": "aload_1 (the Identifier local) + a bridge call that stores it as the"
                            " pending registry id in a ThreadLocal",
            "whyItWorks": "the supplier is evaluated inside this method, so a lambda that builds"
                          " Item.Settings runs with the pending id set",
        },
        "whatIsStillMissing": [
            "a rule type that inserts a call before a matched call (the existing registrationKeys"
            " rule only fires when a register call is in the SAME method as the settings ctor)",
            "a bridge that exposes the pending id and a settings factory",
            "a second rule to redirect the mod's `new Item.Settings()` inside the lambda",
            "ThreadLocal lifetime handling: nested registrations or an exception would leak the id",
        ],
        "passed": passed,
        "scope": "probe only: nothing was patched. This answers 'is there an injection point', not"
                 " 'does the conversion work'.",
    }
    (out / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                                     encoding="utf-8", newline="\n")
    print(f"\nprobe: {'PASS' if passed else 'FAIL'} -> {out / 'result.json'}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
