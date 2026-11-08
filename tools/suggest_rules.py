#!/usr/bin/env python3
"""Suggest conversion-rule drafts from an analyzer plan.json.

Joins the analyzer's per-symbol damage report (missingMember / descMismatch) with the
1.20.1 and 1.21.1 mapping chains (Fabric intermediary <-> obfuscated <-> Mojang named)
so every suggestion is backed by a mapped member identity, not a name guess.

    python tools/suggest_rules.py --plan <plan.json> [--artifact <substring>] \
        --out <dir> [--rules rules/fabric-1.21.1]

Outputs into the --out dir:
  suggestions.json   machine-readable: every draft with id, origin, confidence, evidence
  suggestions.md     human-readable table sorted by confidence
  draft-<artifact>.json  schema-shaped rule files (schemaVersion 0.1-draft, target fabric-1.21.1)
                         that can be pasted into rules/fabric-1.21.1/ once a human validates
                         the bridge body (patch hard-fails on rules whose bridge is missing)

Drafts never override existing rules: every candidate is checked against every rule file in
--rules for a matching match-key (same owner/name/desc the patcher would act on). Conflicting
candidates are dropped and reported, so running the tool over an already-passed mod must yield
either "already covered" notes or nothing.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

SOURCE_VERSION = "1.20.1"
TARGET_VERSION = "1.21.1"

SCHEMA_VERSION = "0.1-draft"
RULES_TARGET = "fabric-1.21.1"


def is_static_method(stub_jar: Path, internal_class: str, name: str, desc: str) -> bool | None:
    """Read ACC_STATIC for one method from an intermediary-named stub jar.

    callSiteAdaptation bridges are INVOKESTATIC: for an instance call the receiver stays on
    the stack and must become the bridge's first parameter, so bridgeDesc differs between
    the two shapes. Returns None when the member cannot be found (unknown call shape).
    """
    try:
        with zipfile.ZipFile(stub_jar) as z:
            data = z.read(internal_class + ".class")
    except (KeyError, FileNotFoundError, OSError):
        return None
    buf = data
    pos = 8  # magic + minor + major

    def u2(p):
        return int.from_bytes(buf[p:p + 2], "big"), p + 2

    def u4(p):
        return int.from_bytes(buf[p:p + 4], "big"), p + 4

    cp_count, pos = u2(pos)
    idx = 1
    while idx < cp_count:
        tag = buf[pos]
        pos += 1
        if tag == 1:  # Utf8
            pos += 2 + int.from_bytes(buf[pos:pos + 2], "big")
        elif tag in (7, 8, 16, 19, 20):  # Class, String, MethodType, Module, Package
            pos += 2
        elif tag == 15:  # MethodHandle
            pos += 3
        elif tag in (9, 10, 11, 3, 4, 12, 17, 18):  # refs, ints, floats, name+type, dynamic
            pos += 4
        elif tag in (5, 6):  # long, double (two slots)
            pos += 8
            idx += 1
        idx += 1
    _access, pos = u2(pos)
    _this, pos = u2(pos)
    _super, pos = u2(pos)
    ifc_count, pos = u2(pos)
    pos += 2 * ifc_count
    f_count, pos = u2(pos)
    for _ in range(f_count):
        _a, pos = u2(pos)
        _n, pos = u2(pos)
        _d, pos = u2(pos)
        attr_count, pos = u2(pos)
        for _ in range(attr_count):
            pos += 2  # attribute_name_index
            _len, pos = u4(pos)
            pos += _len
    m_count, pos = u2(pos)
    for _ in range(m_count):
        access, pos = u2(pos)
        n_idx, pos = u2(pos)
        d_idx, pos = u2(pos)
        # resolve name/desc through the constant pool: UTF8 entries
        def utf8(i):
            # walk the pool again for the i-th entry (small files; simple + correct)
            p = 8
            cnt, p = u2(p)
            j = 1
            while j < cnt:
                t = buf[p]
                p += 1
                if t == 1:
                    ln = int.from_bytes(buf[p:p + 2], "big")
                    p += 2
                    if j == i:
                        return buf[p:p + ln]
                    p += ln
                elif t in (7, 8, 16, 19, 20):
                    p += 2
                    if j == i:
                        return None  # indirect ref, not a UTF8
                elif t == 15:
                    p += 3
                elif t in (9, 10, 11, 3, 4, 12, 17, 18):
                    p += 4
                elif t in (5, 6):
                    p += 8
                    j += 1
                j += 1
            return None

        nm = utf8(n_idx)
        dm = utf8(d_idx)
        attr_count, pos = u2(pos)
        for _ in range(attr_count):
            pos += 2  # attribute_name_index
            _len, pos = u4(pos)
            pos += _len
        if nm == name.encode() and dm == desc.encode():
            return bool(access & 0x0008)
    return None

# ---------------------------------------------------------------- mapping loading


class Version:
    """Mapping chain for one Minecraft version: intermediary <-> obf <-> Mojang named."""

    def __init__(self, ver: str, target_dir: Path):
        self.version = ver
        tiny_jar = target_dir / f"intermediary-{ver}-v2.jar"
        mojmap = target_dir / f"client-{ver}-mappings.txt"
        for p in (tiny_jar, mojmap):
            if not p.exists():
                raise SystemExit(f"missing mapping input for {ver}: {p} (run tools/fetch_target_env.py)")
        self.obf_to_inter: dict[str, str] = {}
        self.inter_to_obf: dict[str, str] = {}
        # (obfClass, kind, obfName) -> (interName, obfDesc)
        self.members: dict[tuple[str, str, str], tuple[str, str]] = {}
        # (interClass, interName) -> (obfClass, obfName, obfDesc); ids are unique per member
        self.by_inter: dict[tuple[str, str], tuple[str, str, str]] = {}
        with zipfile.ZipFile(tiny_jar) as z:
            lines = z.read("mappings/mappings.tiny").decode("utf-8").splitlines()
        cur_obf = None
        for line in lines:
            if line.startswith("c\t"):
                p = line.split("\t")
                if len(p) >= 3:
                    cur_obf = p[1]
                    self.obf_to_inter.setdefault(p[1], p[2])
                    self.inter_to_obf.setdefault(p[2], p[1])
            elif line.startswith("\t") and cur_obf:
                p = line[1:].split("\t")  # member rows are "\tm|f\tdesc\tobfName\tinterName"
                if len(p) >= 4 and p[0] in ("m", "f"):
                    kind = "method" if p[0] == "m" else "field"
                    obf_desc, obf_name, inter_name = p[1], p[2], p[3]
                    self.members[(cur_obf, kind, obf_name)] = (inter_name, obf_desc)
                    self.by_inter.setdefault((self.obf_to_inter.get(cur_obf, cur_obf), inter_name),
                                             (cur_obf, obf_name, obf_desc))
        # Mojang official (ProGuard) mappings: obf -> named.
        # One obf name can serve several members of a class (instance vs static vs field
        # namespaces), and method rows carry line-range prefixes that split one method into
        # several rows - so every join is keyed by descriptor, never by name alone.
        self.obf_to_moj: dict[str, str] = {}
        self.moj_methods: dict[tuple[str, str], list[tuple[str, str]]] = {}   # (mojClass, mojName) -> [(desc, obfName)]
        self.moj_fields: dict[tuple[str, str], list[tuple[str, str]]] = {}   # (mojClass, mojName) -> [(type, obfName)]
        self.obf_moj_method: dict[tuple[str, str, str], str] = {}            # (obfClass, obfName, obfDescMoj) -> mojName
        self.obf_moj_field: dict[tuple[str, str], str] = {}                  # (obfClass, obfName) -> mojName
        cur_moj = None
        cur_obf = None
        cls_re = re.compile(r"^(\S+) -> (\S+):$")
        method_re = re.compile(r"^(?:\d+:\d+:)?(\S.*?) (\S+)\((.*)\) -> (\S+)$")
        field_re = re.compile(r"^(\S+) (\S+) -> (\S+)$")
        for raw in mojmap.read_text(encoding="utf-8").splitlines():
            if raw.startswith("#") or not raw:
                continue
            if not raw.startswith((" ", "\t")):
                m = cls_re.match(raw)
                if m:
                    cur_moj, cur_obf = m.group(1), m.group(2)
                    self.obf_to_moj[cur_obf] = cur_moj
                continue
            if cur_moj is None:
                continue
            body = raw.strip()
            m = method_re.match(body)
            if m and "(" in body:
                ret, name, args, obf = m.group(1), m.group(2), m.group(3), m.group(4)
                desc = f"({args}){ret}"
                self.moj_methods.setdefault((cur_moj, name), []).append((desc, obf))
                self.obf_moj_method.setdefault((cur_obf, obf, self._norm_moj_desc(desc)), name)
                continue
            m = field_re.match(body)
            if m and "(" not in body:
                typ, name, obf = m.group(1), m.group(2), m.group(3)
                self.moj_fields.setdefault((cur_moj, name), []).append((typ, obf))
                self.obf_moj_field.setdefault((cur_obf, obf), name)

    def _obf_of(self, moj_class: str) -> str:
        """Reverse of obf_to_moj, built once (a Mojang class name maps back to one obf name)."""
        cache = getattr(self, "_moj_to_obf", None)
        if cache is None:
            cache = {}
            for obf, moj in self.obf_to_moj.items():
                cache.setdefault(moj, obf)
            self._moj_to_obf = cache
        return cache.get(moj_class, moj_class)

    PRIM_MOJ = {"void": "V", "boolean": "Z", "char": "C", "byte": "B", "short": "S",
                "int": "I", "long": "J", "float": "F", "double": "D"}

    def _norm_moj_desc(self, moj_desc: str) -> str:
        """Normalize a Mojang-textual "(net.x.Y,int)void" descriptor to bytecode slash form."""
        if not moj_desc or "(" not in moj_desc:
            return moj_desc
        inner, ret = moj_desc[1:moj_desc.rindex(")")], moj_desc[moj_desc.rindex(")") + 1:]

        def norm(t: str) -> str:
            t = t.strip()
            dims = 0
            while t.endswith("[]"):
                dims += 1
                t = t[:-2]
            base = self.PRIM_MOJ.get(t) or ("L" + t.replace(".", "/") + ";")
            return "[" * dims + base

        return "(" + "".join(norm(t) for t in inner.split(",") if t.strip()) + ")" + norm(ret)

    def obf_desc_to_moj(self, obf_desc: str) -> str:
        """Translate an obfuscated-space bytecode descriptor to Mojang slash names on this version."""
        out = []
        i = 0
        while i < len(obf_desc):
            c = obf_desc[i]
            if c == "L":
                j = obf_desc.index(";", i)
                name = obf_desc[i + 1:j]
                moj = self.obf_to_moj.get(name)
                out.append("L" + (moj.replace(".", "/") if moj else name) + ";")
                i = j + 1
            elif c == ")":
                out.append(")")
                i += 1  # keep translating: the return type follows the paren
            else:
                out.append(c)
                i += 1
        return "".join(out)

    def inter_desc_to_obf(self, inter_desc: str) -> str:
        """Translate an intermediary-space descriptor to this version's obf space."""
        out = []
        i = 0
        while i < len(inter_desc):
            c = inter_desc[i]
            if c == "L":
                j = inter_desc.index(";", i)
                name = inter_desc[i + 1:j]
                obf = self.inter_to_obf.get(name, name)
                out.append("L" + obf + ";")
                i = j + 1
            elif c == ")":
                out.append(")")
                i += 1
            else:
                out.append(c)
                i += 1
        return "".join(out)

    def _desc_equiv(self, obf_desc: str, inter_desc: str) -> bool:
        return obf_desc == self.inter_desc_to_obf(inter_desc)

    # ---- identity helpers -------------------------------------------------

    def moj_class_of_inter(self, inter_class: str) -> str | None:
        obf = self.inter_to_obf.get(inter_class)
        return self.obf_to_moj.get(obf) if obf else None

    def inter_class_of_moj(self, moj_class: str) -> str | None:
        return self.obf_to_inter.get(self.moj_obf_of_class(moj_class)) if self.moj_obf_of_class(moj_class) else None

    def moj_obf_of_class(self, moj_class: str) -> str | None:
        # obf_to_moj is many-to-one in theory; build the reverse on demand
        if not hasattr(self, "_moj_to_obf"):
            rev: dict[str, str] = {}
            for obf, moj in self.obf_to_moj.items():
                rev.setdefault(moj, obf)
            self._moj_to_obf = rev
        return self._moj_to_obf.get(moj_class)

    def member_identity(self, inter_class: str, kind: str, inter_name: str,
                        inter_desc: str | None = None) -> dict | None:
        """Resolve (intermediary) member to obf + Mojang identity on this version.

        Mods reference inherited methods through the receiver type (e.g. Player.method_20235
        declared on LivingEntity), so a direct (class, name) miss falls back to name+descriptor
        matching across all classes. Descriptor comparison happens in Mojang space.
        """
        hit = self.by_inter.get((inter_class, inter_name))
        if hit is None and inter_name is not None and inter_desc is not None:
            for (cls, nm), row in self.by_inter.items():
                if nm != inter_name:
                    continue
                if self._desc_equiv(row[2], inter_desc):
                    hit = row
                    inter_class = cls
                    break
        if hit is None:
            return None
        obf_cls, obf_name, obf_desc = hit
        moj_cls = self.obf_to_moj.get(obf_cls)
        if kind == "method":
            moj_name = self.obf_moj_method.get((obf_cls, obf_name, self.obf_desc_to_moj(obf_desc)))
        else:
            moj_name = self.obf_moj_field.get((obf_cls, obf_name))
        if moj_name is None:
            return {"obfClass": obf_cls, "obfName": obf_name, "obfDesc": obf_desc,
                    "mojClass": moj_cls, "mojName": None, "mojDesc": None}
        moj_desc = self.obf_desc_to_moj(obf_desc)
        return {"obfClass": obf_cls, "obfName": obf_name, "obfDesc": obf_desc,
                "mojClass": moj_cls, "mojName": moj_name, "mojDesc": moj_desc}


def _guess_name(v: Version, obf_cls: str, kind: str, obf_name: str) -> str | None:
    """Descriptor-keyed Mojang name lookup (obf names are shared between member namespaces)."""
    return v.obf_moj_field.get((obf_cls, obf_name)) if kind == "field" else None


PRIMITIVES = {"V", "Z", "B", "S", "C", "I", "J", "F", "D"}


def translate_desc(desc: str, v: Version) -> str:
    """Translate an intermediary/obf-space descriptor to Mojang names on this version."""
    out = []
    i = 0
    while i < len(desc):
        c = desc[i]
        if c in PRIMITIVES:
            out.append(c)
            i += 1
        elif c == "[":
            j = i
            while desc[j] == "[":
                j += 1
            out.append(desc[i:j])
            i = j
        elif c == "L":
            j = desc.index(";", i)
            name = desc[i + 1:j]
            # dot-separated mojmap name with / separators for bytecode
            moj = v.obf_to_moj.get(v.inter_to_obf.get(name, name))
            out.append("L" + (moj.replace(".", "/") if moj else name) + ";")
            i = j + 1
        elif c == "(":
            out.append("(")
            i += 1
        elif c == ")":
            out.append(")" + desc[i + 1:])
            break
        else:
            out.append(c)
            i += 1
    return "".join(out)


def parse_params(moj_desc: str) -> list[str]:
    """Split a Mojang-textual method descriptor "(int,net.x.Y)V" into param type strings."""
    if not moj_desc or "(" not in moj_desc:
        return []
    inner = moj_desc[moj_desc.index("(") + 1:moj_desc.rindex(")")]
    return [p.strip() for p in inner.split(",") if p.strip()]


def diff_params(old: list[str], new: list[str]) -> dict:
    """Common prefix/suffix analysis between two parameter type lists."""
    pre = 0
    while pre < len(old) and pre < len(new) and old[pre] == new[pre]:
        pre += 1
    suf = 0
    while suf < len(old) - pre and suf < len(new) - pre and old[len(old) - 1 - suf] == new[len(new) - 1 - suf]:
        suf += 1
    return {
        "prefix": old[:pre],
        "suffix": old[len(old) - suf:] if suf else [],
        "oldMiddle": old[pre:len(old) - suf],
        "newMiddle": new[pre:len(new) - suf],
    }


# ---------------------------------------------------------------- rule loading (conflict check)


def load_existing_rules(rules_dir: Path) -> dict:
    """Collect every match key the existing rules would act on."""
    keys = {"fieldRedirects": set(), "methodRedirects": set(), "callSiteAdaptations": set(),
            "constructorRedirects": set(), "signatureAdaptations": set(), "methodRenames": set(),
            "callRewrites": set()}
    ids: set[str] = set()
    if not rules_dir.exists():
        return {"keys": keys, "ids": ids, "files": []}
    for path in sorted(rules_dir.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        for r in data.get("fieldRedirects", []) or []:
            keys["fieldRedirects"].add((r.get("sourceOwner"), r.get("sourceName"), r.get("sourceDesc")))
        for r in data.get("methodRedirects", []) or []:
            keys["methodRedirects"].add((r.get("sourceOwner"), r.get("sourceName") or None,
                                         r.get("sourceDesc") or None, r.get("sourceOpcode") or 0))
        for r in data.get("callSiteAdaptations", []) or []:
            keys["callSiteAdaptations"].add((r.get("sourceOwner"), r.get("sourceName"),
                                             r.get("sourceDesc"), r.get("sourceOpcode") or 0))
        for r in data.get("constructorRedirects", []) or []:
            keys["constructorRedirects"].add((r.get("owner"), r.get("desc")))
        for r in data.get("signatureAdaptations", []) or []:
            keys["signatureAdaptations"].add((r.get("targetClass"), r.get("methodName"), r.get("oldDesc")))
            for cr in r.get("callRewrites", []) or []:
                keys["callRewrites"].add((cr.get("owner"), cr.get("name"), cr.get("oldDesc")))
        for r in data.get("methodRenames", []) or []:
            keys["methodRenames"].add((r.get("owner"), r.get("oldName"), r.get("oldDesc")))
        for section in data.values():
            if isinstance(section, list):
                for r in section:
                    if isinstance(r, dict) and r.get("id"):
                        ids.add(r["id"])
    return {"keys": keys, "ids": ids, "files": sorted(p.name for p in rules_dir.glob("*.json"))}


def _opcode_overlap(a: int | None, b: int | None) -> bool:
    """0/None means any opcode, so it overlaps a pinned one."""
    a = a or 0
    b = b or 0
    return a == 0 or b == 0 or a == b


def conflicts(existing: dict, draft: dict) -> bool:
    keys = existing["keys"]
    kind = draft["kind"]
    if kind == "fieldRedirect":
        return (draft["sourceOwner"], draft["sourceName"], draft.get("sourceDesc")) in keys["fieldRedirects"]
    if kind == "methodRedirect":
        for (owner, name, desc, op) in keys["methodRedirects"]:
            if owner == draft["sourceOwner"] and _opcode_overlap(op, draft.get("sourceOpcode")):
                if name is None or draft.get("sourceName") is None or name == draft["sourceName"]:
                    if desc is None or draft.get("sourceDesc") is None or desc == draft["sourceDesc"]:
                        return True
        return False
    if kind == "callSiteAdaptation":
        for (owner, name, desc, op) in keys["callSiteAdaptations"]:
            if (owner == draft["sourceOwner"] and name == draft["sourceName"]
                    and desc == draft.get("sourceDesc") and _opcode_overlap(op, draft.get("sourceOpcode"))):
                return True
        # a signatureAdaptation's callRewrites already rewrites this exact call
        return (draft["sourceOwner"], draft["sourceName"], draft.get("sourceDesc")) in keys["callRewrites"]
    if kind == "signatureAdaptation":
        return (draft["targetClass"], draft["methodName"], draft.get("oldDesc")) in keys["signatureAdaptations"]
    return False


# ---------------------------------------------------------------- drafting


def slugify(*parts: str) -> str:
    s = ".".join(p for p in parts if p)
    s = re.sub(r"[^A-Za-z0-9.]+", "-", s)
    s = re.sub(r"-+", "-", s).strip("-.")
    return s.lower() or "draft"


def class_short(internal: str) -> str:
    if "/" in internal:
        internal = internal.rsplit("/", 1)[1]
    return internal.replace("class_", "c")


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def evidence_text(finding: dict, src: Version, dst: Version, mapping_note: str) -> str:
    sources = "; ".join(finding.get("sources", [])[:3])
    return (f"analyzer: {finding.get('analyzerWhere')} ref {finding.get('owner')}.{finding.get('name')} "
            f"{finding.get('desc')} (refs={finding.get('refs')}, presentInSource={finding.get('presentInSource')}); "
            f"callers: {sources}. {mapping_note}")


class Suggester:
    def __init__(self, src: Version, dst: Version, existing: dict, plan_path: Path,
                 source_stub: Path | None = None):
        self.src = src
        self.dst = dst
        self.existing = existing
        self.plan_path = plan_path
        self.plan_sha = sha256_of(plan_path)
        self.used_ids: set[str] = existing["ids"]
        self.source_stub = source_stub

    def _bridge_desc(self, owner: str, name: str, desc: str) -> tuple[str, str]:
        """bridgeDesc for an INVOKESTATIC replacement of this call.

        Instance calls keep the receiver on the stack, so the bridge's first parameter is the
        owner type. Returns (bridgeDesc, note).
        """
        static = is_static_method(self.source_stub, owner, name, desc) if self.source_stub else None
        if static is False:  # instance call: receiver becomes the bridge's first argument
            inner = desc[1:desc.index(")")]
            ret = desc[desc.index(")") + 1:]
            return f"(L{owner};{inner}){ret}", "instance call: bridge receives the receiver as first argument"
        if static is True:
            return desc, "static call: bridge signature equals the old descriptor"
        return desc, "call shape unknown (stub lookup failed): verify the receiver by hand"

    def _new_id(self, base: str) -> str:
        cand = base
        n = 2
        while cand in self.used_ids:
            cand = f"{base}-{n}"
            n += 1
        self.used_ids.add(cand)
        return cand

    def _common(self, finding: dict, where: str) -> dict:
        return {
            "origin": {
                "plan": self.plan_path.name,
                "planSha256": self.plan_sha,
                "artifact": where,
                "kind": finding["kind"] if finding.get("kind") else "method",
                "refs": finding.get("refs"),
                "presentInSource": finding.get("presentInSource"),
                "sources": finding.get("sources", [])[:5],
            },
        }

    def _finish(self, drafts: list[dict], dropped: list[dict], draft: dict, confidence: str,
                mapping_note: str, finding: dict, where: str) -> None:
        draft["confidence"] = confidence
        draft["evidence"] = evidence_text(finding, self.src, self.dst, mapping_note)
        if conflicts(self.existing, draft):
            dropped.append({"id": draft.get("id"), "reason": "an existing rule already covers this exact match key",
                            "draft": draft})
            return
        drafts.append(draft)

    # ---- descMismatch: the callee still exists but its descriptor changed ----

    def suggest_desc_mismatch(self, finding: dict, where: str) -> tuple[list[dict], list[dict], list[dict]]:
        drafts: list[dict] = []
        dropped: list[dict] = []
        notes: list[dict] = []
        m = re.match(r"target has same name in (\S+) with desc (.+)$", finding.get("note", ""))
        if not m:
            notes.append({"owner": finding["owner"], "name": finding["name"],
                          "reason": f"unrecognized note: {finding.get('note', '')}"})
            return drafts, dropped, notes
        new_owner, new_desc = m.group(1), m.group(2)
        old_desc = finding["desc"]
        old_moj_desc = translate_desc(old_desc, self.src)
        src_id = self.src.member_identity(finding["owner"], finding.get("kind", "method"), finding["name"], old_desc)
        dst_id = self.dst.member_identity(new_owner, finding.get("kind", "method"), finding["name"], new_desc)
        base = slugify(src_id["mojName"] or finding["name"], "callsite") if src_id and src_id["mojName"] \
            else slugify(class_short(finding["owner"]), finding["name"], "callsite")

        # Mojang-space comparison when both identities resolve
        moj_note = ""
        confidence = "medium"
        append_shape = False
        if src_id and dst_id and src_id["mojName"] and dst_id["mojName"]:
            if src_id["mojName"] == dst_id["mojName"]:
                confidence = "high"
                moj_note = (f"1.20.1 {src_id['mojClass']}.{src_id['mojName']} {old_moj_desc} -> "
                            f"1.21.1 {dst_id['mojClass']}.{dst_id['mojName']} {translate_desc(new_desc, self.dst)}")
                old_params = parse_params(old_moj_desc)
                new_params = parse_params(translate_desc(new_desc, self.dst))
                d = diff_params(old_params, new_params)
                append_shape = bool(d["oldMiddle"]) and all(
                    p == q for p, q in zip(reversed(d["oldMiddle"]), reversed(d["newMiddle"][-len(d["oldMiddle"]):]))
                ) if d["newMiddle"] else False
            else:
                moj_note = f"Mojang names differ across the chain: {src_id['mojName']} vs {dst_id['mojName']}"
        else:
            moj_note = "identity not fully resolved in mappings; descriptor change is from the analyzer note"

        where_owner = finding["owner"]
        common = self._common(finding, where)
        common["origin"]["targetOwner"] = new_owner
        common["origin"]["targetDesc"] = new_desc

        moj_name = (src_id or {}).get("mojName") or finding["name"]
        bridge_desc, shape_note = self._bridge_desc(where_owner, finding["name"], old_desc)
        call = {
            "kind": "callSiteAdaptation",
            "id": self._new_id(base),
            "sourceOwner": where_owner,
            "sourceName": finding["name"],
            "sourceDesc": old_desc,
            "targetOwner": new_owner,
            "targetName": finding["name"],
            "targetDesc": new_desc,
            "bridgeClass": "top/mcbridge1201/bridge/" + _bridge_class(base),
            "bridgeMethod": "adapt",
            "bridgeDesc": bridge_desc,
            "capability": "callsite.descriptor." + slugify(moj_name).replace(".", "-"),
            "risk": "medium",
            "note": ("bridge receives the old stack shape and must implement the 1.21.1 call; "
                     "confidence covers the identity mapping, not the bridge body. " + shape_note),
            **common,
        }
        self._finish(drafts, dropped, call, confidence, moj_note, finding, where)

        if append_shape:
            params = parse_params(old_moj_desc)
            adapt = {
                "kind": "signatureAdaptation",
                "id": self._new_id(slugify(src_id["mojName"] or finding["name"], "signature")),
                "targetClass": "(mod class that overrides this method - fill in by hand)",
                "methodName": finding["name"],
                "oldDesc": old_desc,
                "newDesc": new_desc,
                "paramSlot": len(params) + 1,
                "capability": "override.signature." + slugify(src_id["mojName"] or finding["name"]).replace(".", "-"),
                "risk": "medium",
                "note": ("pure trailing-parameter append; only valid if a mod class overrides the method "
                         "(analyzer cannot see overrides statically) - fill targetClass after checking"),
                **common,
            }
            self._finish(drafts, dropped, adapt, "medium", moj_note + " (append shape)", finding, where)
        return drafts, dropped, notes

    # ---- missingMember: the reference no longer resolves ----

    def suggest_missing_member(self, finding: dict, where: str) -> tuple[list[dict], list[dict], list[dict]]:
        drafts: list[dict] = []
        dropped: list[dict] = []
        notes: list[dict] = []
        owner, name = finding["owner"], finding["name"]
        kind = finding.get("kind", "method")
        old_desc = finding.get("desc", "")

        # 1) same intermediary id alive elsewhere in the target version
        relocs = []
        for (cls, nm), (_obf_cls, _obf_name, obf_desc) in self.dst.by_inter.items():
            if nm == name and cls != owner and kind == "method":
                relocs.append((cls, obf_desc))
        moved = [r for r in relocs if translate_desc(r[1], self.dst) == translate_desc(old_desc, self.src)]
        if moved:
            for cls, _d in moved[:3]:
                base = slugify(class_short(owner), name, "moved")
                bridge_desc, shape_note = self._bridge_desc(owner, name, old_desc)
                draft = {
                    "kind": "methodRedirect",
                    "id": self._new_id(base),
                    "sourceOwner": owner,
                    "sourceName": name,
                    "sourceDesc": old_desc,
                    "bridgeClass": "top/mcbridge1201/bridge/" + _bridge_class(base),
                    "bridgeMethod": "forward",
                    "bridgeDesc": bridge_desc,
                    "capability": "member.moved." + slugify(class_short(owner), name).replace(".", "-"),
                    "risk": "low" if kind == "method" else "medium",
                    "note": (f"same intermediary id {name} now lives on {cls} in 1.21.1; bridge forwards the call. "
                             + shape_note),
                    **self._common(finding, where),
                }
                self._finish(drafts, dropped, draft, "high",
                             f"member id {name} relocated from {owner} to {cls} (same descriptor)", finding, where)
            return drafts, dropped, notes

        # 2) identity via Mojang names on both sides
        src_id = self.src.member_identity(owner, kind, name, old_desc)
        if not src_id or not src_id["mojName"]:
            notes.append({"owner": owner, "name": name,
                          "reason": "member not found in the 1.20.1 mapping chain; no safe draft"})
            return drafts, dropped, notes
        moj_cls, moj_name = src_id["mojClass"], src_id["mojName"]
        if kind == "method":
            hits = self.dst.moj_methods.get((moj_cls, moj_name)) or []
        else:
            hits = self.dst.moj_fields.get((moj_cls, moj_name)) or []
        if hits:
            # same Mojang name exists in 1.21.1 under a different intermediary id; pick by descriptor
            obf_cls = self.dst.moj_obf_of_class(moj_cls)
            candidates = []
            for _payload, obf_name in hits:
                dst_member = self.dst.members.get((obf_cls, kind, obf_name))
                if dst_member:
                    candidates.append((dst_member[0], dst_member[1]))
            exact = [c for c in candidates
                     if translate_desc(c[1], self.dst) == translate_desc(old_desc, self.src)]
            chosen = exact[0] if exact else (candidates[0] if candidates else None)
            if chosen:
                new_inter, new_desc_inter = chosen
                same_desc = bool(exact)
                base = slugify(moj_name, "retarget" if kind == "method" else "field")
                if kind == "method":
                    bridge_desc, shape_note = self._bridge_desc(owner, name, old_desc)
                    draft = {
                        "kind": "methodRedirect",
                        "id": self._new_id(base),
                        "sourceOwner": owner,
                        "sourceName": name,
                        "sourceDesc": old_desc,
                        "bridgeClass": "top/mcbridge1201/bridge/" + _bridge_class(base),
                        "bridgeMethod": "forward",
                        "bridgeDesc": bridge_desc,
                        "capability": "member.renamed." + slugify(moj_name).replace(".", "-"),
                        "risk": "low" if same_desc else "medium",
                        "note": (f"{moj_cls}.{moj_name} is {new_inter} {new_desc_inter} in 1.21.1; "
                                 + ("same semantics, bridge forwards" if same_desc
                                    else "descriptor differs, bridge must convert") + ". " + shape_note),
                        **self._common(finding, where),
                    }
                    draft["origin"]["targetOwner"] = owner
                    draft["origin"]["targetName"] = new_inter
                    draft["origin"]["targetDesc"] = new_desc_inter
                    self._finish(drafts, dropped, draft, "high" if same_desc else "medium",
                                 f"1.20.1 {owner}.{name} = {moj_cls}.{moj_name}; 1.21.1 keeps it as {new_inter}",
                                 finding, where)
                else:
                    draft = {
                        "kind": "fieldRedirect",
                        "id": self._new_id(base),
                        "sourceOwner": owner,
                        "sourceName": name,
                        "sourceDesc": old_desc,
                        "bridgeClass": "top/mcbridge1201/bridge/" + _bridge_class(base),
                        "bridgeMethod": "get",
                        "bridgeDesc": "()" + old_desc,
                        "capability": "field.access." + slugify(moj_name).replace(".", "-"),
                        "risk": "medium",
                        "note": (f"field {moj_cls}.{moj_name} exists in 1.21.1 as {new_inter} but is not "
                                 "resolvable from mod code (private/removed constant) - bridge must supply "
                                 "the value or the semantic equivalent"),
                        **self._common(finding, where),
                    }
                    self._finish(drafts, dropped, draft, "medium",
                                 f"1.20.1 {owner}.{name} = {moj_cls}.{moj_name}; 1.21.1 has {new_inter}",
                                 finding, where)
                return drafts, dropped, notes
        # 3) nothing safe
        notes.append({"owner": owner, "name": name,
                      "reason": f"no {moj_name} continuation in 1.21.1 {moj_cls}; needs a semantic port, "
                                "not a mechanical rule"})
        return drafts, dropped, notes


def _bridge_class(base_slug: str) -> str:
    return "".join(p.capitalize() for p in re.split(r"[.\-]", base_slug) if p) + "Bridge"


# ---------------------------------------------------------------- main


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Suggest rule drafts from an analyzer plan.json (mapping-verified identities).")
    ap.add_argument("--plan", required=True, help="analyzer plan.json (mcbridge1201 analyze --out)")
    ap.add_argument("--artifact", action="append", default=[],
                    help="substring filter on artifact file names; repeatable; default: all")
    ap.add_argument("--target-dir", default=None,
                    help="directory holding intermediary-<ver>-v2.jar and client-<ver>-mappings.txt"
                         " (default: work/target)")
    ap.add_argument("--rules", default=str(ROOT / "rules" / RULES_TARGET),
                    help="rules directory for the conflict check")
    ap.add_argument("--source-stub", default=None,
                    help="intermediary-named 1.20.1 client stub jar (default: work/cb/data/jars/"
                         "client-1.20.1-intermediary.jar) used to read ACC_STATIC for bridgeDesc shapes")
    ap.add_argument("--out", required=True, help="output directory for suggestions.json/.md and drafts")
    args = ap.parse_args()

    target_dir = Path(args.target_dir) if args.target_dir else ROOT / "work" / "target"
    plan_path = Path(args.plan)
    plan = json.loads(plan_path.read_text(encoding="utf-8"))

    src = Version(SOURCE_VERSION, target_dir)
    dst = Version(TARGET_VERSION, target_dir)
    existing = load_existing_rules(Path(args.rules))
    stub = Path(args.source_stub) if args.source_stub else \
        ROOT / "work" / "cb" / "data" / "jars" / "client-1.20.1-intermediary.jar"
    sug = Suggester(src, dst, existing, plan_path, stub)

    artifacts = plan.get("artifacts", [])
    if args.artifact:
        artifacts = [a for a in artifacts if any(s in a["file"] for s in args.artifact)]

    all_drafts: list[dict] = []
    dropped: list[dict] = []
    notes: list[dict] = []
    covered = 0
    for art in artifacts:
        where = art["file"]
        for finding in art.get("descMismatch", []) or []:
            finding = dict(finding)
            finding["analyzerWhere"] = "descMismatch"
            d, dr, n = sug.suggest_desc_mismatch(finding, where)
            covered += len(d) + len(dr)
            all_drafts += d
            dropped += dr
            notes += n
        for finding in art.get("missingMember", []) or []:
            finding = dict(finding)
            finding["analyzerWhere"] = "missingMember"
            d, dr, n = sug.suggest_missing_member(finding, where)
            covered += len(d) + len(dr)
            all_drafts += d
            dropped += dr
            notes += n
        for kind, section in (("missingClass", "missingClass"), ("missingApiClass", "missingApiClass"),
                              ("missingApiMember", "missingApiMember")):
            for finding in art.get(section, []) or []:
                notes.append({"artifact": where, "kind": kind, "owner": finding.get("owner"),
                              "reason": "class/API-level gap: needs a port or shim decision, no mechanical rule"})

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    # per-artifact draft rule files (schema-shaped, paste-ready after human review)
    by_artifact: dict[str, list[dict]] = {}
    for d in all_drafts:
        by_artifact.setdefault(d["origin"]["artifact"], []).append(d)
    written = []
    for art, drafts in sorted(by_artifact.items()):
        stem = re.sub(r"[^A-Za-z0-9._-]+", "_", art)
        doc: dict = {"schemaVersion": SCHEMA_VERSION, "target": RULES_TARGET}
        for d in drafts:
            doc.setdefault(d["kind"] + "s", []).append(d)
        p = out_dir / f"draft-{stem}.json"
        p.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
        written.append(p.name)

    result = {
        "plan": str(plan_path),
        "planSha256": sug.plan_sha,
        "sourceVersion": SOURCE_VERSION,
        "targetVersion": TARGET_VERSION,
        "ruleFilesChecked": existing["files"],
        "drafts": all_drafts,
        "droppedConflicts": dropped,
        "notes": notes,
        "findingCoverage": covered,
        "draftFiles": written,
    }
    (out_dir / "suggestions.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                                              encoding="utf-8", newline="\n")

    lines = ["# Rule suggestions", "",
             f"plan: {plan_path} (sha256 {sug.plan_sha[:12]})", "",
             "| id | kind | confidence | target | note |", "|---|---|---|---|---|"]
    order = {"high": 0, "medium": 1, "low": 2}
    for d in sorted(all_drafts, key=lambda x: order.get(x.get("confidence"), 3)):
        tgt = d.get("targetOwner") or d.get("sourceOwner")
        lines.append(f"| {d['id']} | {d['kind']} | {d.get('confidence')} | {tgt}.{d.get('sourceName', '')} "
                     f"| {d.get('note', '')} |")
    if dropped:
        lines += ["", "## Dropped (would conflict with existing rules)", ""]
        for x in dropped:
            lines.append(f"- {x['id']}: {x['reason']}")
    if notes:
        lines += ["", "## No mechanical draft (needs human decision)", ""]
        for x in notes:
            lines.append(f"- {x.get('artifact', '')} {x.get('owner', '')}.{x.get('name', '')}: {x.get('reason')}")
    (out_dir / "suggestions.md").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")

    print(f"suggestions: {len(all_drafts)} draft(s), {len(dropped)} dropped conflict(s), "
          f"{len(notes)} note(s) -> {out_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
