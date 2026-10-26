#!/usr/bin/env python3
"""Run the p194 third-atlas scene with the p175 evidence runner.

Waits for the third atlas creation (`map-atlas create id=2`), the map 2049 bind
(`map-atlas bind map=map/2049 ... map_atlas/2`), screenshots the held map, then waits for the
normal world-exit cleanup with ALL THREE atlases (`map-atlas clear atlases=3`).
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
    "--world", "ColdWorldAtlasThird",
    "--run-dir", str(RUN),
    "--require-map", "1",
    "--require-map", "1025",
    "--require-map", "2049",
    "--require-log", "map-atlas create id=2",
    "--settle", "8",
    "--exit-log", "map-atlas clear atlases=3",
    "--timeout", "300",
] + sys.argv[1:]
sys.exit(subprocess.call(args))
