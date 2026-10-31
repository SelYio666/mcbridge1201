"""p222: HMCL game-directory detection and --hmcl install path.

Covers: config file parsing (mocked APPDATA), %APPDATA%/.minecraft fallback,
explicit directory with versions/, and explicit directory with a nested .minecraft.
"""
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import from_source_install as fs  # noqa: E402

checks = []


def check(name, ok, detail=""):
    checks.append((name, bool(ok), detail))
    print(("PASS " if ok else "FAIL ") + name + ("  " + detail if detail else ""))


base = Path(tempfile.mkdtemp(prefix="p222-"))
old_appdata = os.environ.get("APPDATA")
try:
    appdata = base / "appdata"
    (appdata / ".hmcl" / "config").mkdir(parents=True)
    game = base / "hmcl-game"
    (game / "versions").mkdir(parents=True)
    (appdata / ".hmcl" / "config" / "user-game-directories.json").write_text(json.dumps({
        "$schema": "https://schemas.glavo.site/hmcl/game-directories/1.0.0",
        "directories": [{"id": "game-directory:x", "path": str(game)}],
    }), encoding="utf-8")
    os.environ["APPDATA"] = str(appdata)
    check("hmcl config path is used", fs.hmcl_game_dir() == game, repr(fs.hmcl_game_dir()))

    (appdata / ".hmcl" / "config" / "user-game-directories.json").unlink()
    (appdata / ".minecraft" / "versions").mkdir(parents=True)
    check("hmcl falls back to %APPDATA%/.minecraft",
          fs.hmcl_game_dir() == appdata / ".minecraft", repr(fs.hmcl_game_dir()))

    explicit = base / "explicit"
    (explicit / "versions").mkdir(parents=True)
    check("explicit directory with versions/ is used",
          fs.hmcl_game_dir(explicit) == explicit, repr(fs.hmcl_game_dir(explicit)))

    nested = base / "nested"
    (nested / ".minecraft" / "versions").mkdir(parents=True)
    check("explicit directory with .minecraft uses the nested one",
          fs.hmcl_game_dir(nested) == nested / ".minecraft", repr(fs.hmcl_game_dir(nested)))

    check("explicit empty directory yields None", fs.hmcl_game_dir(base / "empty") is None)
finally:
    if old_appdata is None:
        os.environ.pop("APPDATA", None)
    else:
        os.environ["APPDATA"] = old_appdata
    shutil.rmtree(base, ignore_errors=True)

ok = all(c[1] for c in checks)
print(f"\n{sum(1 for c in checks if c[1])}/{len(checks)} checks passed")
sys.exit(0 if ok else 1)
