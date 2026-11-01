"""Join an existing local world once (no clicks, quickplay) and report Not a string."""
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GAME = ROOT / "work" / "launcher-e2e"
sys.path.insert(0, str(ROOT / "launcher"))
import mclaunch  # noqa: E402

latest = GAME / "logs" / "latest.log"
latest.unlink(missing_ok=True)
cmd, log, _ = mclaunch.build_command("1.20.4", GAME, "SelYio", "2G",
                                     extra_game=["--quickPlaySingleplayer", "p229-world"])
log.parent.mkdir(parents=True, exist_ok=True)
out = open(log, "w", encoding="utf-8", errors="replace")
proc = subprocess.Popen(cmd, cwd=str(GAME), stdout=out, stderr=subprocess.STDOUT)
seen = False
try:
    for _ in range(60):
        time.sleep(2)
        text = latest.read_text(encoding="utf-8", errors="replace") if latest.exists() else ""
        if "Not a string" in text:
            seen = True
            break
        if "joined the game" in text:
            break
finally:
    proc.terminate()
    try:
        proc.wait(timeout=8)
    except subprocess.TimeoutExpired:
        proc.kill()
    out.close()
print("not_a_string =", seen)
