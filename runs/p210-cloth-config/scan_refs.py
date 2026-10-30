"""List every Minecraft member a 1.20.1 jar references that 1.21.1 does not have (p210).

Running the client and waiting for the next exception takes one round trip per broken member, and
each round trip hides the rest: Cloth Config failed on `Screen.field_44669`, then on twelve final
`method_25394` overrides, then on `TextFieldWidget.method_1870()` - three runs to learn what a
constant-pool walk answers in one second.

This reads the constant pool of every class in the jar (no ASM, no javap parsing) and resolves each
`net/minecraft/...` Fieldref/Methodref against the 1.21.1 intermediary jar, walking superclasses and
interfaces. Only *missing* members are reported: a member that exists but threw at runtime is a
different question (signature-invisible, e.g. a class that must be `final`), and pretending this
scan replaces the live run would be the same mistake in the other direction.

Usage:
  python runs/p210-cloth-config/scan_refs.py --jar work/tmp/p210/cloth-patched.jar \
      --out runs/p210-cloth-config/refs-after.json
"""
import argparse
import json
import struct
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CLIENT = ROOT / "work" / "cb" / "data" / "jars" / "client-1.21.1-intermediary.jar"

TAG_UTF8, TAG_CLASS, TAG_STRING = 1, 7, 8
TAG_FIELDREF, TAG_METHODREF, TAG_INTERFACEMETHODREF = 9, 10, 11
TAG_NAMEANDTYPE = 12
TAG_METHODHANDLE, TAG_METHODTYPE, TAG_DYNAMIC, TAG_INVOKEDYNAMIC = 15, 16, 17, 18
TAG_MODULE, TAG_PACKAGE = 19, 20


def parse_class(data: bytes) -> dict:
    """Return {"this": name, "super": name, "interfaces": [...], "refs": [(tag, owner, name, desc)]}."""
    off = 8  # magic + minor + major
    (cp_count,) = struct.unpack_from(">H", data, off)
    off += 2
    pool: dict[int, tuple] = {}
    i = 1
    while i < cp_count:
        tag = data[off]
        off += 1
        if tag == TAG_UTF8:
            (length,) = struct.unpack_from(">H", data, off)
            off += 2
            pool[i] = (TAG_UTF8, data[off:off + length].decode("utf-8", "replace"))
            off += length
        elif tag in (3, 4):  # Integer, Float
            off += 4
        elif tag in (5, 6):  # Long, Double take two slots
            off += 8
            i += 1
        elif tag in (TAG_CLASS, TAG_STRING, TAG_METHODTYPE, TAG_MODULE, TAG_PACKAGE):
            (idx,) = struct.unpack_from(">H", data, off)
            off += 2
            pool[i] = (tag, idx)
        elif tag in (TAG_FIELDREF, TAG_METHODREF, TAG_INTERFACEMETHODREF):
            cls, nt = struct.unpack_from(">HH", data, off)
            off += 4
            pool[i] = (tag, cls, nt)
        elif tag == TAG_NAMEANDTYPE:
            name, desc = struct.unpack_from(">HH", data, off)
            off += 4
            pool[i] = (tag, name, desc)
        elif tag == TAG_METHODHANDLE:
            off += 3
        elif tag in (TAG_DYNAMIC, TAG_INVOKEDYNAMIC):
            off += 4
        else:
            raise ValueError(f"unknown constant pool tag {tag}")
        i += 1

    (access, this_idx, super_idx) = struct.unpack_from(">HHH", data, off)
    off += 6
    (iface_count,) = struct.unpack_from(">H", data, off)
    off += 2
    ifaces = list(struct.unpack_from(f">{iface_count}H", data, off)) if iface_count else []

    def utf8(idx: int) -> str:
        entry = pool.get(idx)
        return entry[1] if entry and entry[0] == TAG_UTF8 else ""

    def cls_name(idx: int) -> str:
        entry = pool.get(idx)
        return utf8(entry[1]) if entry and entry[0] == TAG_CLASS else ""

    refs = []
    for entry in pool.values():
        if entry[0] in (TAG_FIELDREF, TAG_METHODREF, TAG_INTERFACEMETHODREF):
            _, cls, nt = entry
            nat = pool.get(nt)
            if not nat or nat[0] != TAG_NAMEANDTYPE:
                continue
            refs.append((entry[0], cls_name(cls), utf8(nat[1]), utf8(nat[2])))
    return {
        "this": cls_name(this_idx),
        "super": cls_name(super_idx),
        "interfaces": [cls_name(x) for x in ifaces],
        "refs": refs,
    }


# Every chain ends in Object, and enums in Enum, neither of which is in the client jar. Without
# these two entries "does class_342.method_1870() exist?" and "does this enum have ordinal()?"
# would both answer "cannot tell", which is exactly the ambiguity that made the first version
# report 0 gaps for a jar that then threw NoSuchMethodError on method_1870.
JDK_TAIL = {
    "java/lang/Object": {
        "fields": set(),
        "methods": {("<init>", "()V"), ("equals", "(Ljava/lang/Object;)Z"), ("hashCode", "()I"),
                    ("toString", "()Ljava/lang/String;"), ("getClass", "()Ljava/lang/Class;"),
                    ("clone", "()Ljava/lang/Object;"), ("notify", "()V"), ("notifyAll", "()V"),
                    ("wait", "()V"), ("wait", "(J)V"), ("wait", "(JI)V"),
                    ("finalize", "()V")},
        "super": "", "interfaces": [],
    },
    "java/lang/Enum": {
        "fields": set(),
        "methods": {("name", "()Ljava/lang/String;"), ("ordinal", "()I"),
                    ("compareTo", "(Ljava/lang/Enum;)I"), ("compareTo", "(Ljava/lang/Object;)I"),
                    ("getDeclaringClass", "()Ljava/lang/Class;"),
                    ("describeConstable", "()Ljava/util/Optional;")},
        "super": "java/lang/Object", "interfaces": [],
    },
}


def index_jar(path: Path) -> dict[str, dict]:
    """class name -> {"fields": set, "methods": set, "super": str, "interfaces": [str]}."""
    out: dict[str, dict] = {}
    with zipfile.ZipFile(path) as z:
        for name in z.namelist():
            if not name.endswith(".class") or name.startswith("META-INF/"):
                continue
            data = z.read(name)
            try:
                info = parse_class(data)
            except Exception:
                continue
            fields, methods = find_members(data, info)
            out[info["this"]] = {"fields": fields, "methods": methods,
                                 "super": info["super"], "interfaces": info["interfaces"]}
    for name, entry in JDK_TAIL.items():
        out.setdefault(name, entry)
    return out


def find_members(data: bytes, info: dict) -> tuple[set, set]:
    """Second pass: read the field/method tables, which sit after the interfaces."""
    off = 8
    (cp_count,) = struct.unpack_from(">H", data, off)
    off += 2
    pool: dict[int, tuple] = {}
    i = 1
    while i < cp_count:
        tag = data[off]
        off += 1
        if tag == TAG_UTF8:
            (length,) = struct.unpack_from(">H", data, off)
            off += 2
            pool[i] = (TAG_UTF8, data[off:off + length].decode("utf-8", "replace"))
            off += length
        elif tag in (3, 4):
            off += 4
        elif tag in (5, 6):
            off += 8
            i += 1
        elif tag in (TAG_CLASS, TAG_STRING, TAG_METHODTYPE, TAG_MODULE, TAG_PACKAGE):
            off += 2
        elif tag in (TAG_FIELDREF, TAG_METHODREF, TAG_INTERFACEMETHODREF):
            off += 4
        elif tag == TAG_NAMEANDTYPE:
            off += 4
        elif tag == TAG_METHODHANDLE:
            off += 3
        elif tag in (TAG_DYNAMIC, TAG_INVOKEDYNAMIC):
            off += 4
        i += 1

    off += 6  # access, this, super
    (iface_count,) = struct.unpack_from(">H", data, off)
    off += 2 + iface_count * 2

    def utf8(idx: int) -> str:
        entry = pool.get(idx)
        return entry[1] if entry and entry[0] == TAG_UTF8 else ""

    fields, methods = set(), set()
    for target, is_method in ((fields, False), (methods, True)):
        (count,) = struct.unpack_from(">H", data, off)
        off += 2
        for _ in range(count):
            _access, name_idx, desc_idx, attr_count = struct.unpack_from(">HHHH", data, off)
            off += 8
            target.add((utf8(name_idx), utf8(desc_idx)))
            for _ in range(attr_count):
                (_attr_name, attr_len) = struct.unpack_from(">HI", data, off)
                off += 6 + attr_len
    return fields, methods


def resolve(index: dict[str, dict], owner: str, name: str, desc: str, is_field: bool):
    """True if the member is reachable from owner; False if it is missing; None if the walk left
    the indexed jar (java/lang/Enum, objectweb, ...) before finding it, i.e. undecidable here."""
    seen = set()
    unknown = False
    stack = [owner]
    while stack:
        cls = stack.pop()
        if cls in seen or not cls:
            continue
        seen.add(cls)
        entry = index.get(cls)
        if entry is None:
            # Not a class in the client jar: the superclass chain leaves Minecraft (Object, Enum)
            # or the reference points at a library. Continuing past it is what makes "inherited
            # from class_339" resolve at all - returning False here was the first version's bug,
            # and it reported 19 phantom gaps.
            unknown = True
            continue
        if (name, desc) in (entry["fields"] if is_field else entry["methods"]):
            return True
        stack.append(entry["super"])
        stack.extend(entry["interfaces"])
    return None if unknown else False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--jar", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    jar = Path(args.jar)
    if not jar.is_absolute():
        jar = ROOT / jar
    out = Path(args.out)
    if not out.is_absolute():
        out = ROOT / out

    index = index_jar(CLIENT)
    missing_classes: dict[str, set] = {}
    missing_members: dict[tuple, set] = {}
    checked = 0
    unchecked = 0

    with zipfile.ZipFile(jar) as z:
        for name in z.namelist():
            if not name.endswith(".class") or name.startswith("META-INF/"):
                continue
            data = z.read(name)
            try:
                info = parse_class(data)
            except Exception as exc:
                print(f"skip {name}: {exc}", file=sys.stderr)
                continue
            for tag, owner, member, desc in info["refs"]:
                if not owner.startswith("net/minecraft/"):
                    continue
                is_field = tag == TAG_FIELDREF
                checked += 1
                if owner not in index:
                    missing_classes.setdefault(owner, set()).add(info["this"])
                    continue
                verdict = resolve(index, owner, member, desc, is_field)
                if verdict is None:
                    unchecked += 1
                    continue
                if verdict is False:
                    key = (owner, member, desc, "field" if is_field else "method")
                    missing_members.setdefault(key, set()).add(info["this"])

    report = {
        "jar": str(jar),
        "jar_sha256": __import__("hashlib").sha256(jar.read_bytes()).hexdigest(),
        "client_index": str(CLIENT),
        "client_classes": len(index),
        "references_checked": checked,
        "references_unchecked": unchecked,
        "missing_classes": [{"owner": k, "used_by": sorted(v)[:6], "count": len(v)}
                            for k, v in sorted(missing_classes.items())],
        "missing_members": [
            {"owner": k[0], "name": k[1], "desc": k[2], "kind": k[3],
             "used_by": sorted(v)[:6], "count": len(v)}
            for k, v in sorted(missing_members.items(), key=lambda kv: -len(kv[1]))
        ],
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                   encoding="utf-8", newline="\n")
    print(f"{checked} MineCraft references checked against {len(index)} classes"
          f" ({unchecked} left the client jar and cannot be judged here)")
    print(f"missing classes: {len(report['missing_classes'])}")
    print(f"missing members: {len(report['missing_members'])}")
    for item in report["missing_members"][:25]:
        print(f"  {item['owner']}.{item['name']}{item['desc']}  x{item['count']}")
    for item in report["missing_classes"][:10]:
        print(f"  CLASS {item['owner']} x{item['count']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
