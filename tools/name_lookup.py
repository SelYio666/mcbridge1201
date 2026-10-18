"""Resolve intermediary names to Mojang (human) names by joining Fabric intermediary and
Mojang official mappings on the obfuscated names.

Usage:
  python tools/name_lookup.py <version> class net/minecraft/class_2073
  python tools/name_lookup.py <version> field net/minecraft/class_2073 field_9640
  python tools/name_lookup.py <version> method net/minecraft/class_1799 method_7948

Version data is read from work/target/intermediary-<ver>-v2.jar and
work/target/client-<ver>-mappings.txt (downloaded by tools/fetch_target_env.py).
"""
import os
import re
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load(ver):
    tjar = os.path.join(ROOT, "work", "target", f"intermediary-{ver}-v2.jar")
    mfile = os.path.join(ROOT, "work", "target", f"client-{ver}-mappings.txt")
    with zipfile.ZipFile(tjar) as z:
        tiny = z.read("mappings/mappings.tiny").decode("utf-8").splitlines()
    obf_to_inter, inter_to_obf = {}, {}
    members = {}  # (obfClass, kind, obfName) -> interName
    cur = None
    for line in tiny:
        if line.startswith("c\t"):
            p = line.split("\t")
            if len(p) >= 3:
                obf_to_inter[p[1]] = p[2]
                inter_to_obf[p[2]] = p[1]
                cur = p[1]
        elif line.startswith("\t") and cur:
            p = line.split("\t")
            if len(p) >= 4 and p[0] in ("\tm", "\tf"):
                members[(cur, "method" if p[0].strip() == "m" else "field", p[2])] = p[3]

    mojang_class = {}   # obf -> mojang
    mojang_member = {}  # (obfClass, kind, obfName) -> (mojangName, typeText)
    cur_obf = None
    for raw in open(mfile, encoding="utf-8"):
        if raw.startswith("#"):
            continue
        if not raw.startswith((" ", "\t")):
            m = re.match(r"^\s*(\S+) -> (\S+):$", raw)
            if m:
                mojang_class[m.group(2)] = m.group(1)
                cur_obf = m.group(2)
            continue
        m = re.match(r"^\s{4}(\S.*?) ([A-Za-z_$<][\w$<>]*)\((.*)\) -> (\S+)$", raw.strip())
        if m and cur_obf:
            mojang_member[(cur_obf, "method", m.group(4))] = (m.group(2), m.group(3))
            continue
        m = re.match(r"^\s{4}(\S+) ([A-Za-z_$][\w$]*) -> (\S+)$", raw.strip())
        if m and cur_obf:
            mojang_member[(cur_obf, "field", m.group(3))] = (m.group(2), m.group(1))
    return obf_to_inter, inter_to_obf, members, mojang_class, mojang_member


def main():
    ver, kind, cls = sys.argv[1], sys.argv[2], sys.argv[3]
    obf_to_inter, inter_to_obf, members, mojang_class, mojang_member = load(ver)
    obf = inter_to_obf.get(cls)
    if obf is None:
        print(f"{cls}: not in intermediary-{ver}")
        return 1
    print(f"{cls} (intermediary) -> obf {obf} -> Mojang {mojang_class.get(obf, '?')}")
    if kind == "class":
        return 0
    member = sys.argv[4]
    inter_member = members.get((obf, kind, member))
    print(f"  member {member} -> mojang {mojang_member.get((obf, kind, member))}  (intermediary {inter_member})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
