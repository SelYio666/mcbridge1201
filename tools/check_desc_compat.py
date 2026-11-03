#!/usr/bin/env python3
"""Separate real descriptor breakage from subtype false alarms in the 1.21.4 delta.

The static analyser reports a `descMismatch` whenever a referenced field's descriptor differs
from the target's. That is not the same as "broken": if the new field type is a *subtype* of the
old one, a JVM accepts the value wherever the old type was expected, and no conversion is needed.

1.21.4 has both cases, close together:

* `InteractionResult.SUCCESS` went from `class_1269` to a record field of type
  `class_1269$class_9860`, which `implements class_1269` -> compatible, a false alarm.
* `BlockStateProperties` fields went from `class_2753` (DirectionProperty, deleted) to
  `class_2754<Direction>` -> a real break.

    python tools/check_desc_compat.py
    python tools/check_desc_compat.py --delta runs/p250-1214-break-classification/result.json

Exit codes: 0 classified, 2 a required input is missing.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import deque
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DELTA = ROOT / "runs" / "p250-1214-break-classification" / "result.json"
DEFAULT_OUT = ROOT / "runs" / "p253-desc-compat"
STUB_1214 = ROOT / "work" / "target" / "client-1.21.4-intermediary.jar"


def java_home() -> str | None:
    import os
    env = os.environ.get("JAVA_HOME")
    if env and (Path(env) / "bin" / "javap.exe").exists():
        return env
    for cand in (ROOT.parent / ".toolchain" / "jdk", ROOT / ".toolchain" / "jdk"):
        if (cand / "bin" / "javap.exe").exists():
            os.environ["JAVA_HOME"] = str(cand)
            return str(cand)
    return None


def javap(javap_exe: str, internal: str) -> str:
    p = subprocess.run([javap_exe, "-cp", str(STUB_1214), internal.replace("/", ".")],
                       capture_output=True, text=True, errors="replace")
    return (p.stdout or "") + (p.stderr or "")


HEADER = re.compile(r"^(?:public |final |abstract |sealed |non-sealed )*(?:class|interface|enum|record)"
                    r"\s+(\S+)(?:\s+extends\s+([\w.$]+))?(?:\s+implements\s+(.+?))?\s*\{", re.M)


def parse_supertypes(text: str) -> list[str]:
    """Class header -> direct supertypes as internal names."""
    m = HEADER.search(text)
    if not m:
        return []
    out = []
    if m.group(2):
        out.append(m.group(2).replace(".", "/"))
    if m.group(3):
        for part in m.group(3).split(","):
            name = part.strip()
            if name:
                out.append(name.replace(".", "/"))
    return out


def is_subtype(javap_exe: str, candidate: str, target: str, cache: dict) -> bool:
    """Breadth-first over the stub's own class headers. Not resolving the JDK is fine: game
    classes never inherit from a JDK type in a way that matters here."""
    seen = set()
    queue = deque([candidate])
    while queue:
        cur = queue.popleft()
        if cur == target:
            return True
        if cur in seen:
            continue
        seen.add(cur)
        if cur not in cache:
            cache[cur] = parse_supertypes(javap(javap_exe, cur))
        for sup in cache[cur]:
            if sup not in seen:
                queue.append(sup)
    return False


def field_type(javap_exe: str, owner: str, field: str) -> str | None:
    text = javap(javap_exe, owner)
    for line in text.splitlines():
        if field in line and ";" in line and ("static" in line or "public" in line):
            m = re.search(r"(\S+)\s+" + re.escape(field) + r"\s*;", line)
            if m:
                return m.group(1)
    return None


def methods_named(javap_exe: str, owner: str, name: str) -> list[str]:
    """Every overload of `name` in the target class, as javap prints them."""
    # javap prints constructors as "class_4309(...)" rather than "<init>(", so the needle has to
    # follow the class name for those.
    needle = name
    if name == "<init>":
        needle = owner.rsplit("/", 1)[-1].split("$")[-1]
    out = []
    for line in javap(javap_exe, owner).splitlines():
        if needle + "(" in line and line.strip().endswith(";"):
            out.append(line.strip())
    return out


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--delta", default=str(DEFAULT_DELTA))
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    args = ap.parse_args()
    delta_path = Path(args.delta)
    out = Path(args.out)
    if not out.is_absolute():
        out = ROOT / out
    out.mkdir(parents=True, exist_ok=True)
    home = java_home()
    if home is None:
        print("need a JDK for javap", file=sys.stderr)
        return 2
    javap_exe = str(Path(home) / "bin" / "javap")
    if not Path(javap_exe).is_file():
        javap_exe = str(Path(home) / "bin" / "javap.exe")
    if not delta_path.is_file():
        print(f"missing delta: {delta_path}", file=sys.stderr)
        return 2
    if not STUB_1214.is_file():
        print(f"missing stub: {STUB_1214}", file=sys.stderr)
        return 2

    delta = json.loads(delta_path.read_text(encoding="utf-8"))
    entries = []
    for label, recs in (delta.get("entries") or {}).items():
        for r in recs:
            if r.get("category") == "descriptor-changed":
                entries.append(dict(r, input=label))

    cache: dict[str, list[str]] = {}
    results = []
    for r in entries:
        owner = r["owner"]
        field = r.get("name")
        old_desc = r.get("desc") or ""
        m = re.match(r"L([^;]+);", old_desc)
        old_type = m.group(1) if m else None
        new_simple = field_type(javap_exe, owner, field) if field else None
        new_type = new_simple.replace(".", "/") if new_simple else None
        verdict = "unknown"
        detail = ""
        new_signatures = []
        if new_type is None and field:
            # Not a field: a method whose signature moved. Report every overload so a rule author
            # can see the new shape; do not guess compatibility from a signature alone.
            new_signatures = methods_named(javap_exe, owner, field)
            if new_signatures:
                verdict = "method-changed"
                detail = "signature moved; adapt at the call site (or via a bridge)"
        subtype = False
        if old_type and new_type:
            if new_type == old_type:
                verdict, detail = "same", "descriptor already matches"
            else:
                # A subtype is NOT good enough: JVMS 5.4.3.2/5.4.3.3 resolve a field or method by
                # name AND descriptor, so a stale descriptor fails with NoSuchFieldError /
                # NoSuchMethodError before the verifier ever looks at assignability.
                # Measured with JvmResolutionTest against the 1.21.4 stub (runs/p255).
                subtype = is_subtype(javap_exe, new_type, old_type, cache)
                verdict = "broken"
                detail = (f"{new_type} {'is a subtype of' if subtype else 'is not a subtype of'}"
                          f" {old_type}; either way the descriptor differs, so resolution fails")
        results.append({
            "input": r["input"], "owner": owner, "field": field,
            "mojangOwner": r.get("mojangOwner1211") or r.get("mojangOwner1214"),
            "oldDescriptor": old_desc, "oldType": old_type,
            "newType": new_type, "newSignatures": new_signatures,
            "newTypeIsSubtype": subtype, "verdict": verdict, "detail": detail,
        })
        print(f"{verdict:11} {owner}.{field}  {old_type} -> {new_type}")

    by_verdict = {}
    for r in results:
        by_verdict[r["verdict"]] = by_verdict.get(r["verdict"], 0) + 1
    real = [r for r in results if r["verdict"] in ("broken", "method-changed")]
    result = {
        "workstream": "B03: separate real descriptor breakage from subtype false alarms",
        "source": delta_path.relative_to(ROOT).as_posix(),
        "counts": {
            "descriptorChangedTotal": len(results),
            "broken": len([r for r in results if r["verdict"] == "broken"]),
            "methodChanged": by_verdict.get("method-changed", 0),
            "compatible": by_verdict.get("compatible", 0),
            "same": by_verdict.get("same", 0),
            "unknown": by_verdict.get("unknown", 0),
        },
        "verdicts": by_verdict,
        "entries": results,
        "needsConversion": real,
        "caveats": [
            "A changed descriptor is broken even when the new type is a subtype: JVMS 5.4.3.2/5.4.3.3"
            " resolve a field or method by name AND descriptor. newTypeIsSubtype is recorded for"
            " information only. Measured with JvmResolutionTest (runs/p255).",
            "Even a resolving member can behave differently; this check only judges linkage.",
            "This only looks at the descriptor. A member that disappeared entirely is a different"
            " category ('member-removed') and is not re-examined here.",
        ],
        "scope": "static only: no conversion, no game launch",
    }
    (out / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                                     encoding="utf-8", newline="\n")
    print(f"\n{len(results)} descriptor change(s): {result['counts']}")
    print(f"-> {out / 'result.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
