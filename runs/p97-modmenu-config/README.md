# P97: Mod Menu configuration screen

Date: 2026-10-20. Follow-up to p94 (mod list).

## Goal

Open a mod's configuration screen from Mod Menu's list (here: Mod Menu's own options screen),
which exercises the options-list widget and screen background paths.

## Blockers fixed

1. **OptionsList constructor** — 1.20.1 `OptionsList(client,width,height,top,bottom,itemHeight)`
   became `(client,width,OptionsSubScreen parent)`. `ModMenuOptionsListBridge.create` takes the
   parent from `client.field_1755` (the options screen is already current while it builds the list).
2. **`render-widget-override` mis-renaming screens** — `ModMenuOptionsScreen` extends
   `OptionsSubScreen` (`class_4667`), not `class_437` directly, so the exclusion list did not cover
   it and its `render` was renamed away. `excludeSuper` now accepts a comma-separated list and the
   rule excludes both `class_437` and `class_4667`.
3. **Old `renderBackground(DrawContext)`** — `ModMenuOptionsScreen.method_25434(class_332)` is
   forwarded to `class_437.method_25420(ctx,0,0,0)` through the same bridge used for ModsScreen.

## Result

Probe: `ModMenu.getConfigScreen("modmenu", currentScreen)` opens
`com.terraformersmc.modmenu.gui.ModMenuOptionsScreen`.

```text
MODMENU_CONFIG id=modmenu class=com.terraformersmc.modmenu.gui.ModMenuOptionsScreen
MODMENU_CONFIG_LIST items=10 w=342 h=190 y=33 rowTop0=37
```

The screenshot shows the options screen with ten option rows and the Done button. No tombstone,
NoSuchMethodError, or new crash report.

## Scope

- This is Mod Menu's own config screen; other mods' Cloth-Config-based screens were not opened.
- The option labels look blurry in the screenshot; this machine already shows blurry/missing GUI
  assets elsewhere (magenta checkerboard), so it is treated as an environment/asset issue, not a
  failing conversion. Individual toggles were not interacted with.

## Evidence

`client.log`, `modmenu-config.png`.
