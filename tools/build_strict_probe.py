#!/usr/bin/env python3
"""Build the strict bridge probe jar (client-side runtime check for ISSUE-01)."""
import pathlib
import shutil
import subprocess
import sys
import zipfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
PROBE = ROOT / "probes" / "strictprobe"
JAVA_HOME = pathlib.Path(__import__("os").environ.get("JAVA_HOME", ""))
if not JAVA_HOME.exists():
    sys.exit("JAVA_HOME is required")

stub = ROOT / "work/cb/data/jars/client-1.21.1-intermediary.jar"
loader = ROOT / "work/target/fabric-loader-0.19.5.jar"
mods = ROOT / "work/instances/fabric-1.21.1-server/.fabric/processedMods"
libs = [
    ROOT / "work/bridges",
    mods / "fabric-lifecycle-events-v1-2.3.1+6c1df3606a-9f74236580e9e222.jar",
    mods / "fabric-api-base-0.4.42+6573ed8c6a-ec0e6648f37ee3.jar",
    ROOT / "work/instances/fabric-1.21.1-server/libraries/io/netty/netty-buffer/4.1.97.Final/netty-buffer-4.1.97.Final.jar",
    ROOT / "work/instances/fabric-1.21.1-server/libraries/com/mojang/datafixerupper/8.0.16/datafixerupper-8.0.16.jar",
]
classes = ROOT / "work/tmp/strictprobe/classes"
shutil.rmtree(classes, ignore_errors=True)
classes.mkdir(parents=True)

cp = ";".join(str(p) for p in [stub, loader, *libs])
cmd = [str(JAVA_HOME / "bin/javac.exe"), "-nowarn", "-proc:none", "-encoding", "UTF-8",
       "-cp", cp, "-d", str(classes), str(PROBE / "src/probe/StrictProbe.java")]
rc = subprocess.call(cmd)
if rc != 0:
    sys.exit(rc)

bridge = ROOT / "work/bridges/top/mcbridge1201/bridge/TrashSlotNbtBridge.class"
dest = classes / "top/mcbridge1201/bridge/TrashSlotNbtBridge.class"
dest.parent.mkdir(parents=True, exist_ok=True)
shutil.copy2(bridge, dest)
shutil.copy2(PROBE / "fabric.mod.json", classes / "fabric.mod.json")

out = ROOT / "work/tmp/strictprobe/strictprobe.jar"
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
    for p in classes.rglob("*"):
        if p.is_file():
            z.write(p, p.relative_to(classes).as_posix())
print("built", out, out.stat().st_size)
