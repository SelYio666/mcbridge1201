# P110: Shulker grid preview attempt (unfinished)

Date: 2026-10-20.

## Goal

Restore the full grid preview that the conversion lost when it stripped ShulkerBoxTooltip's
`ItemStack` mixins (see P100/P107).

## What was built

- `java/src/shulkerpreview/` + `tools/build_shulker_preview_companion.py`: a companion mod that
  mixes into `ItemStack.getTooltipData()` (`method_32347`) and returns the mod's own
  `PreviewTooltipData`, using the public API (`PreviewProviderRegistry`, `PreviewContext`,
  `PreviewProvider.shouldDisplay/getInventory`). The mod's `HandledScreenMixin` (still active) then
  draws the preview.
- `rules/fabric-1.21.1/shulker-nbt.json` gained `shulker.nbt-list-contains`
  (`NbtListCompatBridge`): 1.20.1 code tests `NbtCompound.contains(key, 9)` for "is a list" and
  `contains(key, 99)` for "is a number"; 1.21.1 changed those checks, so the bridge restores the old
  meaning. It applies to 11 call sites.

## Where it stops

The companion is called (mixin applies, provider found, `PreviewTooltipData` path reachable), but the
provider reports an empty inventory:

```text
SBT_COMPONENT net.minecraft.class_9288@... item=minecraft:shulker_box count=1 items=list:0
SBT_ITER iter=0 stream1=0 stream2=0
SBT_PREVIEW provider=ShulkerBoxPreviewProvider show=false inv=27 nonAir=0
```

The server-side item really has contents
(`data get entity TestPlayer Inventory[0]` shows
`"minecraft:container": [{item: {count: 5, id: "minecraft:diamond"}, slot: 0}]`), and the client
stack does carry a `ContainerComponent`, yet all three vanilla accessors
(`method_59714()` iterable, `method_57489()` stream, `method_59712()` stream) return no non-empty
stack on the client. The synthesized legacy `BlockEntityTag.Items` therefore stays empty and
`shouldDisplay` is false.

## Honest status

**Grid preview is not restored.** The remaining gap is client-side container-component visibility in
this setup, not the mixin wiring. Next hypotheses:

1. the hovered stack is not the server-given one (hotbar mapping or an older client-side stack),
2. a component-parse difference between network sync and RCON-created components,
3. another wrapper in the mod's inventory path that our bridge does not cover.

Recording it here avoids claiming a visual win that did not happen. The companion sources, builder
and the NBT compat rule stay in the repo as groundwork; they are not part of any verified mod claim.

## Evidence

`grid-window.png` (hover without grid), `server.log` (join/give), and the SBT debug lines in the
client log of the run.
