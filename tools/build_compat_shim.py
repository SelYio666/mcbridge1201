#!/usr/bin/env python3
"""Build the mcbridge-compat-shim Fabric mod (rule-free runtime shims for removed symbols).

Currently provides: ItemPredicate.ANY (class_2073.field_9640), re-added by mixin and
initialized to the same empty-predicate shape the fieldRedirect bridge builds. Compiled
against the 1.21.1 intermediary stub + sponge-mixin, packaged deterministically. The jar
lands in work/ only - the repository keeps 0 jars.

    python tools/build_compat_shim.py --stub work/cb/data/jars/client-1.21.1-intermediary.jar \
        --lib work/instances/fabric-1.21.1-server/libraries/net/fabricmc/sponge-mixin/<ver>/sponge-mixin-<ver>.jar \
        --out work/shim/mcbridge-compat-shim-0.1.0.jar
"""
import argparse
import os
import shutil
import struct
import subprocess
import sys
import zipfile

ACC_SYNTHETIC = 0x1000

# Mixin rejects non-private static fields, so every public static shim field must be marked
# synthetic in the compiled class (field resolution ignores the flag). Extend this map when
# new shim mixins are added.
SYNTHETIC_FIELDS = {"ItemPredicateAnyFieldMixin.class": ["field_9640"]}


def mark_field_synthetic(class_path: str, field_name: str) -> None:
    """Set ACC_SYNTHETIC on one field of a compiled class.

    Why: Mixin rejects every non-private static field in a mixin ("contains non-private
    static field", validateField) unless the field is private or SYNTHETIC. The shim's whole
    job is a PUBLIC static member named exactly like a removed 1.20.1 constant so foreign
    GETSTATIC sites resolve; field resolution ignores the synthetic flag entirely, so marking
    the compiled field synthetic passes Mixin's validator while keeping public access.
    """
    with open(class_path, "rb") as f:
        data = bytearray(f.read())

    def u2(p):
        return (data[p] << 8) | data[p + 1]

    pos = 8
    cp_count = u2(pos)
    pos += 2
    idx = 1
    while idx < cp_count:
        tag = data[pos]
        pos += 1
        if tag == 1:
            pos += 2 + u2(pos)
        elif tag in (7, 8, 16, 19, 20):
            pos += 2
        elif tag == 15:
            pos += 3
        elif tag in (9, 10, 11, 3, 4, 12, 17, 18):
            pos += 4
        elif tag in (5, 6):
            pos += 8
            idx += 1
        idx += 1
    # find the UTF8 index of the field name
    name_idx = None
    p = 8
    cnt = u2(p)
    p += 2
    j = 1
    while j < cnt:
        t = data[p]
        p += 1
        if t == 1:
            ln = u2(p)
            p += 2
            if data[p:p + ln] == field_name.encode():
                name_idx = j
            p += ln
        elif t in (7, 8, 16, 19, 20):
            p += 2
        elif t == 15:
            p += 3
        elif t in (9, 10, 11, 3, 4, 12, 17, 18):
            p += 4
        elif t in (5, 6):
            p += 8
            j += 1
        j += 1
    if name_idx is None:
        raise SystemExit(f"field {field_name} not found in {class_path}")
    pos += 2  # access_flags
    pos += 2  # this_class
    pos += 2  # super_class
    ifc_count = u2(pos)
    pos += 2 + 2 * ifc_count
    f_count = u2(pos)
    pos += 2
    for _ in range(f_count):
        access_pos = pos
        access = u2(access_pos)
        n_idx = u2(pos + 2)
        d_idx = u2(pos + 4)
        attr_count = u2(pos + 6)
        pos += 8
        for _ in range(attr_count):
            pos += 2
            alen = struct.unpack(">I", data[pos:pos + 4])[0]
            pos += 4 + alen
        if n_idx == name_idx:
            data[access_pos:access_pos + 2] = struct.pack(">H", access | ACC_SYNTHETIC)
            with open(class_path, "wb") as f:
                f.write(bytes(data))
            print(f"marked {field_name} synthetic in {os.path.basename(class_path)}")
            return
    raise SystemExit(f"field_info for {field_name} not found in {class_path}")


def main(argv=None):
    ap = argparse.ArgumentParser(description="Build the mcbridge compat shim mod")
    ap.add_argument("--stub", required=True, help="1.21.1 intermediary client jar (compile stub)")
    ap.add_argument("--lib", action="append", default=[], help="extra compile dependency (repeatable)")
    ap.add_argument("--out", required=True, help="output jar path")
    ap.add_argument("--src", default=os.path.join("compat-shim", "src"), help="shim source root")
    args = ap.parse_args(argv)

    java_home = os.environ.get("JAVA_HOME")
    if not java_home:
        print("JAVA_HOME is not set", file=sys.stderr)
        return 2
    javac = os.path.join(java_home, "bin", "javac.exe")
    if not os.path.exists(javac):
        javac = os.path.join(java_home, "bin", "javac")

    java_src = os.path.join(args.src, "java")
    resources = os.path.join(args.src, "resources")
    sources = []
    for root, _dirs, files in os.walk(java_src):
        for name in files:
            if name.endswith(".java"):
                sources.append(os.path.join(root, name))
    if not sources:
        print("no sources under", java_src, file=sys.stderr)
        return 2
    for needed in ("fabric.mod.json", "mcbridge-compat-shim.mixins.json"):
        if not os.path.exists(os.path.join(resources, needed)):
            print("missing", needed, file=sys.stderr)
            return 2

    build_dir = os.path.join("work", "tmp", "compat-shim-build")
    shutil.rmtree(build_dir, ignore_errors=True)
    os.makedirs(build_dir, exist_ok=True)
    classpath = os.pathsep.join([args.stub] + args.lib)
    cmd = [javac, "-nowarn", "-proc:none", "-encoding", "UTF-8", "-cp", classpath, "-d", build_dir] + sources
    print(" ".join(cmd))
    rc = subprocess.call(cmd)
    if rc != 0:
        return rc
    for root, _dirs, files in os.walk(build_dir):
        for name in files:
            for fname in SYNTHETIC_FIELDS.get(name, []):
                mark_field_synthetic(os.path.join(root, name), fname)
    for name in os.listdir(resources):
        shutil.copyfile(os.path.join(resources, name), os.path.join(build_dir, name))

    out_parent = os.path.dirname(os.path.abspath(args.out))
    os.makedirs(out_parent, exist_ok=True)
    with zipfile.ZipFile(args.out, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _dirs, files in os.walk(build_dir):
            for name in sorted(files):
                full = os.path.join(root, name)
                info = zipfile.ZipInfo(os.path.relpath(full, build_dir).replace(os.sep, "/"),
                                       date_time=(1980, 1, 1, 0, 0, 0))
                info.external_attr = 0o644 << 16
                zf.writestr(info, open(full, "rb").read(), zipfile.ZIP_DEFLATED)
    print("built", args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
