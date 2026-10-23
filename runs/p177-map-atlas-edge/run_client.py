#!/usr/bin/env python3
"""Run the p177 edge-case scene with the p175 evidence runner.

Requires both map ids to be bound to the atlas and writes the logs/screenshot into this directory.
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
    "--world", "ColdWorldMapEdge",
    "--run-dir", str(RUN),
    "--require-map", "1",
    "--require-map", "2",
    "--settle", "12",
] + sys.argv[1:]
sys.exit(subprocess.call(args))
