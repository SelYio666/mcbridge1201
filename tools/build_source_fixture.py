#!/usr/bin/env python3
"""Build the source-side fixture jar once, from 1.20.1 sources, and pin it by hash.

Why a self-built fixture: every real sample in `work/corpus` is somebody else's artifact, so a
converter change can never be tested against a *known* input shape. This fixture is ours: it
covers the bytecode shapes the conversion rules actually touch, it is compiled once against the
1.20.1 intermediary namespace, and the jar hash is recorded so every target converts the same bytes.

    python tools/build_source_fixture.py
    python tools/build_source_fixture.py --out-json work/tmp/fixture-manifest.json

Exit codes: 0 built and pinned, 1 compile/verification failure, 2 missing toolchain or inputs.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = ROOT / "fixtures" / "source-fabric-1.20.1"
SRC = FIXTURE / "src"
RES = FIXTURE / "resources"
OUT = FIXTURE / "out"
MANIFEST = FIXTURE / "manifest.json"
SCHEMA = "source-fixture-1"

# The fixture is a 1.20.1 source artifact: its own Java level is part of its identity.
SOURCE_JAVA = 17
SOURCE_CLASS_MAJOR = 61

# Compile classpath. Every entry is pinned by hash in the manifest; a missing one is a hard stop,
# because compiling against a different library set would produce a different fixture.
DEPENDENCIES = [
    ("1.20.1 client jar remapped to intermediary (compile stub)",
     "work/cb/data/jars/client-1.20.1-intermediary.jar"),
    ("fabric loader (entrypoint interfaces)",
     "work/target/fabric-loader-0.19.5.jar"),
    ("sponge-mixin (annotations for @Mixin/@Inject)",
     "work/instances/fabric-1.21.1-server/libraries/net/fabricmc/sponge-mixin/0.17.4+mixin.0.8.7/sponge-mixin-0.17.4+mixin.0.8.7.jar"),
    ("gson (referenced by gui/data signatures)",
     "work/lib/gson-2.11.0.jar"),
    ("datafixerupper (Codec in signatures)",
     "work/instances/fabric-1.21.1-server/libraries/com/mojang/datafixerupper/8.0.16/datafixerupper-8.0.16.jar"),
    ("brigadier (command types in gui signatures)",
     "work/instances/fabric-1.21.1-server/libraries/com/mojang/brigadier/1.3.10/brigadier-1.3.10.jar"),
    ("fastutil (collection types in signatures)",
     "work/instances/fabric-1.21.1-server/libraries/it/unimi/dsi/fastutil/8.5.12/fastutil-8.5.12.jar"),
    ("netty buffer (ByteBuf in signatures)",
     "work/instances/fabric-1.21.1-server/libraries/io/netty/netty-buffer/4.1.97.Final/netty-buffer-4.1.97.Final.jar"),
    ("netty common",
     "work/instances/fabric-1.21.1-server/libraries/io/netty/netty-common/4.1.97.Final/netty-common-4.1.97.Final.jar"),
]

COVERS = [
    "registration (Registry.register with an Identifier built from (String, String))",
    "item-nbt (ItemStack NBT read, the 1.20.5 WrapperLookup signature break)",
    "gui-render-hook (Screen.render override, the 1.21.6 extract/draw split)",
    "mixin-inject (@Inject into a real intermediary member with a 4-arg callback)",
    "indy (lambda, method reference, string concat, stream chain)",
    "constructor (new Identifier(ns, path), private from 1.21.1)",
]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def die(message: str) -> None:
    print(message, file=sys.stderr)
    raise SystemExit(2)


def java_home() -> str:
    env = os.environ.get("JAVA_HOME")
    if env and (Path(env) / "bin" / "javac.exe").exists():
        return env
    for cand in (ROOT.parent / ".toolchain" / "jdk", ROOT / ".toolchain" / "jdk"):
        if (cand / "bin" / "javac.exe").exists():
            os.environ["JAVA_HOME"] = str(cand)
            return str(cand)
    die("no JDK found; set JAVA_HOME")


def javac_feature(javac: Path) -> int:
    p = subprocess.run([str(javac), "-version"], capture_output=True, text=True, errors="replace")
    import re
    m = re.search(r"javac\s+(\d+)", (p.stdout or "") + (p.stderr or ""))
    return int(m.group(1)) if m else -1


def class_majors(root: Path) -> dict[int, int]:
    counts: dict[int, int] = {}
    for p in root.rglob("*.class"):
        head = p.read_bytes()[:8]
        if len(head) < 8:
            continue
        major = (head[6] << 8) | head[7]
        counts[major] = counts.get(major, 0) + 1
    return counts


def collect_sources() -> list[Path]:
    sources = sorted(SRC.rglob("*.java"), key=lambda p: p.as_posix())
    if not sources:
        die(f"no fixture sources under {SRC}")
    return sources


def pack(class_dir: Path, jar_path: Path) -> None:
    """Deterministic zip: fixed timestamps, sorted entries, resources first then classes."""
    entries: list[tuple[str, bytes]] = []
    for p in sorted(RES.rglob("*"), key=lambda x: x.as_posix()):
        if p.is_file():
            entries.append((p.relative_to(RES).as_posix(), p.read_bytes()))
    for p in sorted(class_dir.rglob("*.class"), key=lambda x: x.as_posix()):
        entries.append((p.relative_to(class_dir).as_posix(), p.read_bytes()))
    entries.sort(key=lambda e: e[0])
    jar_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(jar_path, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in entries:
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            z.writestr(info, data)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out-json", default=None)
    ap.add_argument("--keep-classes", action="store_true",
                    help="keep the intermediate class directory for inspection")
    args = ap.parse_args()

    home = java_home()
    javac = Path(home) / "bin" / "javac.exe"
    if not javac.is_file():
        javac = Path(home) / "bin" / "javac"
    feature = javac_feature(javac)
    if feature < SOURCE_JAVA:
        die(f"javac {feature} cannot target Java {SOURCE_JAVA}; the fixture is a 1.20.1 artifact")

    deps = []
    classpath = []
    for role, rel in DEPENDENCIES:
        p = ROOT / rel
        if not p.is_file():
            die(f"missing fixture dependency ({role}): {p}\n"
                "the fixture must be compiled against a pinned classpath, not a partial one")
        deps.append({"role": role, "path": rel, "sha256": sha256_file(p), "size": p.stat().st_size})
        classpath.append(str(p))

    sources = collect_sources()
    class_dir = OUT / "classes"
    if class_dir.exists():
        shutil.rmtree(class_dir)
    class_dir.mkdir(parents=True)

    cmd = [str(javac), "-nowarn", "-proc:none", "-encoding", "UTF-8",
           "--release", str(SOURCE_JAVA), "-cp", os.pathsep.join(classpath),
           "-d", str(class_dir)] + [str(s) for s in sources]
    print(" ".join(cmd))
    rc = subprocess.call(cmd)
    if rc != 0:
        print(f"fixture compile failed (rc {rc})", file=sys.stderr)
        return 1

    majors = class_majors(class_dir)
    if set(majors) != {SOURCE_CLASS_MAJOR}:
        print(f"fixture classes are not all at class major {SOURCE_CLASS_MAJOR}: {majors}",
              file=sys.stderr)
        return 1

    version = json.loads((RES / "fabric.mod.json").read_text(encoding="utf-8"))["version"]
    jar_path = OUT / f"mcbfixture-{version}.jar"
    pack(class_dir, jar_path)
    if not args.keep_classes:
        shutil.rmtree(class_dir)

    with zipfile.ZipFile(jar_path) as z:
        jar_entries = sorted(z.namelist())
    for required in ("fabric.mod.json", "mcbfixture.mixins.json",
                     "mcbfixture/FixtureMod.class", "mcbfixture/mixin/FixtureMixin.class"):
        if required not in jar_entries:
            print(f"packed jar is missing {required}", file=sys.stderr)
            return 1

    manifest = {
        "schemaVersion": SCHEMA,
        "fixtureId": "source-fabric-1.20.1",
        "source": {
            "minecraft": "1.20.1",
            "loader": "fabric",
            "javaMajor": SOURCE_JAVA,
            "classMajorMax": SOURCE_CLASS_MAJOR,
            "namespace": "intermediary",
        },
        "input": {
            "jar": jar_path.relative_to(ROOT).as_posix(),
            "sha256": sha256_file(jar_path),
            "size": jar_path.stat().st_size,
        },
        "classes": {
            "count": sum(majors.values()),
            "majors": {str(k): v for k, v in sorted(majors.items())},
            "sources": [p.relative_to(ROOT).as_posix() for p in sources],
        },
        "covers": COVERS,
        "dependencies": deps,
        "builtWith": {"javac": f"{feature}", "release": SOURCE_JAVA},
        "verification": {
            "compiled": True,
            "classMajorChecked": True,
            "jarPacked": True,
            "scanned": False,
            "ranInSource": False,
            "note": "Compiled and hashed only. It has NOT been run in a 1.20.1 game: that needs a"
                    " 1.20.1 Fabric server/client instance this machine does not have, so the"
                    " source-side runtime baseline is pending, not passed.",
        },
        "policy": "Compiled once. Targets convert exactly these bytes; do not recompile per target"
                  " and do not feed a converted jar back as a source.",
    }
    text = json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    MANIFEST.write_text(text, encoding="utf-8", newline="\n")
    if args.out_json:
        Path(args.out_json).write_text(text, encoding="utf-8", newline="\n")
    print(f"fixture {jar_path.relative_to(ROOT).as_posix()} "
          f"{manifest['input']['size']} bytes sha256 {manifest['input']['sha256'][:16]}")
    print(f"{sum(majors.values())} class(es) at major {SOURCE_CLASS_MAJOR}; manifest -> "
          f"{MANIFEST.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
