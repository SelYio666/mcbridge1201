"""Find the `Dimension` tag inside level.dat's `Data.Player` compound and report its NBT type."""
import gzip
import json
import sys
from pathlib import Path

TAG_NAMES = {0: "End", 1: "Byte", 2: "Short", 3: "Int", 4: "Long", 5: "Float", 6: "Double",
             7: "ByteArray", 8: "String", 9: "List", 10: "Compound", 11: "IntArray", 12: "LongArray"}


class R:
    def __init__(self, data: bytes):
        self.b = data
        self.i = 0

    def u(self, n):
        v = int.from_bytes(self.b[self.i:self.i + n], "big", signed=False)
        self.i += n
        return v

    def s(self, n):
        v = int.from_bytes(self.b[self.i:self.i + n], "big", signed=True)
        self.i += n
        return v

    def str(self):
        n = self.u(2)
        v = self.b[self.i:self.i + n].decode("utf-8", "replace")
        self.i += n
        return v

    def payload(self, t):
        if t == 1:
            return self.s(1)
        if t == 2:
            return self.s(2)
        if t == 3:
            return self.s(4)
        if t == 4:
            return self.s(8)
        if t == 5:
            import struct
            v = struct.unpack(">f", self.b[self.i:self.i + 4])[0]
            self.i += 4
            return v
        if t == 6:
            import struct
            v = struct.unpack(">d", self.b[self.i:self.i + 8])[0]
            self.i += 8
            return v
        if t == 7:
            n = self.u(4)
            self.i += n
            return f"<{n} bytes>"
        if t == 8:
            return self.str()
        if t == 9:
            et = self.u(1)
            n = self.u(4)
            return [self.payload(et) for _ in range(n)]
        if t == 10:
            out = {}
            while True:
                tt = self.u(1)
                if tt == 0:
                    break
                name = self.str()
                out[name] = (tt, self.payload(tt))
            return out
        if t == 11:
            n = self.u(4)
            vals = [self.s(4) for _ in range(n)]
            return vals
        if t == 12:
            n = self.u(4)
            vals = [self.s(8) for _ in range(n)]
            return vals
        raise ValueError(t)


def main(path):
    raw = gzip.decompress(Path(path).read_bytes())
    r = R(raw)
    t = r.u(1)
    name = r.str()
    root = r.payload(t)
    data = root["Data"][1]
    player = data.get("Player")
    out = {"file": path, "root": name, "has_player": bool(player)}
    if player:
        pt, pv = player
        out["player_type"] = TAG_NAMES.get(pt)
        out["player_keys"] = sorted(pv.keys())
        dim = pv.get("Dimension")
        if dim:
            out["dimension_type"] = TAG_NAMES.get(dim[0])
            out["dimension_value"] = dim[1] if not isinstance(dim[1], (dict, list)) else "<complex>"
        else:
            out["dimension_type"] = None
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main(sys.argv[1])
