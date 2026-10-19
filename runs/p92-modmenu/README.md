# P92: Mod Menu title screen (private field + final render)

Date: 2026-10-19. Follow-up to the six-mod expansion report.

## Blockers

1. `IllegalAccessError: private field class_442.field_32271` in
   `ModMenuEventHandler.shiftButtons` — 1.21.1 made the Realms-button text private.
2. After that, `IncompatibleClassChangeError: ModMenuButtonWidget overrides final method
   class_339.method_25394` — 1.21.1 moved the override point from `render` (now final) to the
   protected `renderWidget` (`class_4264.method_48579`).

## Changes

- `ModMenuTitleScreenBridge` + `fieldRedirects` in `modmenu-title-screen.json`: reads
  `class_442.field_32271` reflectively for the label comparison.
- New rule type **`methodRenames`** (`RuleSet` + `JarPatcher` + `Main` merge):
  renames `ModMenuButtonWidget.method_25394(DrawContext,IIF)V` to `method_48579` and rewrites the
  `invokespecial class_4185.method_25394` super call to `method_48579`, so the update-badge drawing
  keeps working instead of being deleted.

## Result (real client, main menu)

- no `IllegalAccessError`, no `IncompatibleClassChangeError`, no new crash report;
- Mod Menu loads (`- modmenu 7.2.2`) and the title screen renders; the remaining title-screen log
  stack is the same missing-asset noise seen for other mods on this machine;
- the mod list screen itself was not opened/asserted.

## Note

The first patch attempt silently did nothing because `Main.patch` merged only a subset of rule
lists; `methodRenames` was missing from that merge. Fixed in the same commit.

## Evidence

- `client.log`; patched jar and converted jars stay out of git.
