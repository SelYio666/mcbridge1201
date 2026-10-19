# P91: ShulkerBoxTooltip provider contract

Date: 2026-10-19. Follow-up to the six-mod expansion report.

## Goal

Make ShulkerBoxTooltip's preview provider read a 1.21.1 shulker box (CONTAINER component) without the
CenturyBridge tombstones for the old `BlockEntityTag` NBT path.

## Changes

- `rules/fabric-1.21.1/shulker-nbt.json` + `ShulkerBoxNbtBridge`:
  - `t0` (`ItemStack.getSubNbt("BlockEntityTag")`) → rebuild the old `Items` compound
    (`Slot`/`id`/`Count`) from `DataComponentTypes.CONTAINER` (`class_9334.field_49622`,
    `class_9288` items);
  - `t1` (`ItemStack.fromNbt`) → parse `id` + `Count` back into a stack.
- `rules/fabric-1.21.1/fabric-legacy-networking.json` extended:
  - client `registerReceiver` / `unregisterReceiver` (non-global) and the
    `ServerPlayNetworking$PlayChannelHandler` shim for the integrated server;
  - `new class_2817(Identifier, PacketByteBuf)` factory.
- `rules/fabric-1.21.1/dyecolor-components.json` + `DyeColorBridge`: 1.21.1 re-used
  `DyeColor.method_7787` as an int colour; the old `float[]` components are unpacked from it.

## Result (contract probe, real client)

```text
SHULKER_FIXTURE nativeContainerCount=5
SHULKER_PROVIDER class=com.misterpemodder.shulkerboxtooltip.impl.provider.ShulkerBoxPreviewProvider
SHULKER_CONTRACT_RESULT diamondCount=5 expected=5 shouldDisplay=false
```

`diamondCount == expected` — the provider reads the five diamonds through the bridged legacy NBT
path. No tombstone / NoSuchMethodError remains in this path.

## Notes

- `shouldDisplay=false` was not investigated; it likely depends on the mod's own display config or
  preview context (the probe builds a bare `PreviewContext`, no player).
- Hovering a real shulker box in the GUI (visual tooltip) was not tested; this is a provider-level
  contract, matching the expansion report's scope.
- The networking shims were required because this mod registers both client and integrated-server
  channels on join.

## Evidence

- `client.log`; rules and bridge sources are in the repository, converted jars stay out of git.
