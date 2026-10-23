#!/usr/bin/env python3
"""Widen access flags in a class jar for compilation only.

Mixin sources sometimes need to name a package-private target type (for example
``MapRenderer.MapTexture`` in 1.21.1). The runtime jar gets public access through the mod's
access widener, but ``javac`` checks the class file flags directly. This tool copies a jar and
flips the requested classes (and their matching ``InnerClasses`` entries) to public; it changes
no bytecode offsets, so the copy stays a valid jar.

Usage:
  python tools/widen_stub.py --in <stub.jar> --out <widened.jar> \
      --class net/minecraft/class_330$class_331
"""
from __future__ import annotations

import argparse
import struct
import sys
import zipfile

# Payload size after the tag byte for fixed-size constant-pool entries.
CP_SIZES = {3: 4, 4: 4, 5: 8, 6: 8, 7: 2, 8: 2, 9: 4, 10: 4, 11: 4, 12: 4,
            15: 3, 16: 2, 17: 4, 18: 4, 19: 2, 20: 2}


class Reader:
    def __init__(self, data: bytes) -> None:
        self.data = data
        self.off = 0

    def u1(self) -> int:
        value = self.data[self.off]
        self.off += 1
        return value

    def u2(self) -> int:
        value = struct.unpack_from(">H", self.data, self.off)[0]
        self.off += 2
        return value

    def u4(self) -> int:
        value = struct.unpack_from(">I", self.data, self.off)[0]
        self.off += 4
        return value

    def skip(self, count: int) -> None:
        self.off += count


def parse_class(data: bytes) -> dict:
    """Return the offsets/indices needed to patch access flags and InnerClasses entries."""
    if data[:4] != b"\xca\xfe\xba\xbe":
        raise ValueError("not a class file")
    r = Reader(data)
    r.skip(8)  # magic, minor, major
    cp_count = r.u2()
    cp_names: list[bytes | None] = [None] * cp_count
    cp_class: list[int] = [0] * cp_count
    i = 1
    while i < cp_count:
        tag = r.u1()
        if tag == 1:  # Utf8
            length = r.u2()
            cp_names[i] = data[r.off:r.off + length]
            r.skip(length)
        elif tag == 7:  # Class -> name_index
            cp_class[i] = r.u2()
        elif tag in CP_SIZES:
            r.skip(CP_SIZES[tag])
            if tag in (5, 6):  # Long/Double take two constant-pool slots
                i += 1
        else:
            raise ValueError(f"unknown constant-pool tag {tag}")
        i += 1

    def class_name(index: int) -> bytes:
        return cp_names[cp_class[index]] if cp_class[index] else b""

    access_off = r.off
    r.skip(2)
    this_class = r.u2()
    this_name = class_name(this_class)
    r.skip(2)  # super_class
    r.skip(2 * r.u2())  # interfaces
    for _ in range(2):  # fields, then methods
        count = r.u2()
        for _ in range(count):
            r.skip(6)  # access, name, descriptor
            for _ in range(r.u2()):
                r.skip(2)  # attribute name index
                r.skip(r.u4())
    inner_entries = []
    for _ in range(r.u2()):
        attr_name = cp_names[r.u2()]
        length = r.u4()
        payload_off = r.off
        r.skip(length)
        if attr_name != b"InnerClasses":
            continue
        count = struct.unpack_from(">H", data, payload_off)[0]
        pos = payload_off + 2
        for _ in range(count):
            inner_idx, _outer_idx, _inner_name_idx, _flags = struct.unpack_from(">HHHH", data, pos)
            inner_entries.append((pos + 6, class_name(inner_idx)))
            pos += 8
    return {"access_off": access_off, "this_name": this_name, "inner_entries": inner_entries}


def patch_class(data: bytes, targets: set[bytes]) -> tuple[bytes, bool]:
    info = parse_class(data)
    out = bytearray(data)
    changed = False
    access = struct.unpack_from(">H", out, info["access_off"])[0]
    if info["this_name"] in targets and not access & 0x0001:
        struct.pack_into(">H", out, info["access_off"], access | 0x0001)
        changed = True
    for flags_off, inner_name in info["inner_entries"]:
        if inner_name not in targets:
            continue
        flags = struct.unpack_from(">H", out, flags_off)[0]
        widened = (flags & ~0x0006) | 0x0001  # clear private/protected, set public
        if widened != flags:
            struct.pack_into(">H", out, flags_off, widened)
            changed = True
    return bytes(out), changed


def widen_jar(src: str, dst: str, classes: list[str]) -> int:
    targets = {c.replace(".", "/").encode("utf-8") for c in classes}
    patched: list[str] = []
    with zipfile.ZipFile(src) as zin:
        entries = [(info, zin.read(info.filename)) for info in zin.infolist()]
    with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as zout:
        for info, data in entries:
            if info.filename.endswith(".class"):
                data, changed = patch_class(data, targets)
                if changed:
                    patched.append(info.filename)
            new_info = zipfile.ZipInfo(info.filename, date_time=(1980, 1, 1, 0, 0, 0))
            new_info.compress_type = zipfile.ZIP_DEFLATED
            zout.writestr(new_info, data)
    print(f"widened {len(patched)} class(es) -> {dst}: {', '.join(sorted(patched))}")
    return 0 if patched else 3


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="src", required=True)
    ap.add_argument("--out", dest="dst", required=True)
    ap.add_argument("--class", dest="classes", action="append", required=True)
    args = ap.parse_args(argv)
    try:
        return widen_jar(args.src, args.dst, args.classes)
    except Exception as exc:  # noqa: BLE001 - CLI reports the exact failure
        print(f"widen failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
