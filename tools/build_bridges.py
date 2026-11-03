"""Compile the Java-source bridges against the intermediary stub.

Two modes, on purpose:

    # legacy: everything is spelled out on the command line, behaviour unchanged
    python tools/build_bridges.py --stub work/cb/data/jars/client-1.21.1-intermediary.jar \
        --lib work/lib/gson-2.11.0.jar --out work/bridges

    # target mode (A03): stub, libs, output dir and --release come from the profile
    python tools/build_bridges.py --profile targets/fabric-1.21.1.json

Target mode refuses rather than guesses. It fails when the profile's bridge ABI is not the one
this build embeds, when the target Java release is above what the local javac can emit, when the
stub is missing or its bytes differ from the frozen hash, and when the produced classes do not
carry exactly the target's class major. A bridge compiled at the wrong level is not a warning:
the target runtime rejects the class after the artifact shipped.

The generated classes are embedded by `mcbridge1201 patch --bridge-dir <out>`.
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BRIDGE_ABI = "mcbridge-bridge-1"
SUPPORTED_PROFILE_SCHEMA = "target-profile-1"


def die(message):
    """Refuse with exit code 2: the caller asked for something this build must not do."""
    print(message, file=sys.stderr)
    raise SystemExit(2)


# --------------------------------------------------------------------------- helpers

def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def class_major_from_bytes(head):
    if len(head) < 8:
        return -1
    return ((head[6] & 0xFF) << 8) | (head[7] & 0xFF)


def class_major(path):
    with open(path, "rb") as f:
        return class_major_from_bytes(f.read(8))


def class_major_for(java_major):
    """Class file major for a Java feature release (17 -> 61, 21 -> 65, 25 -> 69)."""
    return java_major + 44


def jar_max_class_major(jar):
    """Highest class major inside a jar (top level only; nested jars are not the javac classpath)."""
    worst = -1
    with zipfile.ZipFile(jar) as zf:
        for name in zf.namelist():
            if not name.endswith(".class"):
                continue
            major = class_major_from_bytes(zf.read(name)[:8])
            if major > worst:
                worst = major
    return worst


def javac_feature_version(javac):
    out = subprocess.run([javac, "-version"], capture_output=True, text=True, errors="replace")
    text = (out.stdout or "") + (out.stderr or "")
    m = re.search(r"javac\s+(\d+)", text)
    if not m:
        return -1
    return int(m.group(1))


def java_sources(root):
    out = []
    for dirpath, _dirs, files in os.walk(root):
        for f in sorted(files):
            if f.endswith(".java"):
                out.append(os.path.join(dirpath, f))
    return out


def verify_majors(out_dir, expected, label):
    """Every produced class must carry exactly the target class major."""
    bad = []
    total = 0
    for dirpath, _dirs, files in os.walk(out_dir):
        for f in files:
            if not f.endswith(".class"):
                continue
            total += 1
            full = os.path.join(dirpath, f)
            major = class_major(full)
            if major != expected:
                bad.append((os.path.relpath(full, out_dir).replace(os.sep, "/"), major))
    if bad:
        print(f"FAIL {label}: {len(bad)}/{total} class(es) are not at major {expected}:", file=sys.stderr)
        for rel, major in bad[:10]:
            print(f"  {rel}: major {major}", file=sys.stderr)
        return False
    print(f"{label}: {total} class(es) at major {expected}")
    return True


# --------------------------------------------------------------------------- profile mode

def from_profile(profile_path):
    """Turn a target profile into compile settings, or exit with the reason it can't be used."""
    profile_path = os.path.abspath(profile_path)
    with open(profile_path, encoding="utf-8") as f:
        p = json.load(f)
    schema = p.get("schemaVersion")
    if schema != SUPPORTED_PROFILE_SCHEMA:
        die(f"profile {profile_path}: unsupported schemaVersion {schema!r}")
    pipeline = p.get("pipeline") or {}
    abi = pipeline.get("bridgeAbi")
    if abi != BRIDGE_ABI:
        die(f"profile {profile_path}: bridge ABI {abi!r} but this build embeds {BRIDGE_ABI!r};"
                 " the bridge sources must be re-validated against the new ABI")
    target = p.get("target") or {}
    indices = p.get("indices") or {}
    stub = indices.get("bridgeStub")
    if not stub or not stub.get("path"):
        die(f"profile {profile_path}: indices.bridgeStub is missing; a bridge has to be"
                 " compiled against a named target stub, not whatever jar is lying around")
    stub_path = stub["path"] if os.path.isabs(stub["path"]) else os.path.join(ROOT, stub["path"])

    java_major = target.get("javaMajor")
    class_major_max = target.get("classMajorMax")
    if not java_major or not class_major_max:
        die(f"profile {profile_path}: target.javaMajor and target.classMajorMax are required")
    derived = class_major_for(int(java_major))
    if derived != int(class_major_max):
        die(f"profile {profile_path}: classMajorMax {class_major_max} does not match Java"
                 f" {java_major} (expected {derived})")

    output = pipeline.get("output") or {}
    out = output.get("bridgeClasses")
    if not out:
        die(f"profile {profile_path}: pipeline.output.bridgeClasses is missing; a target must"
                 " own its output directory, otherwise two targets overwrite each other")
    out = out if os.path.isabs(out) else os.path.join(ROOT, out)

    libs = []
    for entry in indices.get("libs") or []:
        path = entry.get("path")
        if not path:
            continue
        libs.append(path if os.path.isabs(path) else os.path.join(ROOT, path))
    closure = indices.get("libClosure")
    if closure and closure.get("path"):
        closure_path = closure["path"] if os.path.isabs(closure["path"]) else os.path.join(ROOT, closure["path"])
        if not os.path.isfile(closure_path):
            die(f"library closure missing: {closure_path}")
        actual = sha256(closure_path)
        if closure.get("sha256") and actual != closure["sha256"]:
            die(f"library closure {os.path.basename(closure_path)} has sha256 {actual[:12]} but the"
                f" profile froze {closure['sha256'][:12]}")
        with open(closure_path, encoding="utf-8") as f:
            lock = json.load(f)
        for rel in lock.get("classpath") or []:
            libs.append(rel if os.path.isabs(rel) else os.path.join(ROOT, rel))
        print(f"classpath closure: {len(lock.get('classpath') or [])} jar(s) from"
              f" {os.path.basename(closure_path)}")

    sources = pipeline.get("bridgeSources") or []
    return {
        "bridge_sources": sources,
        "profile_path": profile_path,
        "profile_id": p.get("profileId"),
        "target_id": target.get("id"),
        "java_major": int(java_major),
        "class_major_max": int(class_major_max),
        "stub": stub_path,
        "stub_sha256": stub.get("sha256"),
        "libs": libs,
        "out": out,
        "shim_out": os.path.join(os.path.dirname(out), "bridges-shim"),
    }


def check_target_reachable(cfg, javac, feature):
    """Refuse targets this JDK cannot emit; refuse stubs the target runtime could not read."""
    if cfg["java_major"] > feature:
        die(f"target {cfg['target_id']} needs Java {cfg['java_major']} but javac is {feature}:"
                 " this target is not reachable from this toolchain (a JDK upgrade is the fix,"
                 " not a flag)")
    if not os.path.isfile(cfg["stub"]):
        die(f"bridge stub missing: {cfg['stub']}")
    actual = sha256(cfg["stub"])
    if not cfg["stub_sha256"] or actual != cfg["stub_sha256"]:
        die(f"bridge stub {os.path.basename(cfg['stub'])} has sha256 {actual[:12]} but the"
                 f" profile froze {(cfg['stub_sha256'] or 'nothing')[:12]}; rebuild or update the"
                 " profile, do not compile bridges against an unpinned stub")
    stub_major = jar_max_class_major(cfg["stub"])
    if stub_major > cfg["class_major_max"]:
        die(f"bridge stub carries class major {stub_major}, above the target's"
                 f" {cfg['class_major_max']}: `javac --release {cfg['java_major']}` refuses to read"
                 " a newer classpath class, so remap the stub for this target first")
    print(f"target {cfg['target_id']}: java {cfg['java_major']} (major {cfg['class_major_max']}),"
          f" stub {os.path.basename(cfg['stub'])} @{stub_major}, out {os.path.relpath(cfg['out'], ROOT)}")


# --------------------------------------------------------------------------- legacy mode

def legacy(args):
    return {
        "java_major": args.release,
        "class_major_max": class_major_for(args.release) if args.release else None,
        "stub": os.path.abspath(args.stub),
        "stub_sha256": None,
        "libs": [os.path.abspath(x) for x in args.lib],
        "out": os.path.abspath(args.out or os.path.join(ROOT, "work", "bridges")),
        "shim_out": os.path.join(ROOT, "work", "tmp", "bridges-shim"),
        "service_strict": False,
    }


# --------------------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--profile", default=None,
                    help="target profile JSON; supplies stub, libs, output dir and --release")
    ap.add_argument("--stub", default=None, help="intermediary stub jar (legacy mode)")
    ap.add_argument("--out", default=None,
                    help="output dir; legacy default work/bridges, target mode default comes from"
                         " pipeline.output.bridgeClasses (an explicit --out overrides both)")
    ap.add_argument("--lib", action="append", default=[])
    ap.add_argument("--release", type=int, default=None,
                    help="javac --release (legacy mode); target mode takes it from the profile")
    args = ap.parse_args()

    if args.profile and args.stub:
        die("--profile and --stub are mutually exclusive: a target stub comes from the profile,"
                 " so passing another one would silently compile against the wrong classes")
    if not args.profile and not args.stub:
        die("either --profile or --stub is required")

    java_home = os.environ.get("JAVA_HOME")
    if not java_home:
        print("JAVA_HOME is required", file=sys.stderr)
        return 2
    javac = os.path.join(java_home, "bin", "javac.exe" if os.name == "nt" else "javac")
    feature = javac_feature_version(javac)
    if feature <= 0:
        print(f"cannot determine javac version at {javac}", file=sys.stderr)
        return 2

    if args.profile:
        cfg = from_profile(args.profile)
        if args.lib:
            cfg["libs"] = cfg["libs"] + [os.path.abspath(x) for x in args.lib]
        if args.out:
            cfg["out"] = os.path.abspath(args.out)
            cfg["shim_out"] = os.path.join(os.path.dirname(cfg["out"]), "bridges-shim")
            print(f"note: output overridden to {os.path.relpath(cfg['out'], ROOT)} by --out; the"
                  f" profile's own directory is {os.path.relpath(from_profile(args.profile)['out'], ROOT)}")
        check_target_reachable(cfg, javac, feature)
        release = cfg["java_major"]
        expected_major = cfg["class_major_max"]
    else:
        cfg = legacy(args)
        release = args.release
        expected_major = class_major_for(release) if release else None
        if not os.path.isfile(cfg["stub"]):
            print(f"stub missing: {cfg['stub']}", file=sys.stderr)
            return 2

    src_roots = [os.path.join(ROOT, rel) for rel in (cfg.get("bridge_sources") or [])]
    if not src_roots:
        src_roots = [os.path.join(ROOT, "java", "src", "bridge", "java")]
    sources = []
    for root in src_roots:
        sources.extend(java_sources(root))
    if not sources:
        print("no bridge sources under", ", ".join(src_roots), file=sys.stderr)
        return 2
    print("bridge sources:", ", ".join(os.path.relpath(r, ROOT) for r in src_roots),
          "->", len(sources), "file(s)")
    os.makedirs(cfg["out"], exist_ok=True)
    cp = os.pathsep.join([os.path.abspath(cfg["stub"])] + [os.path.abspath(x) for x in cfg["libs"]])
    common = ["-nowarn", "-proc:none", "-encoding", "UTF-8"]
    if release:
        common += ["--release", str(release)]
    cmd = [javac] + common + ["-cp", cp, "-d", cfg["out"]] + sources
    print(" ".join(cmd))
    rc = subprocess.call(cmd)
    if rc != 0:
        return rc
    print("compiled", len(sources), "bridge source(s) ->", cfg["out"])

    shim_root = os.path.join(ROOT, "java", "src", "bridge-shim", "java")
    shim_sources = java_sources(shim_root)
    if shim_sources:
        shim_out = cfg["shim_out"]
        os.makedirs(shim_out, exist_ok=True)
        shim_cmd = [javac] + common + ["-cp", cp, "-d", shim_out] + shim_sources
        rc = subprocess.call(shim_cmd)
        if rc != 0:
            return rc
        shims = [
            ("net", "fabricmc", "fabric", "api", "client", "networking", "v1",
             "ClientPlayNetworking$PlayChannelHandler.class"),
            ("net", "fabricmc", "fabric", "api", "networking", "v1",
             "ServerPlayNetworking$PlayChannelHandler.class"),
        ]
        for parts in shims:
            nested = os.path.join(shim_out, *parts)
            if not os.path.exists(nested):
                print("shim did not produce", nested, file=sys.stderr)
                return 3
            dest_dir = os.path.join(cfg["out"], *parts[:-1])
            os.makedirs(dest_dir, exist_ok=True)
            dest = os.path.join(dest_dir, parts[-1])
            with open(nested, "rb") as src, open(dest, "wb") as dst:
                dst.write(src.read())
            print("embedded legacy shim ->", dest)

    if expected_major is not None:
        if not verify_majors(cfg["out"], expected_major, "bridge class major"):
            return 4
    else:
        print("note: no --release given, so the class major is whatever the toolchain emits"
              " (legacy mode; pass --profile to make it a checked property)")

    if args.profile:
        # The output directory is part of the target identity: print it so a report can record
        # which target's bridges were actually compiled.
        print(f"target output: {os.path.relpath(cfg['out'], ROOT)} (profile {cfg['profile_id']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
