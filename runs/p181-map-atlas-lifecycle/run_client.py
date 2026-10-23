#!/usr/bin/env python3
"""Run the p181 map lifecycle scene with the p175 evidence runner.

Waits for a second atlas upload (`map-atlas update`), screenshots the updated map, then waits for
the normal `/stop` world-exit cleanup marker (`map-atlas clear`).
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUN = Path(__file__).resolve().parent
runner = ROOT / "runs" / "p175-map-atlas" / "run_client.py"
args = [
    sys.executable, str(runner),
    "--world", "ColdWorldMapUpdate",
    "--run-dir", str(RUN),
    "--require-log", "map-atlas update",
    "--exit-log", "map-atlas clear atlases=1",
    "--settle", "3",
    "--timeout", "180",
] + sys.argv[1:]
sys.exit(subprocess.call(args))
