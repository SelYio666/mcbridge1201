#!/usr/bin/env python3
"""Single-stream vs 4-range download A/B for a large file (client jar).

Writes runs/p126-segment-bench/bench.json and deletes every downloaded file afterwards.
Uses only stdlib; verifies SHA-1 of both results, so "faster" never wins by corrupting data.
"""
from __future__ import annotations

import hashlib
import json
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "launcher"))
import mclaunch  # noqa: E402

OUT = ROOT / "runs" / "p126-segment-bench"
UA = {"User-Agent": "mcbridge-segbench/0.1"}
SEGMENTS = 4
ROUNDS = 2


def sha1(path: Path) -> str:
    h = hashlib.sha1()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def single(url: str, dest: Path) -> float:
    t0 = time.time()
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120) as r, \
            dest.open("wb") as f:
        while True:
            chunk = r.read(1 << 20)
            if not chunk:
                break
            f.write(chunk)
    return time.time() - t0


def ranged(url: str, dest: Path, size: int, segments: int) -> tuple[float, list[int]]:
    with dest.open("wb") as f:
        f.truncate(size)
    statuses: list[int] = [0] * segments
    errors: list[str] = []

    def worker(i: int) -> None:
        start = i * size // segments
        end = (i + 1) * size // segments - 1
        try:
            req = urllib.request.Request(url, headers={**UA, "Range": f"bytes={start}-{end}"})
            with urllib.request.urlopen(req, timeout=120) as r:
                statuses[i] = r.status
                if r.status != 206:
                    errors.append(f"segment {i}: status {r.status} (range ignored)")
                    return
                fh = dest.open("r+b")
                try:
                    fh.seek(start)
                    while True:
                        chunk = r.read(1 << 20)
                        if not chunk:
                            break
                        fh.write(chunk)
                finally:
                    fh.close()
        except Exception as exc:  # noqa: BLE001 - recorded, then the run fails
            errors.append(f"segment {i}: {exc!r}")

    t0 = time.time()
    threads = [threading.Thread(target=worker, args=(i,)) for i in range(segments)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    elapsed = time.time() - t0
    if errors:
        raise RuntimeError("; ".join(errors))
    return elapsed, statuses


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    v = mclaunch.find_version("1.21.1")
    meta = mclaunch.http_json(v["url"], max_age=0)
    jar = meta["downloads"]["client"]
    size, digest = int(jar["size"]), jar["sha1"]
    url = jar["url"]
    tmp = ROOT / "work" / "p126-client.jar"
    tmp.parent.mkdir(parents=True, exist_ok=True)
    results = {"url": url, "size": size, "segments": SEGMENTS, "rounds": [], "ok": False}
    try:
        for rnd in range(ROUNDS):
            s = single(url, tmp)
            same = sha1(tmp) == digest
            results["rounds"].append({"mode": "single", "round": rnd, "seconds": round(s, 3),
                                      "mbps": round(size / 1e6 / s, 2), "sha1_ok": same})
            if not same:
                raise RuntimeError("single download sha1 mismatch")
            m, statuses = ranged(url, tmp, size, SEGMENTS)
            same = sha1(tmp) == digest
            results["rounds"].append({"mode": "ranged", "round": rnd, "seconds": round(m, 3),
                                      "mbps": round(size / 1e6 / m, 2), "sha1_ok": same,
                                      "statuses": statuses})
            if not same:
                raise RuntimeError("ranged download sha1 mismatch")
        s_times = [r["seconds"] for r in results["rounds"] if r["mode"] == "single"]
        m_times = [r["seconds"] for r in results["rounds"] if r["mode"] == "ranged"]
        results["single_best"] = min(s_times)
        results["ranged_best"] = min(m_times)
        results["speedup"] = round(results["single_best"] / results["ranged_best"], 3)
        results["ok"] = True
    except Exception as exc:  # noqa: BLE001
        results["error"] = repr(exc)
    finally:
        tmp.unlink(missing_ok=True)
        results["cleaned"] = not tmp.exists()
    (OUT / "bench.json").write_text(json.dumps(results, indent=2, ensure_ascii=False),
                                   encoding="utf-8")
    print(json.dumps({k: results.get(k) for k in ("size", "single_best", "ranged_best",
                                                  "speedup", "ok", "error", "cleaned")},
                     ensure_ascii=False))
    for r in results["rounds"]:
        print(f"  {r['mode']:6s} r{r['round']}  {r['seconds']:6.3f}s  {r['mbps']:5.2f} MB/s"
              f"  sha1={r['sha1_ok']}")
    return 0 if results["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
