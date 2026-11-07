"""p249: negative control - the same modpack mods on NeoForge 1.21.1.

Forge 47 (1.20.1) mods are not NeoForge 21 (1.21.1) mods: different loader, different SRG
names, different Minecraft. This probe records the refusal so the claim "needs a loader port"
has evidence instead of being asserted.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUN = Path(__file__).resolve().parent
BASE = ROOT / "work" / "launcher-e2e"
SRC = ROOT / "work" / "packtest"
GAME = ROOT / "work" / "packtest-1211"
VERSION = "neoforge-21.1.264"
sys.path.insert(0, str(ROOT / "launcher"))
import mclaunch  # noqa: E402


def link(src: Path, dst: Path) -> None:
    if dst.exists():
        return
    subprocess.run(["cmd", "/c", "mklink", "/J", str(dst), str(src)], check=True,
                   capture_output=True)


def main() -> int:
    GAME.mkdir(parents=True, exist_ok=True)
    for sub in ("assets", "libraries", "versions"):
        link(BASE / sub, GAME / sub)
    if (GAME / "mods").exists():
        shutil.rmtree(GAME / "mods")
    shutil.copytree(SRC / "mods", GAME / "mods")
    shutil.copy2(BASE / "options.txt", GAME / "options.txt")

    cmd, log, _ = mclaunch.build_command(VERSION, GAME, "PackUser", "3G")
    log.parent.mkdir(parents=True, exist_ok=True)
    latest = GAME / "logs" / "latest.log"
    latest.unlink(missing_ok=True)
    out = open(log, "w", encoding="utf-8", errors="replace")
    proc = subprocess.Popen(cmd, cwd=str(GAME), stdout=out, stderr=subprocess.STDOUT)
    result: dict[str, object] = {"version": VERSION, "mod_count": len(list((GAME / 'mods').glob('*.jar')))}
    try:
        for _ in range(60):
            time.sleep(2)
            if proc.poll() is not None:
                break
            text = latest.read_text(encoding="utf-8", errors="replace") if latest.exists() else ""
            if "Incompatible mods found" in text or "Missing or unsupported" in text:
                break
        text = latest.read_text(encoding="utf-8", errors="replace") if latest.exists() else ""
        launch_text = log.read_text(encoding="utf-8", errors="replace") if log.exists() else ""
        both = text + "\n" + launch_text
        result["exited"] = proc.poll() is not None
        keys = ("Incompatible mods found", "Missing or unsupported mandatory dependencies",
                "Failed to load mods", "Mod ID", "Expected range", "Actual version",
                "requires neoForge", "requires forge",
                "ClassNotFoundException", "NoClassDefFoundError",
                "net.minecraftforge.fml.loading")
        result["errors"] = [l.strip()[:160] for l in both.splitlines()
                            if any(k in l for k in keys)][:12]
        result["loaded"] = "joined the game" in text
    finally:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
        out.close()
    (RUN / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["errors"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
