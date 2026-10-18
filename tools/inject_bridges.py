"""Replace generated bridge classes in a patched jar with javac-compiled versions.

Usage:
  python tools/inject_bridges.py --jar in.jar --out out.jar --classes work/bridges \
      --replace top/mcbridge1201/bridge/ItemPredicateFromJson \
                top/mcbridge1201/bridge/ItemPredicateAny
"""
import argparse
import os
import zipfile


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jar", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--classes", required=True)
    ap.add_argument("--replace", action="append", required=True)
    args = ap.parse_args()

    with zipfile.ZipFile(args.jar) as zin:
        entries = {n: zin.read(n) for n in zin.namelist() if not n.endswith("/")}
    replaced = []
    for internal in args.replace:
        src = os.path.join(args.classes, *internal.split("/")) + ".class"
        if not os.path.exists(src):
            print("missing compiled class:", src, flush=True)
            return 2
        entries[internal + ".class"] = open(src, "rb").read()
        replaced.append(internal)
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with zipfile.ZipFile(args.out, "w", zipfile.ZIP_DEFLATED) as zout:
        for name, data in entries.items():
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            zout.writestr(info, data)
    print("replaced", len(replaced), "bridge classes ->", args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
