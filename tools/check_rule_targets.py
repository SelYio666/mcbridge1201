#!/usr/bin/env python3
"""Verify that every target-side member a rule names actually exists in the target.

Written because of a real slip: 1.21.4 renamed `Registry#registryKey` from
`method_30517` to `method_46765`, the 1.21.4 registration rule still said `method_30517`, and
every bytecode assertion passed because `patch` emits call instructions without checking that the
callee exists. The artifact would have thrown `NoSuchMethodError` at the first registration
(runs/p260).

What counts as a "target-side" reference is explicit per rule type - source and bridge fields are
excluded, because the first is the 1.20.1 shape and the second is our own compiled class:

  registrationKeys      setterOwner/Name/Desc, keyFactory*, registryKey*
  callSiteAdaptations   targetOwner/targetName/targetDesc
  signatureAdaptations  targetClass/methodName/newDesc

Everything else is skipped rather than guessed at. A checker that guesses produces false alarms,
and a false alarm is how a gate gets switched off.

    python tools/check_rule_targets.py
    python tools/check_rule_targets.py --rules-dir rules/fabric-1.21.4 --stub <jar>

Exit codes: 0 every reference resolves, 1 something is missing, 2 a required input is missing.
"""
from __future__ import annotations

import argparse
import json
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import classpool  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_STUB = ROOT / "work" / "target" / "client-1.21.4-intermediary.jar"

# rule list -> [(owner field, name field, descriptor field)]
TARGET_REFS = {
    "registrationKeys": [
        ("setterOwner", "setterName", "setterDesc"),
        ("keyFactoryOwner", "keyFactoryName", "keyFactoryDesc"),
        ("registryKeyOwner", "registryKeyName", "registryKeyDesc"),
    ],
    "callSiteAdaptations": [("targetOwner", "targetName", "targetDesc")],
    "signatureAdaptations": [("targetClass", "methodName", "newDesc")],
}


class Target:
    def __init__(self, jar: Path):
        self.jar = jar
        with zipfile.ZipFile(jar) as z:
            self.names = set(z.namelist())
        self._cache: dict[str, dict] = {}

    def has_class(self, internal: str) -> bool:
        return internal + ".class" in self.names

    def members(self, internal: str) -> dict:
        if internal not in self._cache:
            with zipfile.ZipFile(self.jar) as z:
                entry = internal + ".class"
                self._cache[internal] = (classpool.declarations(z.read(entry))
                                         if entry in self.names else {"fields": [], "methods": []})
        return self._cache[internal]

    def has_member(self, internal: str, name: str, desc: str) -> bool:
        members = self.members(internal)
        return any(n == name and d == desc
                   for n, d in members["fields"] + members["methods"])


def check_rule_file(path: Path, target: Target) -> list[dict]:
    problems = []
    data = json.loads(path.read_text(encoding="utf-8"))
    for rule_list, specs in TARGET_REFS.items():
        for entry in data.get(rule_list) or []:
            for owner_field, name_field, desc_field in specs:
                owner = entry.get(owner_field)
                name = entry.get(name_field)
                desc = entry.get(desc_field)
                if not owner or not name:
                    continue
                rule_id = entry.get("id", "?")
                if not target.has_class(owner):
                    problems.append({"file": path.name, "rule": rule_id, "kind": "class",
                                     "owner": owner, "name": name, "desc": desc,
                                     "why": "the owning class is not in the target"})
                    continue
                if desc and not target.has_member(owner, name, desc):
                    problems.append({"file": path.name, "rule": rule_id, "kind": "member",
                                     "owner": owner, "name": name, "desc": desc,
                                     "why": "no such member with this exact descriptor"})
    return problems


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--rules-dir", default="rules/fabric-1.21.4")
    ap.add_argument("--stub", default=str(DEFAULT_STUB))
    ap.add_argument("--json", default=None)
    args = ap.parse_args()

    stub = Path(args.stub)
    rules_dir = Path(args.rules_dir)
    if not rules_dir.is_absolute():
        rules_dir = ROOT / rules_dir
    if not stub.is_file():
        print(f"missing target stub: {stub}", file=sys.stderr)
        return 2
    files = sorted(rules_dir.glob("*.json"), key=lambda p: p.name)
    if not files:
        print(f"no rule files under {rules_dir}", file=sys.stderr)
        return 2

    target = Target(stub)
    problems = []
    references = 0
    for path in files:
        found = check_rule_file(path, target)
        problems.extend(found)
        data = json.loads(path.read_text(encoding="utf-8"))
        references += sum(len(data.get(k) or []) * len(v)
                          for k, v in TARGET_REFS.items())

    for p in problems:
        print(f"MISSING {p['kind']:6} {p['file']} {p['rule']}: {p['owner']}.{p['name']}{p['desc'] or ''}")
        print(f"        {p['why']}")
    print(f"checked {len(files)} rule file(s), {references} target reference group(s): "
          f"{len(problems)} missing")

    if args.json:
        Path(args.json).write_text(json.dumps(
            {"stub": str(stub), "rulesDir": str(rules_dir), "ruleFiles": len(files),
             "problems": problems, "passed": not problems}, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8", newline="\n")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
