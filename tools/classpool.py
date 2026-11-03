"""Minimal class-file constant pool reader, shared by the evidence tools.

Three tools now need to answer "does this jar still reference that member/type, exactly?".
Substring matching on class bytes answers it wrongly: a bridge's own pool mentions the very
member it forwards to (p254 hit that), and the same UTF-8 entry can serve a method name and a
string constant. So the constant pool is parsed and references are counted as (owner, name,
descriptor) or as class names.

No ASM dependency: this is deliberately small and only understands the constant pool.
"""
from __future__ import annotations

import struct


def parse_pool(data: bytes) -> dict[int, tuple[int, object]]:
    count = struct.unpack_from(">H", data, 8)[0]
    pool: dict[int, tuple[int, object]] = {}
    pos = 10
    i = 1
    while i < count:
        tag = data[pos]
        pos += 1
        if tag == 1:  # Utf8
            length = struct.unpack_from(">H", data, pos)[0]
            pos += 2
            pool[i] = (1, data[pos:pos + length].decode("utf-8", errors="replace"))
            pos += length
        elif tag in (7, 8, 16, 19, 20):  # Class, String, MethodType, Module, Package
            pool[i] = (tag, struct.unpack_from(">H", data, pos)[0])
            pos += 2
        elif tag == 15:  # MethodHandle
            pool[i] = (tag, struct.unpack_from(">BH", data, pos))
            pos += 3
        elif tag in (3, 4, 9, 10, 11, 12, 17, 18):
            pool[i] = (tag, struct.unpack_from(">HH", data, pos))
            pos += 4
        elif tag in (5, 6):  # long / double occupy two slots
            pos += 8
            i += 1
        else:
            raise ValueError(f"unknown constant pool tag {tag}")
        i += 1
    return pool


def _member_refs(data: bytes, tags: tuple[int, ...]) -> list[tuple[str, str, str]]:
    pool = parse_pool(data)
    out = []
    for _idx, (tag, payload) in pool.items():
        if tag not in tags:
            continue
        class_idx, nat_idx = payload
        class_entry = pool.get(class_idx)
        nat_entry = pool.get(nat_idx)
        if not class_entry or not nat_entry or nat_entry[0] != 12:
            continue
        owner = pool.get(class_entry[1])
        name = pool.get(nat_entry[1][0])
        desc = pool.get(nat_entry[1][1])
        if owner and name and desc:
            out.append((owner[1], name[1], desc[1]))
    return out


def fieldrefs(data: bytes) -> list[tuple[str, str, str]]:
    """(owner, name, descriptor) for every Fieldref."""
    return _member_refs(data, (9,))


def methodrefs(data: bytes, owner: str | None = None) -> list[tuple[str, str, str]]:
    """(owner, name, descriptor) for every Methodref/InterfaceMethodref, optionally filtered."""
    out = _member_refs(data, (10, 11))
    return [r for r in out if owner is None or r[0] == owner]


def class_names(data: bytes) -> list[str]:
    """Every class named by a CONSTANT_Class entry (types, casts, frames, signatures)."""
    pool = parse_pool(data)
    out = []
    for _idx, (tag, payload) in pool.items():
        if tag != 7:
            continue
        utf8 = pool.get(payload)
        if utf8 and utf8[0] == 1:
            out.append(utf8[1])
    return out


def declarations(data: bytes) -> dict[str, list[tuple[str, str]]]:
    """Members DECLARED by a class: {'fields': [(name, desc)], 'methods': [(name, desc)]}.

    Distinct from fieldrefs/methodrefs, which are *references* to members elsewhere. A checker that
    wants to know "does the target really have this member with this descriptor" has to read the
    declaration tables, not the pool of references.
    """
    count = struct.unpack_from(">H", data, 8)[0]
    pool, pos = _parse_pool_with_pos(data, count)

    def utf8(idx: int) -> str:
        entry = pool.get(idx)
        return entry[1] if entry and entry[0] == 1 else ""

    pos += 6  # access_flags, this_class, super_class
    interfaces = struct.unpack_from(">H", data, pos)[0]
    pos += 2 + 2 * interfaces

    def members(offset: int) -> tuple[list[tuple[str, str]], int]:
        n = struct.unpack_from(">H", data, offset)[0]
        offset += 2
        out = []
        for _ in range(n):
            _access, name_idx, desc_idx, attr_count = struct.unpack_from(">HHHH", data, offset)
            offset += 8
            out.append((utf8(name_idx), utf8(desc_idx)))
            for _a in range(attr_count):
                _name, length = struct.unpack_from(">HI", data, offset)
                offset += 6 + length
        return out, offset

    fields, pos = members(pos)
    methods, pos = members(pos)
    return {"fields": fields, "methods": methods}


def _parse_pool_with_pos(data: bytes, count: int) -> tuple[dict[int, tuple[int, object]], int]:
    """Same walk as parse_pool, but also returns the offset just past the pool."""
    pool: dict[int, tuple[int, object]] = {}
    pos = 10
    i = 1
    while i < count:
        tag = data[pos]
        pos += 1
        if tag == 1:
            length = struct.unpack_from(">H", data, pos)[0]
            pos += 2
            pool[i] = (1, data[pos:pos + length].decode("utf-8", errors="replace"))
            pos += length
        elif tag in (7, 8, 16, 19, 20):
            pool[i] = (tag, struct.unpack_from(">H", data, pos)[0])
            pos += 2
        elif tag == 15:
            pool[i] = (tag, struct.unpack_from(">BH", data, pos))
            pos += 3
        elif tag in (3, 4, 9, 10, 11, 12, 17, 18):
            pool[i] = (tag, struct.unpack_from(">HH", data, pos))
            pos += 4
        elif tag in (5, 6):
            pos += 8
            i += 1
        else:
            raise ValueError(f"unknown constant pool tag {tag}")
        i += 1
    return pool, pos
