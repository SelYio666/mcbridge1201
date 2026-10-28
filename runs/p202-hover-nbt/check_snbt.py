#!/usr/bin/env python3
"""Parse-check the p202 container SNBT against the real dedicated server, without a client.

/item replace needs an online player to APPLY, but the item argument is parsed first, so an
invalid component id or a malformed SNBT list reports "Unknown item component" / "Expected ..."
even with nobody online. That is enough to catch the mistake the first p202 run hit
(shulker_box["minecraft:container"=...] -> Unknown item component 'minecraft:'), which would
otherwise cost another full client run to discover.
"""
from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SERVER = ROOT / "work" / "instances" / "fabric-1.21.1-server-trashslot"
LOG = ROOT / "work" / "tmp" / "p202-snbt-server.log"

sys.path.insert(0, str(ROOT / "runs" / "p202-hover-nbt"))
import run as harness  # noqa: E402

CANDIDATES = [
    ("rich-unquoted-outer", harness.rich_box_command()),
    ("plain", harness.plain_box_command()),
]


def main() -> int:
    java_home = str(ROOT.parent / ".toolchain" / "jdk")
    java = Path(java_home) / "bin" / "java.exe"
    LOG.write_text("", encoding="utf-8")
    with LOG.open("w", encoding="utf-8", errors="replace") as out:
        proc = subprocess.Popen([str(java), "-Xmx1G", "-jar", "fabric-server-launch.jar", "nogui"],
                                cwd=str(SERVER), stdout=out, stderr=subprocess.STDOUT,
                                stdin=subprocess.PIPE)
        try:
            deadline = time.time() + 120
            while time.time() < deadline:
                if proc.poll() is not None:
                    break
                if "Done (" in LOG.read_text(encoding="utf-8", errors="replace"):
                    break
                time.sleep(1)
            text = LOG.read_text(encoding="utf-8", errors="replace")
            if "Done (" not in text:
                print("server did not start")
                return 2
            mark = len(text)
            for name, command in CANDIDATES:
                # no player online: this only exercises the PARSER, which is the point
                proc.stdin.write((f"say PARSE {name}\n").encode("utf-8"))
                proc.stdin.write((command + "\n").encode("utf-8"))
                proc.stdin.flush()
                time.sleep(2)
            time.sleep(2)
            tail = LOG.read_text(encoding="utf-8", errors="replace")[mark:]
            bad = ("Unknown item component", "Expected", "Couldn't parse", "Invalid")
            for line in tail.splitlines():
                if any(marker in line for marker in bad) or "PARSE" in line:
                    print(line)
            ok = not any(marker in tail for marker in bad)
            print("PARSE CHECK:", "OK" if ok else "FAILED")
            return 0 if ok else 1
        finally:
            if proc.poll() is None:
                proc.stdin.write(b"stop\n")
                proc.stdin.flush()
                try:
                    proc.wait(timeout=25)
                except subprocess.TimeoutExpired:
                    proc.kill()


if __name__ == "__main__":
    sys.exit(main())
