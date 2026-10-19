import json
import os
import pathlib
import subprocess
import sys

MC = pathlib.Path(r"D:\我的世界\.minecraft")
VERSION = MC / "versions" / "fabric-loader-0.19.5-1.21.1"
BASE = MC / "versions" / "1.21.1"
JAVA = pathlib.Path(r"C:\Users\27682\AppData\Local\Packages\Microsoft.4297127D64EC6_8wekyb3d8bbwe\LocalCache\Local\runtime\java-runtime-delta\windows-x64\java-runtime-delta\bin\java.exe")
OUT = pathlib.Path(r"C:\Users\27682\Documents\新建文件夹\mcbridge1201\runs\p50-client")

base = json.loads((BASE / "1.21.1.json").read_text(encoding="utf-8"))
fabric = json.loads((VERSION / "fabric-loader-0.19.5-1.21.1.json").read_text(encoding="utf-8"))


def artifact_path(lib):
    art = lib.get("downloads", {}).get("artifact")
    return art["path"] if art else None


def allowed(lib):
    rules = lib.get("rules")
    if not rules:
        return True
    allowed_flag = False
    for rule in rules:
        os_name = rule.get("os", {}).get("name")
        if rule["action"] == "allow" and (os_name is None or os_name == "windows"):
            allowed_flag = True
        if rule["action"] == "disallow" and os_name == "windows":
            allowed_flag = False
    return allowed_flag


cp = []
for lib in base["libraries"]:
    if not allowed(lib):
        continue
    path = artifact_path(lib)
    if not path:
        continue
    if "natives-" in path and ("natives-windows" not in path or "arm64" in path or "natives-windows-x86" in path):
        continue
    cp.append(str(MC / "libraries" / path))

for lib in fabric["libraries"]:
    name = lib["name"]
    parts = name.split(":")
    group, artifact, version = parts[0], parts[1], parts[2]
    classifier = parts[3] if len(parts) > 3 else None
    path = MC / "libraries" / group.replace(".", "/") / artifact / version / (
        f"{artifact}-{version}" + (f"-{classifier}" if classifier else "") + ".jar")
    if not path.exists():
        print("missing fabric lib", path, file=sys.stderr)
        sys.exit(2)
    cp.append(str(path))

cp.append(str(BASE / "1.21.1.jar"))

USERNAME = os.environ.get("MC_USERNAME", "TestPlayer")
GAME_DIR = os.environ.get("MC_GAME_DIR", str(VERSION))
LOG_DIR = pathlib.Path(os.environ.get("MC_LOG_DIR", str(OUT)))
CWD = pathlib.Path(os.environ.get("MC_CWD", str(VERSION)))

args = [
    str(JAVA), "-Xmx2048M", "-Xms512M",
    "-Djava.library.path=" + str(VERSION / "natives"),
    "-Dfabric.development=false",
    "-Dfile.encoding=UTF-8",
    "-cp", ";".join(cp),
    fabric["mainClass"],
    "--username", USERNAME,
    "--version", "fabric-loader-0.19.5-1.21.1",
    "--gameDir", GAME_DIR,
    "--assetsDir", str(MC / "assets"),
    "--assetIndex", "17",
    "--uuid", "00000000000000000000000000000001",
    "--accessToken", "0",
    "--clientId", "0",
    "--xuid", "0",
    "--versionType", "release",
    "--width", "1024", "--height", "768",
]
if os.environ.get("QUICK_PLAY_MP"):
    args += ["--quickPlayMultiplayer", os.environ["QUICK_PLAY_MP"]]
if os.environ.get("QUICK_PLAY"):
    args += ["--quickPlaySingleplayer", os.environ["QUICK_PLAY"]]
LOG_DIR.mkdir(parents=True, exist_ok=True)
log = open(LOG_DIR / "client.log", "wb")
proc = subprocess.Popen(args, cwd=str(CWD), stdout=log, stderr=subprocess.STDOUT)
print(proc.pid)
