#!/usr/bin/env python3
"""Run the p188 atlas overflow scene with the p175 evidence runner.

Waits for the overflow atlas creation (`map-atlas create id=1`), the map 1024 bind
(`map-atlas bind map=map/1024 ... map_atlas/1`), screenshots the held map, then waits for the
normal world-exit cleanup with BOTH atlases (`map-atlas clear atlases=2`).
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
    "--world", "ColdWorldAtlasOverflow",
    "--run-dir", str(RUN),
    "--require-map", "1",
    "--require-map", "1024",
    "--require-log", "map-atlas create id=1",
    "--settle", "8",
    "--exit-log", "map-atlas clear atlases=2",
    "--timeout", "240",
] + sys.argv[1:]
sys.exit(subprocess.call(args))
