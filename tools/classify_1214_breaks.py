#!/usr/bin/env python3
"""Classify the 1.21.4 breakages of a real 1.20.1 sample into rule candidates.

B01 (runs/p247) measured *how many* new breakages 1.21.4 adds for a given input. A number is not
a work item, so this tool turns each break into a classified entry:

* `class-removed`    - the owning class no longer exists in the target,
* `member-removed`   - the class exists, the member does not,
* `descriptor-changed` - the member name exists but the descriptor differs,
* `already-absent`   - the break also exists on the baseline (1.21.1), so it is not 1.21.4's,
* `unresolved`       - the mapping/name could not be pinned down.

Each entry carries the Mojang name when the source mapping knows it, because "class_1269" is not
actionable and "InteractionResult" is. The proposed rule type is a suggestion attached to the
finding, not a claim that the rule exists.

    python tools/classify_1214_breaks.py
    python tools/classify_1214_breaks.py --delta runs/p247-fabric-1.21.4-delta/result.json

Exit codes: 0 classified, 2 a required input is missing.
"""
from __future__ import annotations

import argparse
import json
import sys
import zipfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DELTA = ROOT / "runs" / "p247-fabric-1.21.4-delta" / "result.json"
DEFAULT_OUT = ROOT / "runs" / "p250-1214-break-classification"
STUB_1214 = ROOT / "work" / "target" / "client-1.21.4-intermediary.jar"
STUB_1211 = ROOT / "work" / "target" / "client-1.21.1-intermediary.jar"


def load_mojang_names(ver: str) -> dict[str, str]:
    """intermediary class -> Mojang class name, via the official mappings + intermediary tiny."""
    import re
    mapping_file = ROOT / "work" / "target" / f"client-{ver}-mappings.txt"
    inter_jar = ROOT / "work" / "target" / f"intermediary-{ver}-v2.jar"
    if not mapping_file.is_file() or not inter_jar.is_file():
        return {}
    obf_to_mojang = {}
    cur = None
    for raw in mapping_file.read_text(encoding="utf-8", errors="replace").splitlines():
        if raw.startswith("#"):
            continue
        if not raw.startswith((" ", "\t")):
            m = re.match(r"^(\S+) -> (\S+):$", raw.strip())
            if m:
                obf_to_mojang[m.group(2)] = m.group(1)
            continue
    with zipfile.ZipFile(inter_jar) as z:
        tiny = z.read("mappings/mappings.tiny").decode("utf-8", errors="replace").splitlines()
    obf_to_inter = {}
    for line in tiny:
        if line.startswith("c\t"):
            p = line.split("\t")
            if len(p) >= 3:
                obf_to_inter[p[1]] = p[2]
    return {inter: obf_to_mojang[obf] for obf, inter in obf_to_inter.items() if obf in obf_to_mojang}


class Stub:
    """Cheap existence checks against a target stub: class entries and member names in constants."""

    def __init__(self, jar: Path):
        self.jar = jar
        with zipfile.ZipFile(jar) as z:
            self.names = set(z.namelist())

    def has_class(self, internal: str) -> bool:
        return internal + ".class" in self.names

    def has_member_name(self, internal: str, member: str) -> bool:
        if not self.has_class(internal):
            return False
        with zipfile.ZipFile(self.jar) as z:
            return member.encode("utf-8") in z.read(internal + ".class")


def classify(entry: dict, kind: str, stub_1214: Stub, stub_1211: Stub,
             names_1211: dict[str, str], names_1214: dict[str, str]) -> dict:
    owner = entry.get("owner") or ""
    name = entry.get(name_key(kind))
    desc = entry.get("desc")
    mojang_1211 = names_1211.get(owner)
    mojang_1214 = names_1214.get(owner)
    record = {
        "kind": kind,
        "owner": owner,
        "name": name,
        "desc": desc,
        "mojangOwner1211": mojang_1211,
        "mojangOwner1214": mojang_1214,
    }
    if not owner:
        record["category"] = "unresolved"
    elif not stub_1214.has_class(owner):
        record["category"] = "class-removed"
        record["note"] = "the owning class is gone from the 1.21.4 index"
    else:
        present = stub_1214.has_member_name(owner, name) if name else True
        if name and not present:
            record["category"] = "member-removed"
            record["note"] = "the class exists but the member name no longer appears in it"
        elif name and present:
            record["category"] = "descriptor-changed"
            record["note"] = "the member name exists; the descriptor is what moved"
        else:
            record["category"] = "class-fields-changed"
    if stub_1211.has_class(owner) and name and not stub_1211.has_member_name(owner, name):
        record["alsoAbsentOn1211"] = True
    record["proposedRuleType"] = suggest(record)
    return record


def name_key(kind: str) -> str:
    return "name"


def suggest(record: dict) -> str:
    cat = record["category"]
    if cat == "descriptor-changed":
        return "callSiteAdaptations (callee gained/lost parameters) or signatureAdaptations (override)"
    if cat == "member-removed":
        return "methodRedirects / fieldRedirects to a bridge, or an explicit degradation if there is no replacement"
    if cat == "class-removed":
        return "needs a hand-written bridge or a degradation: a rule cannot invent a class"
    return "manual triage"


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

    if not delta_path.is_file():
        print(f"missing delta report: {delta_path}", file=sys.stderr)
        return 2
    for stub in (STUB_1214, STUB_1211):
        if not stub.is_file():
            print(f"missing stub: {stub}", file=sys.stderr)
            return 2

    delta = json.loads(delta_path.read_text(encoding="utf-8"))
    names_1211 = load_mojang_names("1.21.1")
    names_1214 = load_mojang_names("1.21.4")
    stub_1214, stub_1211 = Stub(STUB_1214), Stub(STUB_1211)

    per_input = {}
    all_records = []
    for label, info in (delta.get("delta") or {}).items():
        records = []
        for field, kind in (("newIn1214", "new"), ):
            for entry in info.get(field) or []:
                records.append(classify(entry, kind, stub_1214, stub_1211, names_1211, names_1214))
        per_input[label] = records
        all_records.extend(records)
        print(f"{label}: {len(records)} new break(s)")

    by_category = Counter(r["category"] for r in all_records)
    by_rule = Counter(r["proposedRuleType"] for r in all_records)
    resolved = [r for r in all_records if r.get("mojangOwner1211") or r.get("mojangOwner1214")]

    result = {
        "workstream": "B03: classify the 1.21.4 breakages into rule candidates",
        "source": {"delta": delta_path.relative_to(ROOT).as_posix(),
                   "stubs": [STUB_1211.relative_to(ROOT).as_posix(),
                             STUB_1214.relative_to(ROOT).as_posix()]},
        "counts": {"newBreaks": len(all_records),
                   "withMojangName": len(resolved),
                   "byCategory": dict(by_category),
                   "byProposedRule": dict(by_rule)},
        "entries": per_input,
        "caveats": [
            "Category detection is constant-pool based: 'member present' means the name appears"
            " in the class, not that a call with this descriptor resolves.",
            "A proposed rule type is a suggestion for the next work item, not an existing capability.",
            "Only the breaks measured in the delta are classified; nothing here was converted.",
        ],
        "scope": "classification only: no jar converted, no rule written, no game launched.",
    }
    (out / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                                     encoding="utf-8", newline="\n")
    print(f"\nby category: {dict(by_category)}")
    print(f"-> {out / 'result.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
