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
that this machine already shows elsewhere).

Latest diagnostics (probe, tick 260):

```text
MODMENU_LIST items=8 w=163 h=153 scroll=0.0 row0Visible=true rowTop0=71
```

So the list has eight entries, the scroll amount is 0, the first row's top is at y=71 and the
widget's own visibility test says the row is visible. Geometry therefore looks sane, yet nothing is
painted.

Prime suspect: `ModListWidget.method_25311` (the overridden list render body) starts with
`RenderSystem.getShader()` and then calls the **unbridged** tombstone
`Tombstones_modmenu_7_2_2.t1(class_289)`, which throws
`UnsupportedOperationException: class_289.method_1349 no longer exists in 1.21.1`.
Its sibling tombstones `t2`/`t3`/`t4` are also still unbridged. No tombstone exception appears in the
log, which means this render body is apparently not being reached at all — that contradiction is the
next thing to resolve (verify whether `ModListWidget.method_25311` is called, and bridge or replace
the `t1`–`t4` RenderSystem/Shader/VertexConsumer calls).

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
