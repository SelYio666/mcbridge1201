"""p220: pcl2_game_dir must not return a configured-but-missing folder.

Before the fix, `LaunchFolderSelect:$missing\\` returned `<exe>/missing` even when it did not exist,
so `--pcl` would create and install into a stray folder instead of falling back.
"""
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


base = Path(tempfile.mkdtemp(prefix="p220-"))
try:
    pcl = base / "pcl"
    (pcl / "PCL").mkdir(parents=True)
    (pcl / "PCL" / "Setup.ini").write_text("LaunchFolderSelect:$missing\\\\\n", encoding="utf-8")
    got = fs.pcl2_game_dir(pcl)
    check("missing configured folder -> None (no stray path)", got is None, repr(got))

    (pcl / ".minecraft").mkdir()
    got = fs.pcl2_game_dir(pcl)
    check("portable .minecraft is the fallback", got == pcl / ".minecraft", repr(got))

    (pcl / "PCL" / "Setup.ini").write_text("LaunchFolderSelect:$custom\\\\\n", encoding="utf-8")
    (pcl / "custom").mkdir()
    got = fs.pcl2_game_dir(pcl)
    check("existing relative folder is used", got == pcl / "custom", repr(got))

    absdir = base / "abs-mc"
    absdir.mkdir()
    (pcl / "PCL" / "Setup.ini").write_text(f"LaunchFolderSelect:{absdir}\\\\\n", encoding="utf-8")
    got = fs.pcl2_game_dir(pcl)
    check("absolute existing folder is used", got == absdir, repr(got))
finally:
    shutil.rmtree(base, ignore_errors=True)

ok = all(c[1] for c in checks)
print(f"\n{sum(1 for c in checks if c[1])}/{len(checks)} checks passed")
sys.exit(0 if ok else 1)
