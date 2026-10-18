# P53: world join gets past Balm payload encoding, then lithium tombstone

Date: 2026-10-19 (Asia/Shanghai). The payload blocker is fixed; a new lithium blocker appears.

## Fix

The old Balm 1.20.1 writer is `BiConsumer<T, FriendlyByteBuf>` (packet first, buffer second), not
buffer first. `BalmNetworkingBridge` now calls `writer.accept(value, buf)`. This removed the
`ClassCastException: class_9129 -> MessageTrashSlotContent` from the `trash_slot_content`
clientbound payload.

## Result

The client can now log in and starts generating the world. The next failure is a **lithium**
tombstone during world generation:

```text
UnsupportedOperationException:
  CenturyBridge tombstone: net.minecraft.class_2540.method_10815 no longer exists in 1.21.1
  at centurybridge.gen.Tombstones_lithium_fabric_mc1_20_1_0_11_4.t2
  at me.jellysquid.mods.lithium.common.world.chunk.LithiumHashPalette.method_12290
  at ...PalettedContainer...
```

`method_10815(I)I` is the 1.20.1 `FriendlyByteBuf.getVarIntSize(int)`; 1.21.1 moved this to
`VarInt.getByteSize(int)`. The server-side world stress used an existing world and did not
exercise this palette serialization path, so this is a new real client/world-generation blocker.

## Status

- client main menu: reached
- world join / payload: **passes**
- world generation: **blocked on lithium `method_10815`**
- trash GUI / persistence / two-client: not executed

## Next

- Add a lithium call-site bridge for the tombstone `t2(I)I` → `VarInt.getByteSize(int)` (needs the
  intermediary name of `net.minecraft.network.VarInt`) or an equivalent local implementation.
- Then retry world generation; expect further client-only issues.

## Evidence

- `crash-report.txt`, `latest.log`, `client.log`
