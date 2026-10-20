# P94: Mod Menu mod list screen (in progress)

Date: 2026-10-20. Follow-up to p92 (title screen).

## Goal

Open Mod Menu's actual mod list (`ModsScreen`) instead of only checking the title screen.

## What now works (verified in real client)

Each of these used to abort the screen with a hard JVM error; after the fixes the next stage is
reached, so the list gets further on every round:

1. **Final render overrides** — 9 `method_25394` overrides renamed to `method_48579` (generic
   `render-widget-override` rule, wildcard owner). A leftover old-named method is dropped when the
   class already has the new-name method (recorded as "dropped duplicate override").
2. **Final clickable-text override** — `method_37020` renamed to `method_47399` (new override hook).
3. **EntryListWidget constructor** — `class_4280` six-argument super constructor replaced by the
   `LegacyEntryListWidget` bridge (width, height, bottom-top, top, itemHeight), plus the old
   protected geometry fields and `setLeftPos(int)`.
4. **Direct class_350 subclasses** — `LegacyParentWidget` bridge for classes such as
   `DescriptionListWidget` that extend `class_350` directly.
5. **Identifier(String)** — 11 call sites redirected through `IdentifierBridge`.

## Current blocker

The list now fails at `TexturedButtonWidget` (class_344) construction:

```text
NoSuchMethodError: 'void net.minecraft.class_344.<init>(int, int, int, int, int, int, ..., class_2960, ...)'
```

1.20.1 passed a texture `Identifier` plus atlas `u/v/texWidth/texHeight`; 1.21.1 takes a
`WidgetSprites` (class_8666). Mapping the sub-region form to `WidgetSprites` changes how the button
texture is drawn, so it was deliberately not guessed in this round.

## Scope

- Title screen remains verified (p92). The mod list itself is **not** yet verified; do not claim it.
- The engine additions (wildcard `methodRenames` with duplicate handling, `superclassReplacements`)
  are general and are also useful for other converted mods.

## Evidence

`client.log` — final attempt, showing the class_344 blocker after the earlier stages were passed.
