# P96: Combined mod smoke test

Date: 2026-10-20.

## Setup

One client, one quickplay world, all patched mods installed together:

- AppleSkin 2.5.2 (converted + food/status-effect/networking/identifier bridges)
- Mod Menu 7.2.2 (converted + title/list adapters)
- ShulkerBoxTooltip 4.0.4 (converted + NBT/networking/ender-chest/dye bridges)
- TrashSlot, IronChests (model bridge), Lithium (final), plus Balm and Fabric API

The probe waits until a world is loaded, logs `COMBINED_SMOKE in-world` and saves
`combined-world.png`.

## New blockers found by the combination

The individual runs were green, but loading several patched jars together exposed three more
ShulkerBoxTooltip paths:

1. `ClientPlayNetworkHandler.sendPacket(Packet)` (`class_634.method_2883`) was tombstoned; the C2S
   handshake threw. Bridged to `handler.getConnection().send(packet)`.
2. `PacketByteBuf.writeNbt(NbtCompound)` no longer matches (1.21.1 widened it to `NbtElement`);
   bridged to `writeNbt(NbtElement)`.
3. Ender-chest sync used the 1.20.1 `EnderChestInventory.writeNbt()/readNbt(NbtList)`; 1.21.1 needs
   a `RegistryOps`. Both directions are bridged with `Slot/id/Count` serialisation, the same shape
   the mod's own receiver expects.

Also a deployment trap: **every patched jar embeds its own copy of the bridge classes**, and the
first copy loaded wins. A stale AppleSkin jar without `sendPacket` shadowed the new Shulker bridge.
All patched jars must be regenerated against the same `--bridge-dir` after a bridge change.

## Result

Final combined run:

```text
COMBINED_SMOKE in-world player=literal{TestPlayer}
```

No tombstone, NoSuchMethodError, Unreported exception, or crash report after the fixes; the
screenshot shows the world with the HUD and hotbar.

## Scope

- This is a load/join smoke test, not a gameplay acceptance of every mod.
- Shulker's ender-chest sync is re-serialised by the bridge (Slot/id/Count); NBT components beyond
  item id/count are not carried by that path.

## Evidence

`client.log`, `combined-world.png`.
