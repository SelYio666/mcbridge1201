"""Resolve the p158 Sodium damage matrix against the 1.20.1 and 1.21.1 mappings.

For every entry of `runs/p158-sodium-probe/plan.json` this prints what the symbol was in
1.20.1 (Mojang name) and what happened to it in 1.21.1, so `docs/sodium-plan.md` cites
facts instead of guesses:

  removed     the Mojang class/member name does not exist in 1.21.1 at all
  moved       the same Mojang name now lives in another class (inherited or relocated)
  re-signed   the same Mojang name exists in the same class with a different descriptor
  re-ID       the same Mojang name and descriptor, but a different intermediary id
  unresolved  could not be joined to the mappings; reported, never silently dropped

Every row is also tagged [API] when all of its references come from a 1.20.1-era Fabric
API module bundled inside Sodium's META-INF/jars instead of Sodium's own classes.

How the join works: the Mojang mappings give (obf class, obf member, official desc) ->
official name; the Fabric intermediary tiny gives (obf class, obf member, obf desc) ->
intermediary name. The obf desc is rewritten into the official form (dots -> slashes)
before joining, so overloaded obf names (a, b, ...) cannot be mismatched. The return type
is a prefix in the Mojang file and part of the descriptor in the JVM, so it is folded back
in. When an entry still has several candidates (real overloads), the item's own
descriptor breaks the tie.

Inputs (already in the repo working set, nothing is downloaded):
  work/target/intermediary-<ver>-v2.jar      obf <-> intermediary
  work/target/client-<ver>-mappings.txt      obf <-> Mojang (official) names

Usage:
  python runs/p199-sodium-plan/resolve.py            # table
  python runs/p199-sodium-plan/resolve.py --json     # machine-readable
"""
from __future__ import annotations

import json
import re
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PLAN = ROOT / "runs" / "p158-sodium-probe" / "plan.json"
TARGET = ROOT / "work" / "target"

TYPE_REF = re.compile(r"L([^;]+);")
PRIMITIVES = {"void": "V", "boolean": "Z", "byte": "B", "char": "C", "short": "S",
              "int": "I", "long": "J", "float": "F", "double": "D"}
METHOD_LINE = re.compile(r"^(?P<ret>.*?)\s*(?P<name>[\w$<>]+)\((?P<args>[^)]*)\)$")


def to_desc(type_name: str) -> str:
    """Mojang writes types as they read in source ("com.foo.Bar", "int[]"); descriptors
    need "Lcom/foo/Bar;" and "I"."""
    t = type_name.strip()
    if t.endswith("[]"):
        return "[" + to_desc(t[:-2])
    if t in PRIMITIVES:
        return PRIMITIVES[t]
    return "L" + t.replace(".", "/") + ";"


def pretty(desc: str) -> str:
    """Slash form for comparison, dotted form for humans."""
    return TYPE_REF.sub(lambda m: f"L{m.group(1).replace('/', '.')};", desc)


def load_version(ver: str):
    """Return (inter_class -> official_class, joined rows, obf -> official class map).

    joined rows are (officialClass, kind, officialName, desc, interMember).
    """
    obf_to_inter: dict[str, str] = {}
    tiny_members: list[tuple[str, str, str, str, str]] = []
    with zipfile.ZipFile(TARGET / f"intermediary-{ver}-v2.jar") as z:
        tiny = z.read("mappings/mappings.tiny").decode("utf-8").splitlines()
    cur = None
    for line in tiny:
        if line.startswith("c\t"):
            parts = line.split("\t")
            if len(parts) >= 3:
                obf_to_inter[parts[1]] = parts[2]
                cur = parts[1]
        elif line.startswith("\t") and cur:
            # tiny v2 member row: "\t<kind>\t<desc>\t<obfName>\t<interName>"
            parts = line.split("\t")
            if parts and parts[0] == "":
                parts = parts[1:]
            if len(parts) >= 4 and parts[0] in ("m", "f"):
                kind = "method" if parts[0] == "m" else "field"
                tiny_members.append((cur, kind, parts[1], parts[2], parts[3]))

    obf_class_to_official: dict[str, str] = {}
    ctors: dict[str, list[str]] = {}
    mojang: dict[tuple[str, str, str], tuple[str, str]] = {}
    current_obf = None
    with (TARGET / f"client-{ver}-mappings.txt").open(encoding="utf-8") as fh:
        for raw in fh:
            line = raw.rstrip("\n")
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            if not line.startswith(" ") and "->" in line:
                official, _, obf = line.partition("->")
                current_obf = obf.strip().rstrip(":")
                obf_class_to_official[current_obf] = official.strip().rstrip(":")
                continue
            if not line.startswith(" ") or not current_obf:
                continue
            body, _, obf = line.strip().partition(" -> ")
            obf = obf.strip().rstrip(":")
            body = re.sub(r"^(?:\d+:\d+:)+", "", body)      # source line numbers
            if "(" in body:
                m = METHOD_LINE.match(body)
                if not m:
                    continue
                args = [a for a in m.group("args").split(",") if a.strip()]
                desc = "(" + "".join(to_desc(a) for a in args) + ")" + to_desc(m.group("ret"))
                official_name, kind = m.group("name"), "method"
            else:
                bits = body.split()
                if len(bits) < 2:
                    continue
                official_name, kind = bits[-1], "field"
                desc = to_desc(" ".join(bits[:-1]))
            mojang[(current_obf, obf, desc)] = (official_name, kind)
            if official_name == "<init>":
                ctors.setdefault(obf_class_to_official[current_obf], []).append(desc)

    inter_to_official = {v: obf_class_to_official.get(k, k) for k, v in obf_to_inter.items()}
    joined = []
    for obf_class, kind, obf_desc, obf_name, inter in tiny_members:
        official_class = obf_class_to_official.get(obf_class)
        if official_class is None:
            continue
        desc = TYPE_REF.sub(
            lambda m: f"L{obf_class_to_official.get(m.group(1), m.group(1)).replace('.', '/')};",
            obf_desc)
        hit = mojang.get((obf_class, obf_name, desc))
        if not hit:
            continue
        joined.append((official_class, hit[1], hit[0], desc, inter))
    return inter_to_official, joined, ctors


def main(argv: list[str]) -> int:
    as_json = "--json" in argv
    i2o_1201, joined_1201, ctors_1201 = load_version("1.20.1")
    i2o_1211, joined_1211, ctors_1211 = load_version("1.21.1")

    o2i_1211 = {official: inter for inter, official in i2o_1211.items()
                if not official.startswith("net/minecraft/")}
    cls1211 = {row[0] for row in joined_1211}

    by_cls_inter: dict[tuple[str, str, str], list[tuple[str, str]]] = {}
    by_inter: dict[tuple[str, str], list[tuple[str, str, str]]] = {}
    members_1211: dict[tuple[str, str, str], str] = {}
    by_name_1211: dict[tuple[str, str], list[tuple[str, str]]] = {}
    for cls, kind, name, desc, inter in joined_1211:
        members_1211[(cls, kind, name)] = desc
        by_name_1211.setdefault((kind, name), []).append((cls, desc))
    for cls, kind, name, desc, inter in joined_1201:
        by_cls_inter.setdefault((cls, kind, inter), []).append((name, desc))
        by_inter.setdefault((kind, inter), []).append((cls, name, desc))

    def inter_desc_to_official(desc: str) -> str:
        return TYPE_REF.sub(
            lambda m: f"L{i2o_1201.get(m.group(1), m.group(1)).replace('.', '/')};", desc)

    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    art = plan["artifacts"][0]

    rows = []
    for bucket in ("missingClass", "missingMember", "descMismatch"):
        for item in art[bucket]:
            owner = item["owner"]
            if ";" in owner:                  # composite ref recorded as a class-kind entry
                cls_part, _, rest = owner.partition(";")
                owner_cls = cls_part
                name = rest.split("(")[0].split(":")[0]
                kind = "method" if "(" in rest else "field"
            else:
                owner_cls, name, kind = owner, item.get("name", ""), item.get("kind", "class")
            official = i2o_1201.get(owner_cls, "?")
            sources = item.get("sources", [])
            row = {
                "bucket": bucket,
                "symbol": official if (kind == "class" and not name) else f"{official}#{name}",
                "kind": kind,
                "desc": item.get("desc", ""),
                "refs": item.get("refs", 0),
                # only when *every* reference sits in a bundled Fabric API module: a mixed
                # row still has Sodium code calling it, so it stays Sodium's blocker
                "api_jar": bool(sources) and all(s.startswith("net/fabricmc/") for s in sources),
                "status": "",
                "where": "",
                "detail": "",
            }

            if kind == "class" and not name:
                if official in cls1211:
                    row["status"] = "re-ID"
                    row["where"] = o2i_1211.get(official, "present in 1.21.1")
                else:
                    row["status"] = "removed"
                rows.append(row)
                continue

            want = inter_desc_to_official(row["desc"]) if row["desc"] else ""
            if name == "<init>":
                # intermediary omits constructors (the name is identical in both
                # namespaces), so they can only be resolved from the Mojang side
                here = ctors_1211.get(official, [])
                row["symbol"] = f"{official}#<init>"
                if official not in ctors_1201:
                    row["status"] = "removed"
                    row["where"] = "class gone in 1.21.1"
                elif want and want in here:
                    row["status"] = "re-ID"
                    row["where"] = "constructor unchanged"
                elif here:
                    row["status"] = "re-signed"
                    row["where"] = (pretty(want) if want else "?") + " -> " + "; ".join(
                        pretty(d) for d in here[:2])
                else:
                    row["status"] = "removed"
                    row["where"] = "no constructor in 1.21.1"
                rows.append(row)
                continue
            cands = by_cls_inter.get((official, kind, name))
            declared_elsewhere = False
            if not cands:
                cands = [(c[1], c[2]) for c in by_inter.get((kind, name), [])]
                declared_elsewhere = bool(cands)
            if not cands:
                row["status"] = "unresolved"
                if kind == "field":
                    row["where"] = "field not in the 1.20.1 Mojang member list"
                elif any(x.startswith("net/fabricmc/") for x in sources):
                    row["where"] = "declared by a Fabric API interface, absent from vanilla mappings"
                else:
                    row["where"] = "inherited from a superclass, so not declared here"
                rows.append(row)
                continue

            pick = next((c for c in cands if want and c[1] == want), cands[0])
            official_name, desc1201 = pick
            # where the member was actually declared in 1.20.1 (the owner or a superclass)
            decl = official if not declared_elsewhere else next(
                c[0] for c in by_inter[(kind, name)] if c[2] == desc1201)
            row["symbol"] = f"{official}#{official_name}"
            row["detail"] = pretty(desc1201)

            same = members_1211.get((decl, kind, official_name))
            if same is not None and same == desc1201:
                row["status"] = "re-ID"
                row["where"] = "same signature" if decl == official else f"inherited from {decl}"
            elif same is not None:
                row["status"] = "re-signed"
                row["where"] = f"{pretty(desc1201)} -> {pretty(same)}"
            elif decl != official:
                # declared on a superclass: report what happened to that declaration, not
                # a name-only guess elsewhere in the tree
                row["status"] = "removed"
                row["where"] = f"gone from {decl} in 1.21.1"
            else:
                row["status"] = "removed"
                row["where"] = ""
            rows.append(row)

    if as_json:
        print(json.dumps(rows, indent=2, ensure_ascii=False))
        return 0

    print(f"{'bucket':13} {'status':10} {'1.20.1 symbol':60} {'1.21.1 / detail'}")
    print("-" * 150)
    for row in rows:
        flag = " [API]" if row["api_jar"] else ""
        tail = (row.get("where") or row.get("detail") or "")[:46]
        print(f"{row['bucket']:13} {row['status']:10} {row['symbol'][:58]:60} {tail}{flag}")

    print()
    counts: dict[tuple[str, str], int] = {}
    for row in rows:
        scope = "api-jar" if row["api_jar"] else "sodium"
        counts[(scope, row["status"])] = counts.get((scope, row["status"]), 0) + 1
    for (scope, status), n in sorted(counts.items()):
        print(f"{scope:8} {status:10} {n}")
    unresolved = [r["symbol"] for r in rows if r["status"] == "unresolved"]
    if unresolved:
        print("\nunresolved (listed, not dropped):")
        for sym in unresolved:
            print(" ", sym)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
