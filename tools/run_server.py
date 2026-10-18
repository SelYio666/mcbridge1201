"""Run a Minecraft dedicated server under control, capture its log, stop it cleanly.

Python is used (not a shell pipeline) because the host's PowerShell/git TLS stack is
unusable and because stdin/stdout of the JVM must be driven reliably on Windows.

Usage:
  python tools/run_server.py --instance work/instances/fabric-1.21.1-server \
      --log runs/p0-server-baseline/server.log --timeout 300

Exit code mirrors the JVM exit code; the script itself returns 0 only when the
"Done" marker was observed (otherwise 10 = boot timeout, 11 = exited early).
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--instance", required=True)
    ap.add_argument("--log", required=True)
    ap.add_argument("--timeout", type=int, default=300)
    ap.add_argument("--java", default=os.environ.get("JAVA_HOME", "") + r"\bin\java.exe")
    ap.add_argument("--xmx", default="1536M")
    ap.add_argument("--no-stop", action="store_true", help="do not send stop after Done (crash tests)")
    args = ap.parse_args()

    inst = os.path.abspath(args.instance)
    log_path = os.path.abspath(args.log)
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    if not os.path.exists(args.java):
        print(f"java not found: {args.java}", file=sys.stderr)
        return 2
    # The host's %TEMP% is not writable for this process (ACL from the sandbox);
    # ImageIO/zipfs/tinyremapper all need a writable java.io.tmpdir.
    tmpdir = os.path.join(inst, "tmp")
    os.makedirs(tmpdir, exist_ok=True)

    cmd = [args.java, f"-Xmx{args.xmx}", "-Xms512M", "-Dfile.encoding=UTF-8",
           f"-Djava.io.tmpdir={tmpdir}",
           "-jar", "fabric-server-launch.jar", "nogui"]
    result = {
        "startedAt": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "instance": inst,
        "argv": cmd,
        "doneSeen": False,
        "exitCode": None,
        "durationSeconds": None,
    }
    t0 = time.time()
    with open(log_path, "w", encoding="utf-8", errors="replace") as log:
        log.write("# argv: " + " ".join(cmd) + "\n")
        p = subprocess.Popen(cmd, cwd=inst, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace",
                             bufsize=1)
        state = {"done": False}

        def pump():
            for line in p.stdout:
                log.write(line)
                log.flush()
                if "Done (" in line or "For help, type" in line:
                    state["done"] = True

        th = threading.Thread(target=pump, daemon=True)
        th.start()
        deadline = t0 + args.timeout
        try:
            while time.time() < deadline:
                if p.poll() is not None:
                    break
                if state["done"] and not args.no_stop:
                    time.sleep(2)
                    try:
                        p.stdin.write("stop\n")
                        p.stdin.flush()
                    except Exception:
                        pass
                    break
                time.sleep(0.5)
            else:
                result["timeout"] = True
                p.kill()
        finally:
            try:
                code = p.wait(timeout=120)
            except subprocess.TimeoutExpired:
                p.kill()
                code = p.wait()
            result["exitCode"] = code
            th.join(timeout=5)
    result["doneSeen"] = state["done"]
    result["durationSeconds"] = round(time.time() - t0, 1)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not state["done"]:
        return 10 if result.get("timeout") else 11
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
