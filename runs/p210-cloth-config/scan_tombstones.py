"""List every reference to the generated tombstone stubs inside the nested Cloth Config jar (p210).

The scan answers one question before any patch is written: which tombstone is on the render path
that the config screen must walk every frame, and which ones sit on paths the screen never takes.
A stub only counts as "on the render path" when the method that calls it is itself reachable from
`ClothConfigScreen.method_25394`.

Read-only: it parses class files, it does not patch anything.

Usage:
  python runs/p210-cloth-config/scan_tombstones.py [path/to/cloth.jar]
"""
import io
import json
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_JAR = ROOT / "work" / "tmp" / "p210" / "cloth-in.jar"
TOMBSTONE_PREFIX = "centurybridge/gen/"


def u1(b, i):
    return b[i], i + 1


def u2(b, i):
    return int.from_bytes(b[i:i + 2], "big"), i + 2


def u4(b, i):
    return int.from_bytes(b[i:i + 4], "big"), i + 4


class ClassFile:
    """Minimal class reader: enough of the constant pool to resolve call targets."""

    def __init__(self, data):
        self.data = data
        self.pool = []
        self._read_pool()
        self.name, self.super_name = self._read_header()

    def _read_pool(self):
        b = self.data
        i = 8
        count, i = u2(b, i)
        self.pool = [None] * count
        n = 1
        while n < count:
            tag = b[i]
            i += 1
            if tag == 1:
                ln, i = u2(b, i)
                self.pool[n] = ("utf8", b[i:i + ln].decode("utf-8", "replace"))
                i += ln
            elif tag in (7, 8, 16, 19, 20):
                v, i = u2(b, i)
                self.pool[n] = ("ref", v)
            elif tag in (15,):
                v, i = u1(b, i)
                i += 2
                self.pool[n] = ("mh", v)
            elif tag in (3, 4, 9, 10, 11, 12, 17, 18):
                i += 4
                self.pool[n] = ("num", None)
            elif tag in (5, 6):
                i += 8
                self.pool[n] = ("long", None)
                n += 1
            else:
                raise ValueError("unknown constant pool tag %d" % tag)
            n += 1

    def utf(self, idx):
        e = self.pool[idx]
        if e and e[0] == "utf8":
            return e[1]
        return None

    def class_name(self, idx):
        e = self.pool[idx]
        if e and e[0] == "ref":
            return self.utf(e[1])
        return None

    def _read_header(self):
        b = self.data
        i = 8
        _, i = u2(b, i)                     # constant_pool_count
        # Re-walk the pool to find where it ends.
        n = 1
        while n < len(self.pool):
            e = self.pool[n]
            if e is None:
                n += 1
                continue
            tag = e[0]
            if tag == "utf8":
                i += 2 + len(e[1].encode("utf-8"))
            elif tag == "ref":
                i += 2
            elif tag == "mh":
                i += 3
            elif tag in ("num",):
                i += 4
            elif tag == "long":
                i += 8
                n += 1
            n += 1
        i += 2                              # access_flags
        this_idx, i = u2(b, i)
        super_idx, i = u2(b, i)
        return self.class_name(this_idx), self.class_name(super_idx)

    def methods(self):
        """Yield (name, desc, [called owner/name/desc]) for every method with code."""
        b = self.data
        i = 8
        cnt, i = u2(b, i)
        n = 1
        while n < cnt:
            tag = b[i]
            i += 1
            if tag == 1:
                ln, i = u2(b, i)
                i += ln
            elif tag in (7, 8, 16, 19, 20):
                i += 2
            elif tag == 15:
                i += 3
            elif tag in (3, 4, 9, 10, 11, 12, 17, 18):
                i += 4
            elif tag in (5, 6):
                i += 8
                n += 1
            else:
                raise ValueError("bad tag")
            n += 1
        i += 6                              # access, this, super
        ic, i = u2(b, i)
        i += 2 * ic
        fc, i = u2(b, i)
        for _ in range(fc):
            i += 6
            ac, i = u2(b, i)
            for _ in range(ac):
                _, i = u2(b, i)
                ln, i = u4(b, i)
                i += ln
        mc, i = u2(b, i)
        out = []
        for _ in range(mc):
            access, i = u2(b, i)
            ni, i = u2(b, i)
            di, i = u2(b, i)
            ac, i = u2(b, i)
            code = None
            for _ in range(ac):
                ani, i = u2(b, i)
                alen, i = u4(b, i)
                if self.utf(ani) == "Code":
                    code = b[i:i + alen]
                i += alen
            calls = self._scan_code(code) if code else []
            out.append((self.utf(ni), self.utf(di), calls))
        return out

    def _scan_code(self, code):
        """Walk the instruction stream and collect constant-pool refs to methods."""
        calls = []
        i = 8                               # max_stack, max_locals, code_length
        end = 8 + int.from_bytes(code[4:8], "big")
        while i < end:
            op = code[i]
            if op in (0xb6, 0xb7, 0xb8, 0xb9, 0xba):     # invokevirtual/special/static/interface/dynamic
                idx = int.from_bytes(code[i + 1:i + 3], "big")
                tgt = self._methodref(idx)
                if tgt:
                    calls.append(tgt)
                i += 5 if op == 0xb9 else (5 if op == 0xba else 3)
            elif op in (0xb2, 0xb3, 0xb4, 0xb5):         # field ops
                idx = int.from_bytes(code[i + 1:i + 3], "big")
                tgt = self._fieldref(idx)
                if tgt:
                    calls.append(tgt)
                i += 3
            elif op in (0xbb, 0xbd, 0xc0, 0xc1):         # new/anewarray/checkcast/instanceof
                idx = int.from_bytes(code[i + 1:i + 3], "big")
                cn = self.class_name(idx)
                if cn:
                    calls.append(("type", cn, ""))
                i += 3
            elif op in (0x12,):                          # ldc
                i += 2
            elif op in (0x13, 0x14):                     # ldc_w, ldc2_w
                i += 3
            elif op in (0x15, 0x16, 0x17, 0x18, 0x19, 0x36, 0x37, 0x38, 0x39, 0x3a, 0xa9):
                i += 2
            elif op == 0x84:                             # iinc
                i += 3
            elif op in (0x99, 0x9a, 0x9b, 0x9c, 0x9d, 0x9e, 0x9f, 0xa0, 0xa1, 0xa2,
                        0xa3, 0xa4, 0xa5, 0xa6, 0xa7, 0xa8):
                i += 3
            elif op in (0xc6, 0xc7):
                i += 3
            elif op == 0xc8:
                i += 5
            elif op == 0xc9:
                i += 5
            elif op in (0xaa, 0xab):                     # tableswitch / lookupswitch
                pad = (4 - ((i + 1) % 4)) % 4
                base = i + 1 + pad
                if op == 0xaa:
                    low = int.from_bytes(code[base + 4:base + 8], "big", signed=True)
                    high = int.from_bytes(code[base + 8:base + 12], "big", signed=True)
                    i = base + 12 + 4 * (high - low + 1)
                else:
                    n = int.from_bytes(code[base + 4:base + 8], "big", signed=True)
                    i = base + 8 + 8 * n
            else:
                i += 1
        return calls

    def _methodref(self, idx):
        e = self.pool[idx] if idx < len(self.pool) else None
        if not e or e[0] != "num":
            return None
        # Re-read the raw entry: tag 10/11 -> class_index, name_and_type_index
        raw = self._raw_pool_entry(idx)
        if not raw:
            return None
        tag, ci, nti = raw
        if tag not in (10, 11):
            return None
        owner = self.class_name(ci)
        nt = self.pool[nti]
        if not nt or nt[0] != "num":
            return None
        _, ni, di = self._raw_nt(nti)
        return ("method", owner, self.utf(ni), self.utf(di))

    def _fieldref(self, idx):
        raw = self._raw_pool_entry(idx, allow=(9,))
        if not raw:
            return None
        _, ci, nti = raw
        owner = self.class_name(ci)
        _, ni, di = self._raw_nt(nti)
        return ("field", owner, self.utf(ni), self.utf(di))

    def _raw_nt(self, idx):
        return self._raw_pool_entry(idx, allow=(12,))

    def _raw_pool_entry(self, idx, allow=None):
        """Locate and decode the raw bytes of one pool entry (tag known in advance)."""
        b = self.data
        if not hasattr(self, "_offsets"):
            self._offsets = {}
            i = 10
            n = 1
            count = int.from_bytes(b[8:10], "big")
            while n < count:
                start = i
                tag = b[i]
                i += 1
                if tag == 1:
                    ln = int.from_bytes(b[i:i + 2], "big")
                    i += 2 + ln
                elif tag in (7, 8, 16, 19, 20):
                    i += 2
                elif tag == 15:
                    i += 3
                elif tag in (3, 4, 9, 10, 11, 12, 17, 18):
                    i += 4
                elif tag in (5, 6):
                    i += 8
                    n += 1
                self._offsets[n] = start
                n += 1
        off = self._offsets.get(idx)
        if off is None:
            return None
        tag = b[off]
        if allow and tag not in allow:
            return None
        a = int.from_bytes(b[off + 1:off + 3], "big")
        bb = int.from_bytes(b[off + 3:off + 5], "big")
        return tag, a, bb


def main():
    jar = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_JAR
    if not jar.is_file():
        raise SystemExit("missing jar: %s (run build.py first to extract the nested cloth jar)" % jar)
    hits = {}
    total = 0
    with zipfile.ZipFile(jar) as z:
        for info in z.infolist():
            if not info.filename.endswith(".class"):
                continue
            data = z.read(info)
            try:
                cf = ClassFile(data)
            except Exception as exc:                         # noqa: BLE001 - report, don't guess
                print("SKIP %s: %s" % (info.filename, exc), file=sys.stderr)
                continue
            for mname, mdesc, calls in cf.methods():
                marks = sorted({c[2] for c in calls
                                if c[0] in ("method", "field", "type")
                                and (c[1] or "").startswith(TOMBSTONE_PREFIX)})
                if marks:
                    total += len(marks)
                    hits.setdefault(cf.name.replace("/", "."), []).append(
                        {"method": mname, "desc": mdesc, "tombstones": marks})
    print(json.dumps({"jar": str(jar), "refs": total, "sites": hits},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
