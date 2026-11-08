#!/usr/bin/env python3
"""Symbol-level damage report for a folder of Forge 1.20.1 mod jars.

Forge production jars for 1.20.1 carry OFFICIAL class names (net.minecraft.world.item.ItemStack)
with SRG member names (m_/f_XXXXX_). That makes the whole reference surface checkable without
launching anything:

    srg member --(mcp_config joined.tsrg)--> obf member --(Mojang official 1.20.1 mappings)-->
    official member name --> checked against the 1.21.1 official member universe
    (client-1.21.1-mappings.txt), with descriptors compared in official space on both sides.

    python tools/forge_symbol_damage.py --mods <dir> --out report.json [--markdown report.md]

Per mod: missingClass / missingMember / descMismatch counts plus the symbols themselves,
forge/NeoForge API references, and unresolvable SRG ids. This is ANALYSIS ONLY - it says
nothing about whether a mod would actually run on NeoForge (no runtime claim whatsoever).
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import struct
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TARGET_DIR = ROOT / "work" / "target"

PRIM = {"V", "Z", "B", "S", "C", "I", "J", "F", "D"}


# ----------------------------------------------------------------- mappings


class Mojmap:
    """One version's official (Mojang) mappings: obf <-> named, with member descriptors."""

    def __init__(self, path: Path):
        self.obf_to_named: dict[str, str] = {}
        self.named_to_obf: dict[str, str] = {}
        # (namedCls, kind, obfM) -> list[(namedM, descOrType)] - one obf name can serve a
        # static AND an instance member of a class, so the official name is picked by desc
        self.named_by_obf: dict[tuple[str, str, str], list[tuple[str, str]]] = {}
        # methods: (namedCls, namedM) -> set of descs in official slash space
        self.named_method_descs: dict[tuple[str, str], set[str]] = {}
        self.named_fields: dict[tuple[str, str], set[str]] = {}  # field type (slash space)
        cls_re = re.compile(r"^(\S+) -> (\S+):$")
        method_re = re.compile(r"^(?:\d+:\d+:)?(\S.*?) (\S+)\((.*)\) -> (\S+)$")
        field_re = re.compile(r"^(\S+) (\S+) -> (\S+)$")
        cur_named = None
        for raw in path.read_text(encoding="utf-8").splitlines():
            if raw.startswith("#") or not raw:
                continue
            if not raw.startswith((" ", "\t")):
                m = cls_re.match(raw)
                if m:
                    cur_named = m.group(1)
                    self.obf_to_named[m.group(2)] = cur_named
                    self.named_to_obf.setdefault(cur_named, m.group(2))
                continue
            if cur_named is None:
                continue
            body = raw.strip()
            m = method_re.match(body)
            if m and "(" in body:
                ret, name, args, obf = m.group(1), m.group(2), m.group(3), m.group(4)
                desc = _official_desc(args, ret)
                self.named_method_descs.setdefault((cur_named, name), set()).add(desc)
                self.named_by_obf.setdefault((cur_named, "method", obf), []).append((name, desc))
                continue
            m = field_re.match(body)
            if m and "(" not in body:
                typ, name, obf = m.group(1), m.group(2), m.group(3)
                t = _official_type(typ)
                self.named_fields.setdefault((cur_named, name), set()).add(t)
                self.named_by_obf.setdefault((cur_named, "field", obf), []).append((name, t))


def _official_type(t: str) -> str:
    t = t.strip()
    dims = 0
    while t.endswith("[]"):
        dims += 1
        t = t[:-2]
    if t in PRIM:
        base = t
    else:
        base = "L" + t.replace(".", "/") + ";"
    return "[" * dims + base


def _official_desc(args: str, ret: str) -> str:
    params = "".join(_official_type(p) for p in args.split(",") if p.strip())
    return f"({params}){_official_type(ret)}"


class SrgChain:
    """joined.tsrg (tsrg2 obf srg id): per obf class, srg<->obf member names.

    SRG member ids are globally unique, and mods reference inherited members through the
    receiver type (Player.m_21120_ declared on LivingEntity) - so the lookup goes through a
    global srg -> (obfClass, kind, obfName) index, not the receiver's own member table.
    """

    def __init__(self, zip_path: Path):
        with zipfile.ZipFile(zip_path) as z:
            lines = z.read("config/joined.tsrg").decode("utf-8").splitlines()
        self.obf_cls_members: dict[str, dict[str, str]] = {}  # obfClass -> {kind+obfM: srgM}
        self.srg_index: dict[str, tuple[str, str, str]] = {}  # srg -> (obfClass, kind, obfM)
        cur = None
        for line in lines:
            if line.startswith("tsrg2"):
                continue
            if not line.startswith("\t"):
                p = line.split(" ")
                cur = p[0]
            elif cur:
                p = line[1:].split(" ")
                if len(p) < 2:
                    continue  # tsrg2 "\t\tstatic" markers
                obf_m = p[0]
                if len(p) >= 3 and p[1].startswith("("):
                    srg_m = p[2]  # method row: obf, obfDesc, srg, id
                else:
                    srg_m = p[1]  # field row: obf, srg, id
                if srg_m in ("<init>", "<clinit>") or not srg_m.startswith(("m_", "f_", "func_", "field_")):
                    continue
                kind = "method" if srg_m.startswith(("m_", "func_")) else "field"
                self.obf_cls_members.setdefault(cur, {})[kind + "|" + obf_m] = srg_m
                self.srg_index.setdefault(srg_m, (cur, kind, obf_m))

    def official_member(self, src: Mojmap, named_cls: str, srg: str, desc: str | None = None):
        """srg member -> (kind, officialName, declaringOfficialClass) or None.

        The declaration may live on an ancestor of the receiver class (mods reference through
        the receiver type), and one obf name can serve a static plus an instance member of the
        same class - so the official name is picked by descriptor when the caller has one.
        """
        hit = self.srg_index.get(srg)
        if not hit:
            return None
        obf_cls, kind, obf_m = hit
        named_cls_decl = src.obf_to_named.get(obf_cls)
        if not named_cls_decl:
            return None
        candidates = src.named_by_obf.get((named_cls_decl, kind, obf_m)) or []
        if not candidates:
            return None
        if desc is not None:
            for name, d in candidates:
                if d == desc:
                    return kind, name, named_cls_decl
        return kind, candidates[0][0], named_cls_decl


# ----------------------------------------------------------------- class scanning


def scan_refs(class_bytes: bytes) -> list[tuple[str, str, str]]:
    """All (owner, name, desc) method/field refs in one class file's constant pool."""
    out = []
    buf = class_bytes
    pos = 10  # magic(4) minor(2) major(2) -> cp_count at 8; keep simple: parse from 8

    def u2(p):
        return (buf[p] << 8) | buf[p + 1]

    cp_count = u2(8)
    pool = {}
    p = 10
    i = 1
    while i < cp_count:
        tag = buf[p]
        p += 1
        if tag == 1:
            ln = u2(p)
            pool[i] = ("utf8", buf[p + 2:p + 2 + ln])
            p += 2 + ln
        elif tag in (7, 8, 16, 19, 20):
            pool[i] = ("ref", u2(p))
            p += 2
        elif tag == 15:
            p += 3
        elif tag in (3, 4):
            p += 4
        elif tag == 5 or tag == 6:
            p += 8
            i += 1
        elif tag in (9, 10, 11):  # Field/Method/InterfaceMethodref: class + nat
            pool[i] = ("member", u2(p), u2(p + 2))
            p += 4
        elif tag == 12:  # NameAndType
            pool[i] = ("nat", u2(p), u2(p + 2))
            p += 4
        elif tag in (17, 18):
            p += 4
        i += 1
    for entry in pool.values():
        if entry[0] == "member":
            _t, cls_idx, nat_idx = entry
            cls = pool.get(cls_idx)
            nat = pool.get(nat_idx)
            if not cls or not nat or cls[0] != "ref" or nat[0] != "nat":
                continue
            cname = pool.get(cls[1])
            nm = pool.get(nat[1])
            dm = pool.get(nat[2])
            if not cname or cname[0] != "utf8" or not nm or not dm:
                continue
            out.append((cname[1].decode("utf-8", "replace"),
                        nm[1].decode("utf-8", "replace"),
                        dm[1].decode("utf-8", "replace")))
    return out


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def analyze_jar(jar: Path, src: Mojmap, dst: Mojmap, srg: SrgChain) -> dict:
    out = {"jar": jar.name, "size": jar.stat().st_size, "sha256": sha256(jar),
           "classes": 0, "mcRefs": 0, "forgeApiRefs": 0, "externalRefs": 0,
           "srgUnresolved": 0, "missingClass": {}, "missingMember": {}, "descMismatch": {}}
    def bump(d, key):
        d[key] = d.get(key, 0) + 1
    with zipfile.ZipFile(jar) as z:
        for name in z.namelist():
            if not name.endswith(".class"):
                continue
            out["classes"] += 1
            try:
                refs = scan_refs(z.read(name))
            except Exception:
                continue
            for owner, mname, desc in refs:
                if not (owner.startswith("net/minecraft/") or owner.startswith("com/mojang/")):
                    if owner.startswith(("net/minecraftforge/", "net/neoforged/", "cpw/mods/")):
                        out["forgeApiRefs"] += 1
                    else:
                        out["externalRefs"] += 1
                    continue
                out["mcRefs"] += 1
                named_owner = owner.replace("/", ".")
                if named_owner not in dst.named_to_obf:
                    bump(out["missingClass"], f"{owner} (class absent in 1.21.1)")
                    continue
                if not re.match(r"^[mf]_\d+_$", mname) and not mname.startswith(("func_", "field_")):
                    continue  # constructors <init> and non-SRG names: not member damage by name
                resolved = srg.official_member(src, named_owner, mname, desc)
                if resolved is None:
                    out["srgUnresolved"] += 1
                    bump(out["missingMember"], f"{owner}.{mname} {desc} (srg id not resolvable)")
                    continue
                kind, official_m, declared_cls = resolved
                if kind == "method":
                    descs = dst.named_method_descs.get((declared_cls, official_m))
                else:
                    descs = dst.named_fields.get((declared_cls, official_m))
                if not descs:
                    bump(out["missingMember"],
                         f"{owner}.{official_m} [{mname}] {desc} (member gone in 1.21.1, declared on {declared_cls})")
                    continue
                if desc not in descs:
                    example = sorted(descs)[0]
                    bump(out["descMismatch"],
                         f"{owner}.{official_m} [{mname}] {desc} -> {example}")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Per-mod symbol damage for Forge 1.20.1 jars against the 1.21.1 official surface (analysis only).")
    ap.add_argument("--mods", required=True, help="folder of Forge 1.20.1 mod jars")
    ap.add_argument("--srg", default=str(ROOT / "work" / "tmp" / "mcp-config-1.20.1.zip"),
                    help="mcp_config zip containing config/joined.tsrg (obf<->srg)")
    ap.add_argument("--out", required=True, help="output JSON path")
    ap.add_argument("--markdown", default=None, help="optional markdown report path")
    args = ap.parse_args()

    src = Mojmap(TARGET_DIR / "client-1.20.1-mappings.txt")
    dst = Mojmap(TARGET_DIR / "client-1.21.1-mappings.txt")
    srg = SrgChain(Path(args.srg))

    mods_dir = Path(args.mods)
    results = []
    for jar in sorted(mods_dir.glob("*.jar")):
        try:
            results.append(analyze_jar(jar, src, dst, srg))
        except Exception as e:  # keep going; record the failure honestly
            results.append({"jar": jar.name, "error": f"{type(e).__name__}: {e}"})

    doc = {"source": "Forge 1.20.1 (SRG members, official class names)",
           "target": "1.21.1 official member universe",
           "note": "static symbol analysis only; no runtime claim for NeoForge or anything else",
           "mods": results}
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")

    if args.markdown:
        lines = ["# Forge 1.20.1 -> 1.21.1 symbol damage (analysis only)", "",
                 "| jar | classes | MC refs | missingClass | missingMember | descMismatch | forgeApi |", "|---|---|---|---|---|---|---|"]
        for r in results:
            if "error" in r:
                lines.append(f"| {r['jar']} | ERROR: {r['error'][:60]} | | | | | |")
                continue
            lines.append(f"| {r['jar']} | {r['classes']} | {r['mcRefs']} | {len(r['missingClass'])} "
                         f"| {len(r['missingMember'])} | {len(r['descMismatch'])} | {r['forgeApiRefs']} |")
        Path(args.markdown).write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")

    total_missing = sum(len(r.get("missingMember", {})) for r in results if "error" not in r)
    print(f"mods analyzed: {len(results)}, total missingMember symbols: {total_missing} -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
