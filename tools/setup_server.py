"""Create an isolated Fabric 1.21.1 dedicated-server instance (P0 boot baseline).

No launcher account is needed for a dedicated server; the network is used only to
download the Fabric server launcher and (on first boot) the vanilla server jar from
Mojang. Everything lands under work/instances/ and is never committed.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil

from fetchlib import download, http_json, now_iso, write_json

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORK = os.path.join(ROOT, "work")
MANIFESTS = os.path.join(ROOT, "manifests")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--instance", default=os.path.join(WORK, "instances", "fabric-1.21.1-server"))
    ap.add_argument("--loader", default=None, help="override Fabric loader version")
    args = ap.parse_args()
    INST = os.path.abspath(args.instance)
    os.makedirs(INST, exist_ok=True)
    os.makedirs(os.path.join(INST, "mods"), exist_ok=True)
    lock = json.load(open(os.path.join(MANIFESTS, "environment.lock.json"), encoding="utf-8"))
    loader = args.loader or lock["fabric"]["loader"]["version"]
    installer = http_json("https://meta.fabricmc.net/v2/versions/installer")[0]["version"]
    url = f"https://meta.fabricmc.net/v2/versions/loader/1.21.1/{loader}/{installer}/server/jar"
    rec = download(url, os.path.join(INST, "fabric-server-launch.jar"))
    print(f"[server] launcher {rec['size']} bytes sha256={rec['sha256'][:16]} loader={loader} installer={installer}")

    with open(os.path.join(INST, "eula.txt"), "w", encoding="utf-8") as f:
        f.write("# accepted for an isolated local P0 test instance\neula=true\n")
    with open(os.path.join(INST, "server.properties"), "w", encoding="utf-8") as f:
        f.write("\n".join([
            "online-mode=false",
            "level-name=world",
            "level-seed=mcbridge1201",
            "max-tick-time=-1",
            "spawn-protection=0",
            "view-distance=4",
            "simulation-distance=4",
            "motd=mcbridge1201 P0",
            "enable-command-block=true",
        ]) + "\n")

    fapi = lock["fabric"]["api"]
    shutil.copy(fapi["path"], os.path.join(INST, "mods", os.path.basename(fapi["path"])))

    meta = {
        "generatedAt": now_iso(),
        "instance": INST,
        "minecraft": "1.21.1",
        "loader": loader,
        "installer": installer,
        "serverLauncher": rec,
        "fabricApi": {"path": os.path.basename(fapi["path"]), "sha256": fapi["sha256"]},
        "java": "toolchain JDK 21 (Azul Zulu 21.0.12.1)",
    }
    write_json(os.path.join(INST, "instance.json"), meta)
    print("instance ready:", INST)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
