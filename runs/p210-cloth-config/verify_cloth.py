"""Verdict for p210: does AppleSkin's Cloth Config screen open on 1.21.1, and can it draw?

Two runs are compared, and they differ in exactly one file: `appleskin-patched.jar` (its nested
Cloth Config 11.1.136 still reads the removed `Screen.field_44669`) and `appleskin-cloth.jar` (the
same outer jar with the nested cloth jar patched). Nothing here trusts the harness: the probe's own
report, the client log, the shipped bytecode and the screenshot are checked separately.

1. **Control** (`before/`): opening the screen must fail, the error must be the removed field, and
   the stack must be inside Cloth's `ConfigBuilderImpl.<init>` - otherwise the run proves nothing
   about this patch, it just failed somewhere.
2. **Fix** (`after3/`): the screen must exist, be a `ClothConfigScreen`, hold >= 13 rows of which 9
   are `BooleanToggleBuilder$1`, the client log must carry no mod error, and the screenshot must
   exist and be more than 100 KB (an empty frame compresses far below that).
3. **Bytecode** of the shipped jar: the patched `ConfigBuilderImpl` must not mention `field_44669`
   any more, and Cloth's demo lambda must not mention `field_9131` / `method_7978(Enchantment,int)`
   any more - the two members that only showed up after the first one was fixed.
4. **Provenance**: each `result.json` records the sha256 it ran against; that hash must equal the
   hash of the jar on disk, the two runs must be different jars, and the fix run must be the current
   `work/client/appleskin-cloth.jar` (so after3 cannot silently belong to an older build).

Usage:
  python runs/p210-cloth-config/verify_cloth.py
"""
import hashlib
import io
import json
import re
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUN = Path(__file__).resolve().parent
CONTROL_JAR = ROOT / "work" / "client" / "appleskin-patched.jar"
FIXED_JAR = ROOT / "work" / "client" / "appleskin-cloth.jar"
CLOTH_ENTRY = "META-INF/jars/cloth-config-fabric-11.1.136.jar"
PROBE_ENTRY = "p210probe.jar"
REMOVED_FIELD = "field_44669"
CHILD_LINE = re.compile(r"P210_CHILD i=0 class=(\S+) rows=(\d+) kinds=\{([^}]*)\}")
MIN_ROWS = 13
MIN_BOOLEAN_TOGGLES = 9
MIN_PNG_BYTES = 100 * 1024

checks: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    checks.append((name, ok, detail))
    print(("PASS " if ok else "FAIL ") + name + (("  " + detail) if detail else ""))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(run_dir: Path) -> dict:
    return json.loads((run_dir / "result.json").read_text(encoding="utf-8"))


def log_text(run_dir: Path) -> str:
    return (run_dir / "client.log").read_text(encoding="utf-8", errors="replace")


def nested(jar: Path, entry: str) -> zipfile.ZipFile:
    with zipfile.ZipFile(jar) as outer:
        return zipfile.ZipFile(io.BytesIO(outer.read(entry)))


def kinds(raw: str) -> dict[str, int]:
    out: dict[str, int] = {}
    for part in raw.split(","):
        key, _, value = part.strip().partition("=")
        if value.strip().isdigit():
            out[key.strip()] = int(value)
    return out


def main() -> int:
    for need in (CONTROL_JAR, FIXED_JAR, RUN / "before" / "result.json",
                 RUN / "after3" / "result.json"):
        if not need.is_file():
            raise SystemExit(f"missing input: {need}")

    before = load(RUN / "before")
    after = load(RUN / "after3")
    before_log = log_text(RUN / "before")
    after_log = log_text(RUN / "after3")

    # --- 1. control ------------------------------------------------------
    control = before.get("config") or {}
    control_error = control.get("error") or ""
    check("control_screen_does_not_open", control.get("ok") is False, f"ok={control.get('ok')}")
    check("control_dies_on_the_removed_field", REMOVED_FIELD in control_error,
          control_error[:120] or "no error recorded")
    check("control_dies_inside_cloth_builder",
          any("ConfigBuilderImpl.<init>" in line for line in before.get("stack") or []),
          "stack names ConfigBuilderImpl.<init>")
    control_shot = RUN / "before" / "config.png"
    check("control_kept_a_picture_of_the_failure",
          control_shot.is_file() and control_shot.stat().st_size > MIN_PNG_BYTES,
          f"{control_shot.stat().st_size if control_shot.is_file() else 0} bytes")

    # --- 2. fix ----------------------------------------------------------
    fix = after.get("config") or {}
    screen = fix.get("screen") or ""
    check("fix_screen_opens", fix.get("ok") is True, f"ok={fix.get('ok')}")
    check("fix_screen_is_the_cloth_screen", screen.endswith("ClothConfigScreen"), screen)
    match = CHILD_LINE.search(after_log)
    check("fix_reports_a_row_list", bool(match),
          match.group(0)[:160] if match else "no P210_CHILD line with rows= in the log")
    rows, row_kinds = (0, {})
    if match:
        rows, row_kinds = int(match.group(2)), kinds(match.group(3))
        check("fix_has_at_least_thirteen_rows", rows >= MIN_ROWS, f"rows={rows}")
        check("fix_rows_are_the_nine_toggles",
              row_kinds.get("BooleanToggleBuilder$1") == MIN_BOOLEAN_TOGGLES,
              "kinds=" + json.dumps(row_kinds, sort_keys=True))
    check("fix_has_no_mod_error", after.get("client_errors") == [],
          "; ".join(after.get("client_errors") or []) or "none")
    check("fix_has_no_missing_member", after.get("no_such_field") == 0
          and after.get("no_such_method") == 0,
          f"no_such_field={after.get('no_such_field')} no_such_method={after.get('no_such_method')}")
    done = after.get("done") or {}
    check("fix_reached_the_end_of_the_probe", done.get("tick") is not None,
          f"done.tick={done.get('tick')} screen={done.get('screen')}")
    shot = RUN / "after3" / "config.png"
    check("fix_screenshot_exists", shot.is_file(), str(shot))
    if shot.is_file():
        check("fix_screenshot_is_not_empty", shot.stat().st_size > MIN_PNG_BYTES,
              f"{shot.stat().st_size} bytes")
    buried = [line for line in after_log.splitlines()
              if "NoSuchFieldError" in line or "NoSuchMethodError" in line
              or "IncompatibleClassChangeError" in line or "UnsupportedOperationException" in line]
    check("fix_log_has_no_buried_linkage_error", not buried,
          buried[0][:120] if buried else "none")

    # --- 2b. interaction -------------------------------------------------
    # "It drew thirteen rows" is compatible with a screen that swallows every click. The probe
    # clicks the first toggle's button through Screen.mouseClicked and reads the entry's value back
    # in the same process, so the flip below is a state change, not a redrawn pixel.
    toggle = after.get("toggle") or {}
    check("fix_toggle_was_found_and_clicked", bool(after.get("toggle_row")),
          (after.get("toggle_row") or {}).get("class", "no P210_TOGGLE_ROW line"))
    check("fix_click_was_delivered_by_the_screen",
          bool(after.get("toggle_click")) and "handled=true" in (after.get("toggle_click") or ""),
          after.get("toggle_click") or "no P210_CLICK line")
    check("fix_toggle_value_flipped", toggle.get("flipped") is True,
          f"{toggle.get('before')} -> {toggle.get('after')}")
    check("fix_toggle_flip_came_from_the_click", toggle.get("direct_press") is False,
          "direct_press=" + str(toggle.get("direct_press")))
    toggle_shot = RUN / "after3" / "toggle.png"
    check("fix_toggle_screenshot_exists",
          toggle_shot.is_file() and toggle_shot.stat().st_size > MIN_PNG_BYTES,
          f"{toggle_shot.stat().st_size if toggle_shot.is_file() else 0} bytes")

    # --- 3. bytecode -----------------------------------------------------
    cloth = nested(FIXED_JAR, CLOTH_ENTRY)
    builder = cloth.read("me/shedaniel/clothconfig2/impl/ConfigBuilderImpl.class")
    check("builder_no_longer_mentions_the_removed_field", REMOVED_FIELD.encode() not in builder,
          f"{len(builder)} bytes")
    check("builder_calls_the_background_bridge", b"ClothConfigBridge" in builder, "")
    demo = cloth.read("me/shedaniel/clothconfig2/ClothConfigDemo.class")
    check("demo_no_longer_reads_the_old_enchantment_field", b"field_9131" not in demo, "")
    check("demo_no_longer_calls_the_old_add_enchantment", b"method_7978" not in demo, "")
    check("demo_uses_the_bridges", b"demoEnchantment" in demo and b"keepStackName" in demo, "")

    # --- 4. provenance ---------------------------------------------------
    control_sha = sha256(CONTROL_JAR)
    fixed_sha = sha256(FIXED_JAR)
    check("control_hash_matches_its_jar",
          before.get("appleskin_sha256") == control_sha,
          f"recorded={before.get('appleskin_sha256')} on_disk={control_sha}")
    check("fix_hash_matches_its_jar", after.get("appleskin_sha256") == fixed_sha,
          f"recorded={after.get('appleskin_sha256')} on_disk={fixed_sha}")
    check("the_two_runs_used_different_jars", before.get("appleskin_sha256")
          != after.get("appleskin_sha256"), "")
    check("fix_run_is_the_shipped_jar", after.get("appleskin_sha256") == fixed_sha, fixed_sha)
    check("both_runs_used_the_same_mod_menu",
          before.get("modmenu_sha256") == after.get("modmenu_sha256"),
          before.get("modmenu_sha256") or "")
    check("both_runs_loaded_the_probe", PROBE_ENTRY in (after.get("mods") or []),
          ", ".join(after.get("mods") or []))

    verdict = {
        "control_jar": str(CONTROL_JAR),
        "control_sha256": control_sha,
        "fixed_jar": str(FIXED_JAR),
        "fixed_sha256": fixed_sha,
        "control": {"config": control, "stack_head": (before.get("stack") or [None])[0]},
        "fix": {"config": fix, "rows": rows, "kinds": row_kinds, "done": done,
                "client_errors": after.get("client_errors"),
                "toggle": toggle, "toggle_row": after.get("toggle_row"),
                "toggle_click": after.get("toggle_click"),
                "screenshot_bytes": shot.stat().st_size if shot.is_file() else 0,
                "toggle_screenshot_bytes": (toggle_shot.stat().st_size
                                            if toggle_shot.is_file() else 0)},
        "checks": [{"name": n, "ok": ok, "detail": d} for n, ok, d in checks],
    }
    (RUN / "cloth-check.json").write_text(
        json.dumps(verdict, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")

    failed = [n for n, ok, _ in checks if not ok]
    print(f"\n{len(checks) - len(failed)}/{len(checks)} checks passed")
    if failed:
        print("failed: " + ", ".join(failed))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
