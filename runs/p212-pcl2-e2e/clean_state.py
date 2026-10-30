"""Remove the state a previous p212 run installed, so one panel click can produce before/after (p212).

The first click installed 1.20.4 into the real game folder; a second click would then show it in
`before` as well and prove nothing. This deletes exactly two things and nothing else:

* `versions/<version>/` (the folder the panel created);
* the `mcbridge-<version>` entry in `launcher_profiles.json` (leaving `PCL`, `selectedProfile` and
  `settings` untouched).

It records what it removed, so "the 1.20.4 in this evidence was created by the panel click, not by
an earlier attempt" is checkable instead of asserted.

Usage:
  python runs/p212-pcl2-e2e/clean_state.py --version 1.20.4 --out runs/p212-pcl2-e2e
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_GAME = Path.home() / "AppData" / "Roaming" / ".minecraft"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", default="1.20.4")
    ap.add_argument("--game", default=str(DEFAULT_GAME))
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    out = Path(args.out)
    if not out.is_absolute():
        out = ROOT / out
    out.mkdir(parents=True, exist_ok=True)
    game = Path(args.game)
    info: dict = {"game": str(game), "version": args.version,
                  "ran_at": time.strftime("%Y-%m-%dT%H:%M:%S")}

    vdir = game / "versions" / args.version
    info["version_dir_removed"] = None
    if vdir.is_dir():
        files = {p.name: {"bytes": p.stat().st_size,
                          "sha1": hashlib.sha1(p.read_bytes()).hexdigest()}
                 for p in vdir.iterdir() if p.is_file()}
        info["version_dir_removed"] = {"path": str(vdir), "files": files}
        shutil.rmtree(vdir)

    lpj = game / "launcher_profiles.json"
    key = f"mcbridge-{args.version}"
    info["profile_removed"] = None
    if lpj.is_file():
        data = json.loads(lpj.read_text(encoding="utf-8"))
        profiles = data.get("profiles") or {}
        if key in profiles:
            info["profile_removed"] = profiles.pop(key)
        data["profiles"] = profiles
        if data.get("selectedProfile") == key:
            data["selectedProfile"] = "PCL" if "PCL" in profiles else next(iter(profiles), None)
        if not any(p.get("lastVersionId") == args.version for p in profiles.values()):
            pass  # nothing else references the version; leave the file otherwise as it was
        lpj.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        info["profile_keys_after"] = sorted(profiles.keys())
        info["selected_profile_after"] = data.get("selectedProfile")

    info["version_dir_exists_after"] = vdir.is_dir()
    (out / "clean-state.json").write_text(json.dumps(info, ensure_ascii=False, indent=2) + "\n",
                                          encoding="utf-8", newline="\n")
    print(json.dumps({"removed_dir": bool(info["version_dir_removed"]),
                      "removed_profile": bool(info["profile_removed"]),
                      "profile_keys_after": info.get("profile_keys_after"),
                      "version_dir_exists_after": info["version_dir_exists_after"]},
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
