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

### Root cause found later: the hovered stack has the container *removed*

Printing the hovered stack's full component map gave:

```text
SBT_MAP {!minecraft:container}
```

`!minecraft:container` is a component **removal marker**: that particular stack was patched to have
no container at all.

### Deeper: even a fresh player and a minimal mod set see an empty component

Repeated with a brand-new username (empty inventory) and only Fabric API + the patched Shulker mod
+ this companion + the hover probe:

```text
inv0 (server) => components: {"minecraft:container": [{item: {count: 5, id: "minecraft:diamond"}, slot: 0}]}
SBT_MAP {!minecraft:container}
SBT_ITER raw1=0 raw2=0 head=none stream1=0 stream2=0
```

The server-side item has the contents, but the client-side `ContainerComponent` exposes **zero
slots** through every accessor (`method_57489`, `method_59712`, `method_59714`). The provider is
therefore right to report an empty inventory; nothing in the converted mod's preview code can fix an
empty component.

This is outside the converter's scope (component contents differ between server data and the client
stack). A future run should compare the raw slot-update packet with the server stack, or reproduce
with a vanilla-only client and the same command.

### Vanilla control (no Shulker, no companion)

A minimal inventory probe with only Fabric API reads the stack after the same RCON give:

```text
item replace FreshHover10 hotbar.0 ... => Replaced a slot on FreshHover10 with [Shulker Box]
inv0 (server) => components: {"minecraft:container": [{item: {count: 5, id: "minecraft:diamond"}, slot: 0}]}
INV0 item=minecraft:shulker_box map={!minecraft:container} comp=raw=0 nonAir=0
```

**The vanilla-only client sees the same empty container**: map in removal form, zero slots. (An
earlier probe run printed a normal map value, but that was a stack restored from player data, not a
freshly given one.)

So this is not caused by the converted mod or the companion. The environment's client stack for a
command-created container item exposes an empty/removed container component while the server-side
NBT is correct. Reproducing on a stock 1.21.1 client+server with `/item replace` is the next step;
until then the grid preview cannot be tested at all in this harness.

## Honest status

**Grid preview is not restored in this run.** The companion mixin, the builder and the NBT compat
rule are in place and apply correctly; the blocker is a client-side container-component discrepancy
between the server stack and the stack the tooltip path sees. Recording it here avoids claiming a
visual win that did not happen; this line is parked until a packet-level comparison is done.

## p186 follow-up (partial)

`runs/p186-shulker-grid-client-item/` re-opened this with a **client-side** shulker box carrying a
real `ContainerComponent`: `SBT_ITER raw1=1 head=minecraft:diamondx5` proves the component is not
empty. A companion `ComponentPreviewProvider` wrapper (reads the component directly) plus t2/t4
bridges (`ItemStack.getNbt` `method_7969` → `legacyNbt`, `setNbt` → no-op) let the grid renderer
reach the tooltip: `SBT_WRAP show=true inv=27 nonAir=1` and the `grid.png` preview frame with
`Diamond ×5`. Still open: the item icons inside the grid slots are not drawn, and a **real server
item** (the `/item replace` stack) still shows `!minecraft:container` on the client. So the render
path is partially restored, but the original server-sync blocker is not fixed.

## Evidence

`grid-window.png` (hover without grid), `server.log` (join/give), and the SBT debug lines in the
client log of the run.
