"""Reproducible lithium chunk-access stress check.

Runs two dedicated-server processes against one instance:
  1) force-load a (2r+1)^2 chunk square, set blocks at both far corners, save, stop
  2) restart, assert both blocks with /execute if block, save, stop

Usage:
  python tools/run_chunk_stress.py --instance work/instances/fabric-1.21.1-server-lithium \
      --out runs/p24-chunk-stress-tool --radius 7

Exit 0 only when both runs reached Done and both STRESS_OK markers appear.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--instance", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--radius", type=int, default=7, help="chunk radius (marks (2r+1)^2 chunks)")
    ap.add_argument("--timeout", type=int, default=300)
    args = ap.parse_args()

    inst = os.path.abspath(args.instance)
    out = os.path.abspath(args.out)
    os.makedirs(out, exist_ok=True)
    if not os.path.isdir(inst):
        print(f"instance not found: {inst}", file=sys.stderr)
        return 2

    r = args.radius
    block = r * 16
    add = f"forceload add {-block} {-block} {block} {block}"
    a = (block, 100, block)
    b = (-block, 100, -block)

    def run(tag: str, commands: list[str], delay: float = 1.0) -> dict:
        log = os.path.join(out, f"{tag}.log")
        result_path = os.path.join(out, f"{tag}.result.json")
        cmd = [sys.executable, os.path.join(os.path.dirname(__file__), "run_server.py"),
               "--instance", inst, "--log", log, "--timeout", str(args.timeout),
               "--command-delay", str(delay)]
        for c in commands:
            cmd += ["--command", c]
        proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                              errors="replace")
        with open(result_path, "w", encoding="utf-8") as f:
            f.write(proc.stdout)
        try:
            result = json.loads(proc.stdout)
        except json.JSONDecodeError:
            result = {"raw": proc.stdout, "stderr": proc.stderr}
        result["processExitCode"] = proc.returncode
        with open(result_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)
            f.write("\n")
        return result

    step1 = run("step1", [
        "forceload remove all",
        add,
        f"setblock {a[0]} {a[1]} {a[2]} minecraft:diamond_block",
        f"setblock {b[0]} {b[1]} {b[2]} minecraft:emerald_block",
        "save-all flush",
    ], delay=2.5)
    step2 = run("step2", [
        add,
        f"execute if block {a[0]} {a[1]} {a[2]} minecraft:diamond_block run say STRESS_OK_A",
        f"execute if block {b[0]} {b[1]} {b[2]} minecraft:emerald_block run say STRESS_OK_B",
        "save-all flush",
    ])

    log2 = open(os.path.join(out, "step2.log"), encoding="utf-8", errors="replace").read()
    log1 = open(os.path.join(out, "step1.log"), encoding="utf-8", errors="replace").read()
    marked = re.search(r"Marked (\d+) chunks", log1)
    chunksMarked = int(marked.group(1)) if marked else 0

    def has_server_marker(text, marker):
        """Only count real server output; run_server.py echoes sent commands as '# > ...'."""
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("# >"):
                continue
            if marker in stripped:
                return True
        return False

    verdict = {
        "contract": "lithium.chunk-access.stress",
        "generatedAt": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "instance": inst,
        "radiusChunks": r,
        "chunksExpected": (2 * r + 1) ** 2,
        "chunksMarked": chunksMarked,
        "steps": {
            "step1Done": bool(step1.get("doneSeen")),
            "step1Exit0": step1.get("processExitCode") == 0,
            "step2Done": bool(step2.get("doneSeen")),
            "step2Exit0": step2.get("processExitCode") == 0,
            "forceloadMarked": chunksMarked > 0,
            "markerA": has_server_marker(log2, "STRESS_OK_A"),
            "markerB": has_server_marker(log2, "STRESS_OK_B"),
        },
        "step1Log": os.path.join(out, "step1.log"),
        "step2Log": os.path.join(out, "step2.log"),
        "scope": "dedicated server + command API; no client/GUI/player/multiplayer",
    }
    verdict["passed"] = all(verdict["steps"].values())
    with open(os.path.join(out, "verdict.json"), "w", encoding="utf-8") as f:
        json.dump(verdict, f, indent=2)
        f.write("\n")
    print(json.dumps(verdict, indent=2))
    if not verdict["passed"]:
        # keep the failure visible
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
