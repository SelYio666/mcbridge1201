"""Run the p206 selection harness unchanged, into this directory (p207).

The click path, window raising, probe wiring and screenshots must be identical between the control
and the fix, so this does not re-implement them: it loads `runs/p206-modmenu-select/run.py` and calls
its `main()`. The only thing that changes between the two runs is `--modmenu`.

Usage:
  python runs/p207-description-panel/run.py --modmenu work/client/modmenu-selected.jar \
      --out runs/p207-description-panel/before --row 3
  python runs/p207-description-panel/run.py --modmenu work/client/modmenu-description.jar \
      --out runs/p207-description-panel/after --row 3
"""
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HARNESS = ROOT / "runs" / "p206-modmenu-select" / "run.py"


def load():
    spec = importlib.util.spec_from_file_location("p206harness", HARNESS)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


if __name__ == "__main__":
    try:
        import PIL  # noqa: F401
    except ModuleNotFoundError:
        # The p206 harness grabs the window through Pillow and only prints
        # "screenshot skipped: Pillow missing" when it cannot - which would leave this run without
        # the pixels its verdict is based on. Fail here instead of producing a run with no evidence.
        sys.exit("Pillow is not installed for this interpreter "
                 f"({sys.executable}); run with one that has it, e.g. `py -3.12`")
    sys.exit(load().main())
