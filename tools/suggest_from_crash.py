#!/usr/bin/env python3
"""Crash -> rule candidate loop: parse runtime linkage errors from a log, map each one to a
conversion-rule draft (or to an existing rule that already covers it), and print the
suggestion with its evidence line.

    python tools/suggest_from_crash.py --log <server/client/crash log> --out <dir> [--rules rules/fabric-1.21.1]

Parses NoSuchMethodError / NoSuchFieldError / NoClassDefFoundError / ClassNotFoundException
lines (quoted or bare, remapped names like net.minecraft.class_XXXX and external names
alike), converts dotted signatures to internal descriptors and reuses suggest_rules.py's
mapping machinery, so every candidate carries the same mapped identity + confidence +
evidence as the plan-driven path. Symbols that live outside the Minecraft/Fabric mapping
space (mod classes, third-party libraries) are reported as notes: they are dependency or
port problems, not conversion injuries a rule can carry.

Exit code 0 always (a log without linkage errors is a valid result, not a failure).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import suggest_rules as sr  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent

PRIM = {"void": "V", "boolean": "Z", "char": "C", "byte": "B", "short": "S",
        "int": "I", "long": "J", "float": "F", "double": "D"}

CLASS_RE = re.compile(r"(?:ClassNotFoundError|ClassNotFoundException|NoClassDefFoundError)\s*:\s*"
                      r"(?P<cls>[A-Za-z_$][\w$/.$]*)")


def dotted_to_internal_type(t: str) -> str:
    t = t.strip()
    dims = 0
    while t.endswith("[]"):
        dims += 1
        t = t[:-2].strip()
    base = PRIM.get(t) or ("L" + t.replace(".", "/") + ";")
    return "[" * dims + base


def dotted_desc(args: str, ret: str) -> str:
    params = "".join(dotted_to_internal_type(p) for p in args.split(",") if p.strip())
    return f"({params}){dotted_to_internal_type(ret)}"


def parse_log(log_path: Path) -> list[dict]:
    """Extract linkage errors with the raw evidence line for each."""
    findings: list[dict] = []
    seen = set()
    lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
    for i, raw in enumerate(lines):
        line = raw.strip()
        where = f"{log_path.name}:{i + 1}"
        if "NoSuchMethodError" in line:
            m = re.search(r"NoSuchMethodError:\s*(.+)$", line)
            sig = m.group(1).strip().strip("'\"")
            # shape: [ret] owner.name(args)
            m2 = re.match(r"(?:(\S+)\s+)?([\w$.]+)\.([\w$<>]+)\((.*)\)$", sig)
            if not m2:
                findings.append({"kind": "unparsed", "where": where, "line": line})
                continue
            ret, owner, name, args = m2.group(1) or "void", m2.group(2), m2.group(3), m2.group(4)
            desc = dotted_desc(args, ret)
            key = ("method", owner, name, desc)
            if key in seen:
                continue
            seen.add(key)
            findings.append({"kind": "method", "owner": owner, "name": name, "desc": desc,
                             "where": where, "line": line})
        elif "NoSuchFieldError" in line:
            m = re.search(r"NoSuchFieldError:\s*(.+)$", line)
            sig = m.group(1).strip().strip("'\"")
            m2 = re.match(r"([\w$.]+)\.([\w$]+)$", sig)
            if not m2:
                findings.append({"kind": "unparsed", "where": where, "line": line})
                continue
            key = ("field", m2.group(1), m2.group(2))
            if key in seen:
                continue
            seen.add(key)
            findings.append({"kind": "field", "owner": m2.group(1), "name": m2.group(2),
                             "desc": None, "where": where, "line": line})
        elif ("NoClassDefFoundError" in line or "ClassNotFoundException" in line) and "Caused by" in line:
            m = CLASS_RE.search(line)
            if not m:
                continue
            key = ("class", m.group("cls"))
            if key in seen:
                continue
            seen.add(key)
            findings.append({"kind": "class", "owner": m.group("cls"), "name": None, "desc": None,
                             "where": where, "line": line})
    return findings


def internal_class(dotted: str) -> str:
    return dotted.replace(".", "/")


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Map linkage errors from a crash log to rule drafts or existing rules.")
    ap.add_argument("--log", required=True, help="server/client log or crash report text")
    ap.add_argument("--rules", default=str(ROOT / "rules" / sr.RULES_TARGET),
                    help="existing rules directory for the already-covered check")
    ap.add_argument("--target-dir", default=None,
                    help="mapping inputs dir (default: work/target)")
    ap.add_argument("--source-stub", default=None,
                    help="1.20.1 intermediary stub for ACC_STATIC (default: work/cb/data/jars/...)")
    ap.add_argument("--out", required=True, help="output dir for crash-suggestions.json/.md")
    args = ap.parse_args()

    log_path = Path(args.log)
    target_dir = Path(args.target_dir) if args.target_dir else ROOT / "work" / "target"
    stub = Path(args.source_stub) if args.source_stub else \
        ROOT / "work" / "cb" / "data" / "jars" / "client-1.20.1-intermediary.jar"

    findings = parse_log(log_path)
    src = sr.Version(sr.SOURCE_VERSION, target_dir)
    dst = sr.Version(sr.TARGET_VERSION, target_dir)
    existing = sr.load_existing_rules(Path(args.rules))
    sug = sr.Suggester(src, dst, existing, log_path, stub)
    # origin text should quote the log, not call it a plan
    sug.plan_sha = hashlib.sha256(log_path.read_bytes()).hexdigest()

    results = []
    drafts = []
    for f in findings:
        item = {"evidenceLine": f.get("line"), "logRef": f.get("where")}
        if f["kind"] == "unparsed":
            item.update({"kind": "unparsed", "reason": "could not parse the signature; needs eyes"})
            results.append(item)
            continue
        owner = internal_class(f["owner"]) if f["owner"] else None
        if f["kind"] == "class":
            known = dst.inter_to_obf.get(owner) or src.inter_to_obf.get(owner)
            if known:
                item.update({"kind": "class", "owner": owner, "reason":
                             "MC class missing at runtime: conversion/loader problem, see analyzer missingClass"})
            else:
                item.update({"kind": "class", "owner": owner, "reason":
                             "not a Minecraft/Fabric symbol: dependency or nested-jar problem, "
                             "not something a conversion rule should paper over"})
            results.append(item)
            continue
        if f["kind"] == "field":
            fnd = {"owner": owner, "name": f["name"], "desc": f["desc"] or "",
                   "kind": "field", "refs": None, "presentInSource": None,
                   "sources": [f.get("line", "")[:120]], "analyzerWhere": "crash NoSuchFieldError"}
            d, dr, n = sug.suggest_missing_member(fnd, "crash:" + log_path.name)
            item.update({"kind": "field", "drafts": d, "dropped": dr, "notes": n})
            results.append(item)
            drafts += d
            continue
        # method
        owner_internal = internal_class(f["owner"])
        name = f["name"]
        desc = f["desc"]
        if name == "<init>":
            # constructor: existing constructorRedirect?
            hit = (owner_internal, desc) in existing["keys"]["constructorRedirects"]
            if hit:
                item.update({"kind": "constructor", "alreadyCovered":
                             "an existing constructorRedirect matches this exact call"})
                results.append(item)
                continue
            base = sr.slugify(owner_internal.rsplit("/", 1)[-1], "ctor")
            d = {
                "kind": "constructorRedirect",
                "id": sug._new_id(base),
                "sourceOwner": owner_internal,
                "sourceDesc": desc,
                "bridgeClass": "top/mcbridge1201/bridge/" + sr._bridge_class(base),
                "bridgeMethod": "create",
                "bridgeDesc": desc.replace(")V", ")" + "L" + owner_internal + ";"),
                "capability": "ctor.redirect." + sr.slugify(owner_internal.rsplit("/", 1)[-1]).replace(".", "-"),
                "risk": "medium",
                "note": ("bridge replaces new X(args) with a static factory; must reproduce the "
                         "1.20.1 constructor semantics against 1.21.1 API"),
                "origin": {"log": log_path.name, "logSha256": sug.plan_sha,
                           "evidenceLine": f.get("line")},
                "confidence": "medium",
                "evidence": f"crash: {f.get('line', '')}",
            }
            if sr.conflicts(existing, d):
                results.append({**item, "kind": "constructor", "dropped": True,
                                "reason": "existing rule already covers this match key"})
                continue
            drafts.append(d)
            results.append({**item, "kind": "constructor", "drafts": [d]})
            continue
        # plain method: (a) same owner+name exists in target with a different desc?
        dst_hit = dst.by_inter.get((owner_internal, name))
        if dst_hit:
            obf_desc = dst_hit[2]
            new_desc_inter = dst.inter_desc_to_obf_reverse(obf_desc) if hasattr(dst, "inter_desc_to_obf_reverse") else None
            # build the 1.21.1-side intermediary desc by translating obf->inter on dst
            out = []
            i = 0
            while i < len(obf_desc):
                c = obf_desc[i]
                if c == "L":
                    j = obf_desc.index(";", i)
                    on = obf_desc[i + 1:j]
                    inter = dst.obf_to_inter.get(on, on)
                    out.append("L" + inter + ";")
                    i = j + 1
                elif c == ")":
                    out.append(")")
                    i += 1
                else:
                    out.append(c)
                    i += 1
            new_desc_inter = "".join(out)
            if new_desc_inter != desc:
                bridge_desc, shape_note = sug._bridge_desc(owner_internal, name, desc)
                base = sr.slugify((src.member_identity(owner_internal, "method", name, desc) or {}).get("mojName") or name,
                                  "callsite")
                d = {
                    "kind": "callSiteAdaptation",
                    "id": sug._new_id(base),
                    "sourceOwner": owner_internal,
                    "sourceName": name,
                    "sourceDesc": desc,
                    "targetOwner": owner_internal,
                    "targetName": name,
                    "targetDesc": new_desc_inter,
                    "bridgeClass": "top/mcbridge1201/bridge/" + sr._bridge_class(base),
                    "bridgeMethod": "adapt",
                    "bridgeDesc": bridge_desc,
                    "capability": "callsite.descriptor." + sr.slugify(name).replace(".", "-"),
                    "risk": "medium",
                    "note": ("bridge receives the old stack shape; target keeps the same "
                             f"intermediary id {name} with a changed descriptor. " + shape_note),
                    "origin": {"log": log_path.name, "logSha256": sug.plan_sha,
                               "evidenceLine": f.get("line")},
                    "confidence": "high" if shape_note.startswith(("instance", "static")) else "medium",
                    "evidence": (f"crash: {f.get('line', '')}; 1.21.1 keeps {owner_internal}.{name} "
                                 f"with desc {new_desc_inter}"),
                }
                if sr.conflicts(existing, d):
                    item.update({"kind": "method", "alreadyCovered":
                                 "an existing rule already rewrites this call site"})
                    results.append(item)
                    continue
                drafts.append(d)
                results.append({**item, "kind": "method", "drafts": [d]})
                continue
        # (b) fall through to the plan-driven missing-member machinery
        fnd = {"owner": owner_internal, "name": name, "desc": desc, "kind": "method",
               "refs": None, "presentInSource": None,
               "sources": [f.get("line", "")[:120]], "analyzerWhere": "crash NoSuchMethodError"}
        d, dr, n = sug.suggest_missing_member(fnd, "crash:" + log_path.name)
        item.update({"kind": "method", "drafts": d, "dropped": dr, "notes": n})
        results.append(item)
        drafts += d

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    doc = {
        "log": str(log_path),
        "logSha256": sug.plan_sha,
        "findings": results,
        "drafts": drafts,
    }
    (out_dir / "crash-suggestions.json").write_text(
        json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")

    lines = ["# Crash -> rule suggestions", "", f"log: {log_path} (sha256 {sug.plan_sha[:12]})", ""]
    for r in results:
        lines.append(f"- `{r.get('evidenceLine', '')[:160]}`")
        if r.get("alreadyCovered"):
            lines.append(f"  -> already covered: {r['alreadyCovered']}")
        for d in r.get("drafts", []):
            lines.append(f"  -> draft {d['id']} ({d['kind']}, {d.get('confidence')}): {d.get('note', '')[:160]}")
        for x in r.get("dropped", []):
            lines.append(f"  -> dropped {x.get('id')}: {x.get('reason')}")
        for n in r.get("notes", []):
            lines.append(f"  -> note: {n.get('reason', '')}")
        if r.get("reason"):
            lines.append(f"  -> {r['reason']}")
    (out_dir / "crash-suggestions.md").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")

    print(f"findings: {len(results)}, drafts: {len(drafts)} -> {out_dir}")
    for r in results:
        ev = (r.get("evidenceLine") or "")[:110]
        print(f"  {ev}")
        for d in r.get("drafts", []):
            print(f"    -> {d['id']} ({d['kind']}, {d.get('confidence')})")
        if r.get("alreadyCovered"):
            print("    -> already covered by an existing rule")
        if r.get("reason"):
            print(f"    -> {r['reason'][:140]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
