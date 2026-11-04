#!/usr/bin/env python3
"""Re-decide what happened to the members p250 called "member-removed".

p250 classified six ironchests members as removed for 1.21.4. Re-checking them against the two
intermediary mapping sets shows that two are not removed at all - they are still there with a
different descriptor, i.e. descriptor-changed:

  class_4970.method_9559           6 params -> 8 params
  class_4970$class_4971.method_26226  (BlockPos, ...) 2 params -> (BlockPos) 1 param

The reason p250 got it wrong is visible in its own data: it recorded the OWNER seen at the call
site (class_2237, class_2680), while the members are declared on a superclass (class_4970). A
lookup that goes "exact (owner, name, desc) or nothing" reports "gone" for a member that merely
moved up the hierarchy or changed shape.

This tool reads p250's result, resolves each entry through the 1.21.1 intermediary mapping to its
official name, then asks the 1.21.4 mapping what that member became - and checks the 1.21.4 stub
for the declaration.

    python tools/resolve_removed_members.py
"""
from __future__ import annotations

import argparse
import json
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
P250 = ROOT / "runs" / "p250-1214-break-classification" / "result.json"
TINY_1211 = ROOT / "work" / "target" / "intermediary-1.21.1-v2.jar"
TINY_1214 = ROOT / "work" / "target" / "intermediary-1.21.4-v2.jar"
STUB_1214 = ROOT / "work" / "target" / "client-1.21.4-intermediary.jar"
DEFAULT_OUT = ROOT / "runs" / "p267-removed-members-reclassified"


def load_tiny(jar: Path) -> dict:
    """intermediary member name -> list of {kind, desc, official, ownerOfficial, ownerIntermediary}."""
    z = zipfile.ZipFile(jar)
    lines = z.read("mappings/mappings.tiny").decode("utf-8", "replace").splitlines()
    members: dict[str, list[dict]] = {}
    owner_off = owner_inter = None
    for line in lines[1:]:
        parts = line.split("\t")
        if parts and parts[0] == "c" and len(parts) >= 3:
            owner_off, owner_inter = parts[1], parts[2]
            continue
        stripped = line.lstrip("\t")
        parts = stripped.split("\t")
        if len(parts) >= 4 and parts[0] in ("f", "m"):
            kind, desc, official, intermediary = parts[0], parts[1], parts[2], parts[3]
            members.setdefault(intermediary, []).append({
                "kind": kind, "desc": desc, "official": official,
                "ownerOfficial": owner_off, "ownerIntermediary": owner_inter,
            })
    return members


def declared(jar: Path, owner: str, name: str) -> list[str]:
    """Descriptors of `name` declared directly on `owner` in the stub."""
    entry = owner + ".class"
    with zipfile.ZipFile(jar) as z:
        if entry not in z.namelist():
            return []
        data = z.read(entry)
    sys.path.insert(0, str(ROOT / "tools"))
    import classpool  # noqa: E402

    members = classpool.declarations(data)
    return [d for n, d in members["fields"] + members["methods"] if n == name]


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
    for p in (P250, TINY_1211, TINY_1214, STUB_1214):
        if not p.is_file():
            print(f"missing input: {p}", file=sys.stderr)
            return 2

    old = load_tiny(TINY_1211)
    data = json.loads(P250.read_text(encoding="utf-8"))
    entries = [e for e in data["entries"]["ironchests-5.0.2"]
               if e.get("category") == "member-removed"]

    verdicts = []
    for e in entries:
        name = e.get("name")
        call_owner = e.get("owner")
        decls = old.get(name, [])
        verdict = {"p250": e, "name": name, "callSiteOwner": call_owner}
        if not decls:
            verdict["outcome"] = "unresolved"
            verdictWhy = "not in the 1.21.1 intermediary map"
        else:
            d = decls[0]
            verdict["declaringOwner"] = d["ownerIntermediary"]
            verdict["declaringOwnerOfficial"] = d["ownerOfficial"]
            verdict["officialName"] = d["official"]
            verdict["oldDesc"] = d["desc"]
            present = declared(STUB_1214, d["ownerIntermediary"], name)
            verdict["declaredIn1214"] = present
            if present and d["desc"] in present:
                verdict["outcome"] = "present-unchanged"
                verdictWhy = "still declared with the same descriptor"
            elif present:
                verdict["outcome"] = "descriptor-changed"
                verdictWhy = "same name, different descriptor - a callSite/signature adaptation, not a removal"
            else:
                verdict["outcome"] = "removed"
                verdictWhy = "not declared on the declaring owner in 1.21.4"
        verdict["why"] = verdictWhy
        verdicts.append(verdict)
        print(f"{verdict['outcome']:20} {name:16} callSite={call_owner}"
              f" declaring={verdict.get('declaringOwner')}")

    counts = {}
    for v in verdicts:
        counts[v["outcome"]] = counts.get(v["outcome"], 0) + 1
    print("\ncounts:", counts)

    checks = [
        {"id": "p250-over-counted-removals", "expect": True,
         "got": counts.get("removed", 0) < len(verdicts),
         "why": "at least one entry is not actually removed"},
        {"id": "two-are-descriptor-changes", "expect": 2, "got": counts.get("descriptor-changed", 0)},
    ]
    for c in checks:
        c["passed"] = c["got"] == c["expect"]
        print(f"{'PASS' if c['passed'] else 'FAIL'} {c['id']} got={c['got']} expect={c['expect']}")

    passed = all(c["passed"] for c in checks)
    result = {
        "workstream": "re-decide p250's member-removed entries against both mapping sets",
        "source": P250.relative_to(ROOT).as_posix(),
        "counts": counts,
        "entries": verdicts,
        "checks": checks,
        "rootCause": "p250 recorded the owner seen at the call site (class_2237, class_2680) but"
                     " looked members up without walking the hierarchy; a member that is merely"
                     " declared on a superclass or changed shape then reads as 'removed'",
        "consequence": "the real remaining work is smaller and differently shaped: the"
                       " descriptor-changed ones can use callSiteAdaptations /"
                       " signatureAdaptations; only the truly removed ones need a hand-written"
                       " bridge or an accepted degradation",
        "passed": passed,
        "scope": "mapping + declaration lookup only; nothing was patched or run",
    }
    (out / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                                     encoding="utf-8", newline="\n")
    print(f"\nreclassified: {'PASS' if passed else 'FAIL'} -> {out / 'result.json'}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
