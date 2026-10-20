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

Root cause found in two steps:

1. The wildcard `render-widget-override` rename had also renamed `ModsScreen.render`
   (`method_25394`) to `method_48579`, so the whole screen render body was silently disabled. The
   rule now excludes direct `class_437` subclasses.
2. With the screen render restored, the list body reached `ModListWidget.method_25311` /
   `DescriptionListWidget.method_25394`, which draw through removed RenderSystem/Shader calls
   (`Tombstones_modmenu_7_2_2.t1`, `class_289.method_1349`). Those cannot be forwarded, so a new
   `bodyRedirects` rule replaces both method bodies with `ModMenuListRenderBridge.renderList`: it
   paints a plain translucent row background with `DrawContext` and calls each entry's unchanged
   `Entry.method_25343` hook.

The screenshot now shows the mod list rows (icons, names, description panel, scrollbar). Remaining
visual noise: the magenta/black checkerboard is the missing-texture background this machine already
shows for other screens, and the list backdrop is the simplified translucent fill (recorded
degradation instead of the old shader gradient).

## Scope

- Verified: the screen initialises, ticks and renders for at least 60 ticks with no exception and no
  crash report; a screenshot was captured.
- Verified: list rows render (icons/names/description/scrollbar visible in the screenshot).
- Not verified: scrolling, search input and opening a mod's config were not tested; the row backdrop
  is simplified and the magenta checkerboard comes from the machine's missing assets.
- Textured buttons draw with the original texture atlas because the old drawing was re-implemented,
  but their hover/pressed states were not compared pixel by pixel with 1.20.1.

## Evidence

`client.log` — the successful run (OPENED + STABLE, no errors). The previous crash logs remain in
this directory as history of the blocker chain.
