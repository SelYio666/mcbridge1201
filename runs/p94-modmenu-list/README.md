# P94: Mod Menu mod list screen (passes)

Date: 2026-10-20. Follow-up to p92 (title screen).

## Result (real client)

The mod list screen now opens from the title screen and stays open:

```text
MODMENU_SCREEN_OPENED current=com.terraformersmc.modmenu.gui.ModsScreen
MODMENU_SCREEN_STABLE current=com.terraformersmc.modmenu.gui.ModsScreen
```

`STABLE` is printed 60 ticks after the screen opened; no exception, no new crash report. The earlier
attempts all aborted with hard JVM errors at different stages.

## Chain of blockers fixed (all verified in sequence)

1. **Final render overrides** — 9 `method_25394` overrides renamed to `method_48579`; a leftover
   old-named method is dropped when the class already has the new-name method (recorded as
   "dropped duplicate override").
2. **Final clickable-text override** — `method_37020` renamed to `method_47399`.
3. **EntryListWidget constructor** — `class_4280` six-argument super constructor replaced by
   `LegacyEntryListWidget` (height = bottom-top), plus the old protected geometry fields and
   `setLeftPos(int)`.
4. **Direct class_350 subclasses** — `LegacyParentWidget` for `DescriptionListWidget`.
5. **Identifier(String)** — 11 call sites through `IdentifierBridge`.
6. **TexturedButtonWidget** — `LegacyTexturedButton` keeps the 1.20.1 texture-Identifier + atlas
   constructor and re-implements the old quad+label drawing with `DrawContext.drawTexture`, because
   1.21.1 only accepts WidgetSprites (whole sprites).
7. **TextFieldWidget.tick()** — `class_342.method_1865` died in 1.20.2; 1.21.1 derives the cursor
   blink from wall-clock time, so `TextFieldTickBridge` only keeps the call site linking.

## Visual evidence (2026-10-20 update)

A screenshot was captured with the screen open (`modmenu-list.png`). It shows the Mod Menu chrome
("Toggle Filter Options", "Website", "Issues", "Open Mods Folder", "Done") and a probe reading
`MODMENU_LIST items=8`, i.e. the list data exists.

**The list rows themselves are not drawn**: the list area is black. This is a real visual defect, not
just the missing panorama/asset noise (the magenta checkerboard is the missing-texture background
that this machine already shows elsewhere). Likely cause: the converted `ModListWidget` render body
still derives row/scroll geometry from 1.20.1 list fields, while 1.21.1 lays entries out through its
own selection-list state.

## Scope

- Verified: the screen initialises, ticks and renders for at least 60 ticks with no exception and no
  crash report; a screenshot was captured.
- Not verified: the list rows are invisible (see the visual evidence above); scrolling, search input
  and opening a mod's config were not tested.
- Textured buttons draw with the original texture atlas because the old drawing was re-implemented,
  but their hover/pressed states were not compared pixel by pixel with 1.20.1.

## Evidence

`client.log` — the successful run (OPENED + STABLE, no errors). The previous crash logs remain in
this directory as history of the blocker chain.
