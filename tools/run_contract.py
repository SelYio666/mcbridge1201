"""Run the minimal container contract against a prepared server instance.

Contract (server-side, no client):
  1. place a modded chest
  2. insert 5 diamonds through the container API
  3. read the block entity NBT (must contain Items)
  4. restart the process
  5. read the NBT again (must still contain the item)

Each step is a separate server process so "restart" is a real restart, not a reload.
Exit code 0 only when every assertion passes; the JSON verdict is written next to the logs.
"""
import argparse
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUN = os.path.join(ROOT, "tools", "run_server.py")


def run(instance, log, commands, timeout=240):
    cmd = [sys.executable, RUN, "--instance", instance, "--log", log, "--timeout", str(timeout)]
    for c in commands:
        cmd += ["--command", c]
    subprocess.run(cmd, check=False)
    return open(log, encoding="utf-8", errors="replace").read()


def block_data(log):
    m = re.findall(r"has the following block data: (\{.*)", log)
    return m[-1] if m else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--instance", required=True)
    ap.add_argument("--out", default=os.path.join(ROOT, "runs", "contract"))
    ap.add_argument("--pos", default="0 100 0")
    ap.add_argument("--block", default="ironchests:iron_chest")
    ap.add_argument("--item", default="minecraft:diamond")
    ap.add_argument("--count", type=int, default=5)
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    x, y, z = args.pos.split()
    verdict = {"contract": "container.basic", "instance": os.path.abspath(args.instance),
               "steps": {}}

    log1 = os.path.join(args.out, "step1-place-insert.log")
    out1 = run(args.instance, log1, [
        f"forceload add {x} {z}",
        f"setblock {x} {y} {z} {args.block}",
        f"item replace block {x} {y} {z} container.0 with {args.item} {args.count}",
        f"data get block {x} {y} {z}",
    ])
    data1 = block_data(out1)
    verdict["steps"]["place"] = "setblock" not in out1 or "That position is not loaded" not in out1
    verdict["steps"]["insert"] = "Replaced a slot" in out1
    verdict["steps"]["nbt_after_insert"] = bool(data1 and "Items" in data1)
    verdict["blockDataAfterInsert"] = data1

    log2 = os.path.join(args.out, "step2-restart-read.log")
    out2 = run(args.instance, log2, [
        f"data get block {x} {y} {z}",
        f"data get block {x} {y} {z} Items[0].count",
    ])
    data2 = block_data(out2)
    counts = re.findall(r"has the following block data: (\d+)", out2)
    verdict["steps"]["nbt_after_restart"] = bool(data2 and "Items" in data2)
    verdict["steps"]["count_after_restart"] = bool(counts and int(counts[-1]) == args.count)
    verdict["blockDataAfterRestart"] = data2
    verdict["passed"] = all(verdict["steps"].values())
    verdict["scope"] = "dedicated server + command API; GUI/render/multiplayer NOT verified"

    out_json = os.path.join(args.out, "verdict.json")
    with open(out_json, "w", encoding="utf-8", newline="\n") as f:
        json.dump(verdict, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(json.dumps(verdict, ensure_ascii=False, indent=2))
    print("wrote", out_json)
    return 0 if verdict["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
