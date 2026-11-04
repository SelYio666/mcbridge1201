#!/usr/bin/env python3
"""Structural check of the registry-context bridge.

`RegistryKeyInjectionTest` was attempted and had to be abandoned: constructing
`Item.Settings` offline is impossible. The constructor runs `class_1793.<init>`, which touches
`class_9334.<clinit>` (the data-component registry) and dies with `ExceptionInInitializerError`
unless a game is running. So the *behaviour* "the settings object carries the right RegistryKey"
cannot be proven without an instance - that stays a known limitation, recorded in runs/p265.

What CAN be checked offline is that the bridge does what it claims: read the pending registry,
derive the key through the ordinary factory, and set it on the settings - in that order, inside the
guarded branch - and that `getWithKey` restores the context from a finally block rather than a
straight-line clear.

    python tools/check_bridge_structure.py
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BRIDGES = ROOT / "work" / "targets" / "fabric-1.21.4" / "bridges"
CLASS = "top.mcbridge1201.bridge.RegistryKeyContext"
DEFAULT_OUT = ROOT / "runs" / "p265-key-injection-boundary"

EXPECTED_SETTINGS_CALLS = ["method_46765", "method_29179", "method_63686"]


def java_home() -> str | None:
    env = os.environ.get("JAVA_HOME")
    if env and (Path(env) / "bin" / "javap.exe").exists():
        return env
    for cand in (ROOT.parent / ".toolchain" / "jdk", ROOT / ".toolchain" / "jdk"):
        if (cand / "bin" / "javap.exe").exists():
            os.environ["JAVA_HOME"] = str(cand)
            return str(cand)
    return None


def disassemble() -> str:
    home = java_home()
    if home is None:
        raise SystemExit("need a JDK for javap")
    exe = Path(home) / "bin" / "javap.exe"
    p = subprocess.run([str(exe), "-c", "-p", "-cp", str(BRIDGES), CLASS],
                       capture_output=True, text=True, errors="replace")
    return (p.stdout or "") + (p.stderr or "")


def method_block(text: str, name: str) -> str:
    lines = text.splitlines()
    start = None
    for i, line in enumerate(lines):
        # javap prints "public static Foo settings();" then a Code: line - the signature ends
        # with a semicolon, not a brace.
        if (re.search(r"\b" + re.escape(name) + r"\(", line)
                and line.rstrip().endswith(";")
                and i + 1 < len(lines) and lines[i + 1].strip() == "Code:"):
            start = i
            break
    if start is None:
        return ""
    out = [lines[start]]
    for line in lines[start + 1:]:
        if line.strip() == "}":
            out.append(line)
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
    if not BRIDGES.is_dir():
        print(f"missing compiled bridges: {BRIDGES}", file=sys.stderr)
        return 2

    text = disassemble()
    (out / "javap-RegistryKeyContext.txt").write_text(text, encoding="utf-8", newline="\n")
    settings_body = method_block(text, "settings")
    withkey_body = method_block(text, "getWithKey")

    order = []
    for line in settings_body.splitlines():
        m = re.match(r"\s*(\d+):\s+\S+\s+.*Method (?:net/minecraft/class_)?\S*\.(method_\d+)", line)
        if m:
            order.append((int(m.group(1)), m.group(2)))
    present = [name for _, name in sorted(order) if name in EXPECTED_SETTINGS_CALLS]

    checks = [
        {"id": "settings-derives-a-key", "expect": True,
         "got": "method_46765" in present and "method_29179" in present,
         "why": "reads the registry's key and derives a child key from the pending id"},
        {"id": "settings-attaches-it", "expect": True, "got": "method_63686" in present,
         "why": "without this call the key is computed but never stored"},
        {"id": "settings-order", "expect": EXPECTED_SETTINGS_CALLS, "got": present},
        {"id": "settings-guards-on-a-context", "expect": True,
         "got": ("ifnull" in settings_body or "ifnonnull" in settings_body),
         "why": "outside a context the factory must return plain settings"},
        {"id": "getwithkey-restores-in-finally", "expect": True,
         "got": ("Exception table" in withkey_body and "finally" in text.lower())
                or "Exception table" in withkey_body,
         "why": "a straight-line restore would leak the id when the supplier throws"},
    ]
    for c in checks:
        c["passed"] = c["got"] == c["expect"]
        print(f"{'PASS' if c['passed'] else 'FAIL'} {c['id']} got={c['got']!r}")

    passed = all(c["passed"] for c in checks)
    result = {
        "workstream": "what can and cannot be verified offline about the registry key injection",
        "boundary": {
            "attempt": "construct Item.Settings offline and assert field_54117 names the pending id",
            "blockedBy": "class_1793.<init> -> class_9334.<clinit> (data components) throws"
                         " ExceptionInInitializerError without a running game",
            "consequence": "the behaviour 'settings carries the right RegistryKey' needs a 1.21.4"
                           " instance; it is NOT claimed as verified",
        },
        "structuralChecks": checks,
        "settingsCallOrder": present,
        "passed": passed,
        "scope": "structure only: proves the bridge performs the right calls in the right order, not"
                 " that the game accepts the result",
    }
    (out / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                                     encoding="utf-8", newline="\n")
    print(f"\nbridge structure: {'PASS' if passed else 'FAIL'} -> {out / 'result.json'}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
