#!/usr/bin/env python3
"""A/B/C the fast_buffer_upload vertex mixin on a static 80-armor-stand scene.

Phases: off1, off2 (off/off control for run-to-run nondeterminism), on1, on2 (on stability).
Each phase gets a fresh ColdWorldVertex (camera locked every tick), the corresponding jar, a
client run and a PrintWindow screenshot. Checks:
  * off runs never print the fast-buffer-upload marker;
  * on runs do (glBufferSubData branch actually executes);
  * neither side logs GL/mixin errors or crashes;
  * the off/on pixel difference is within the off/off control (i.e. no new visual regression);
  * on/on is not worse than the control.
The static scene's residual difference is one armor stand at the crosshair; the control proves it
is baseline run-to-run variation, not the mixin.
"""
from __future__ import annotations

import argparse
import io
import json
import re
import shutil
import subprocess
import sys
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUN = Path(__file__).resolve().parent
INSTANCE = ROOT / "work" / "launcher-e2e"
MODS = INSTANCE / "mods"
P175_RUNNER = ROOT / "runs" / "p175-map-atlas" / "run_client.py"
OFF_JAR = ROOT / ".build" / "ImmediatelyFast-port-off.jar"
ON_JAR = ROOT / ".build" / "ImmediatelyFast-vertex-on.jar"
FAST_RE = re.compile(r"fast-buffer-upload subdata count=(\d+)")
BAD_MARKERS = [
    "ClassCastException",
    "InvalidInjectionException",
    "Mixin apply for mod immediatelyfast failed",
    "Mixin transformation of net.minecraft.class_291 failed",
    "java.lang.NoClassDefFoundError",
    "java.lang.NoSuchMethodError",
    "GL_INVALID",
    "OpenGL error",
    "Uncaught exception in thread",
]

sys.path.insert(0, str(RUN))
import make_world  # noqa: E402


def log_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except FileNotFoundError:
        return ""


def run_phase(tag: str, jar: Path) -> dict:
    out = RUN / tag
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    with redirect_stdout(io.StringIO()):
        make_world.prepare()
    shutil.copy2(jar, MODS / "ImmediatelyFast-ported.jar")
    print(f"[{tag}] launching with {jar.name} ({jar.stat().st_size} bytes)")
    proc = subprocess.run(
        [sys.executable, str(P175_RUNNER),
         "--world", "ColdWorldVertex",
         "--run-dir", str(out),
         "--join-only",
         "--timeout", "150",
         "--settle", "15"],
        cwd=str(ROOT), capture_output=True, text=True)
    if proc.returncode != 0:
        print(f"[{tag}] runner exit {proc.returncode}; log tail:")
        print("\n".join((proc.stdout or "").splitlines()[-8:]))
        print("\n".join((proc.stderr or "").splitlines()[-8:]))
    text = log_text(out / "client.log")
    fast = [int(m.group(1)) for m in FAST_RE.finditer(text)]
    errors = [line for line in text.splitlines() if any(m in line for m in BAD_MARKERS)]
    try:
        result = json.loads((out / "result.json").read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 - missing result is a failure
        result = {"error": repr(exc)}
    result.update({
        "fast_upload_markers": len(fast),
        "fast_upload_max": max(fast) if fast else 0,
        "bad_lines": errors,
        "runner_rc": proc.returncode,
    })
    print(f"[{tag}] joined={result.get('joined')} shot={result.get('map_world_rendered')} "
          f"fast_markers={len(fast)} max={result['fast_upload_max']} bad={len(errors)}")
    return result


def image_diff(name: str, off: Path, on: Path) -> dict:
    try:
        from PIL import Image, ImageChops
        import numpy as np
    except Exception as exc:  # noqa: BLE001 - report missing imaging deps
        return {"error": repr(exc)}
    a = Image.open(off).convert("RGB")
    b = Image.open(on).convert("RGB")
    if a.size != b.size:
        return {"error": f"size mismatch {a.size} vs {b.size}"}
    diff = ImageChops.difference(a, b)
    arr = np.asarray(diff)
    total = a.size[0] * a.size[1]
    changed = int((arr.max(axis=2) > 2).sum())
    result = {
        "size": list(a.size),
        "changed_pixels": changed,
        "changed_ratio": changed / total,
        "mean_abs": float(arr.mean()),
        "max_channel": int(arr.max()),
    }
    diff.convert("L").point(lambda v: min(255, v * 8)).save(RUN / f"compare-{name}.png")
    return result


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--off-jar", default=str(OFF_JAR))
    ap.add_argument("--on-jar", default=str(ON_JAR))
    args = ap.parse_args()
    off_jar = Path(args.off_jar)
    on_jar = Path(args.on_jar)
    for jar in (off_jar, on_jar):
        if not jar.exists():
            print(f"missing jar: {jar}", file=sys.stderr)
            return 2
    if off_jar.resolve() == on_jar.resolve():
        print("off and on jars are the same file", file=sys.stderr)
        return 2

    off1 = run_phase("off1", off_jar)
    off2 = run_phase("off2", off_jar)
    on1 = run_phase("on1", on_jar)
    on2 = run_phase("on2", on_jar)

    control = image_diff("off-off2", RUN / "off1" / "world.png", RUN / "off2" / "world.png")
    on_stability = image_diff("on-on2", RUN / "on1" / "world.png", RUN / "on2" / "world.png")
    on_vs_off = image_diff("off-on", RUN / "off1" / "world.png", RUN / "on1" / "world.png")
    control_ratio = control.get("changed_ratio", 1.0)
    passed = bool(
        all(r.get("joined") and r.get("map_world_rendered") for r in (off1, off2, on1, on2))
        and off1.get("fast_upload_markers") == 0 and off2.get("fast_upload_markers") == 0
        and on1.get("fast_upload_markers", 0) > 0 and on2.get("fast_upload_markers", 0) > 0
        and not off1.get("bad_lines") and not off2.get("bad_lines")
        and not on1.get("bad_lines") and not on2.get("bad_lines")
        # no new visual regression beyond the off/off run-to-run control (small margin)
        and on_vs_off.get("changed_ratio", 1.0) <= max(control_ratio * 1.25, 0.002)
        and on_stability.get("changed_ratio", 1.0) <= max(control_ratio * 1.25, 0.002)
    )
    payload = {
        "scene": "ColdWorldVertex (80 static armor stands, camera locked every tick, time 6000, no clouds/weather)",
        "off_jar": str(off_jar),
        "on_jar": str(on_jar),
        "phases": {"off1": off1, "off2": off2, "on1": on1, "on2": on2},
        "pixel_diff": {
            "off_off2_control": control,
            "on_on2_stability": on_stability,
            "off1_on1": on_vs_off,
        },
        "passed": passed,
    }
    (RUN / "result.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                                     encoding="utf-8")
    summary = {
        "passed": passed,
        "off1": {k: off1.get(k) for k in ("joined", "map_world_rendered", "fast_upload_markers", "bad_lines")},
        "off2": {k: off2.get(k) for k in ("joined", "map_world_rendered", "fast_upload_markers", "bad_lines")},
        "on1": {k: on1.get(k) for k in ("joined", "map_world_rendered", "fast_upload_markers", "fast_upload_max", "bad_lines")},
        "on2": {k: on2.get(k) for k in ("joined", "map_world_rendered", "fast_upload_markers", "fast_upload_max", "bad_lines")},
        "diffs": {"control": control, "on_stability": on_stability, "off_on": on_vs_off},
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
