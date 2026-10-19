# P67: IronChests sync NBT ported; next blocker is ResourcefulLib's raw networking

Date: 2026-10-19 (Asia/Shanghai). Continues P66 (model shim fixed the render crash).

## What was fixed

Two call-site redirects, both verified by the patch report (`patch.log`):

| rule | call site | hits |
|---|---|---|
| `ironchests.sync.write-tag` | `GenericChestBlockEntity.getSyncTag` → `method_11007(NbtCompound)` | 1 |
| `ironchests.sync.read-tag` | `GenericChestBlockEntity.loadSyncTag` → `method_11014(NbtCompound)` | 1 |
| `nbt.packet.write-nbt-compound` | `PacketByteBuf.method_10794(NbtCompound)` | 1 |

- The converted class kept 1.20.1 one-argument `readNbt`/`writeNbt` calls. Because both share the same
  descriptor, the conversion had also **swapped** them: `getSyncTag()` called the read method and
  `loadSyncTag()` called the write method. `IronChestsNbtBridge` restores the intended direction
  (`getSyncTag` → two-arg `writeNbt`, `loadSyncTag` → two-arg `readNbt`) using the level's
  `RegistryAccess` as the `HolderLookup.Provider`.
- `NbtPacketBridge` widens `PacketByteBuf.writeNbt(NbtCompound)` to 1.21.1's
  `method_10794(NbtElement)`.

After these, the chest-open path runs past both old errors:

```text
IRONCHESTS_STATE=Block{ironchests:iron_chest}[facing=north,lock=no_lock,open=false,waterlogged=false]
IRONCHESTS_USE_ERROR cause=java.lang.NoSuchMethodError:
  'void net.fabricmc.fabric.api.networking.v1.ServerPlayNetworking.send(
       net.minecraft.class_3222, net.minecraft.class_2960, net.minecraft.class_2540)'
```

## Next blocker: ResourcefulLib 2.0.6 raw channel networking

Full stack (`latest-rl2.log`):

```text
at com.teamresourceful.resourcefullib.common.networking.fabric.PacketChannelHelperImpl.sendToPlayer
at com.teamresourceful.resourcefullib.common.networking.PacketChannelHelper.sendToPlayer
at com.teamresourceful.resourcefullib.common.networking.NetworkChannel.sendToPlayer
at com.teamresourceful.resourcefullib.common.networking.NetworkChannel.sendToAllLoaded
at tech.thatgravyboat.ironchests.common.blocks.SyncableData.sync
at tech.thatgravyboat.ironchests.common.blocks.GenericChestBlockEntity$1.method_31681
at net.minecraft.class_5561.method_31684
at tech.thatgravyboat.ironchests.common.blocks.GenericChestBlockEntity.method_5435
at tech.thatgravyboat.ironchests.common.blocks.GenericChestMenu.<init>
```

IronChests ships ResourcefulLib as a nested JiJ jar
(`META-INF/jars/resourcefullib-fabric-1.20-2.0.6.jar`), and that 1.20.1 build sends raw buffers
through the Fabric channel API that 1.21.1 removed.

## Replacing the library is not an option

Installing the 1.21.1 ResourcefulLib 3.0.12 and dropping the nested 2.0.6 makes the game fail at
startup (`crash-rl3.txt`):

```text
NoClassDefFoundError: com/teamresourceful/resourcefullib/common/networking/base/PacketHandler
at tech.thatgravyboat.ironchests.IronChests.init(IronChests.java:18)
```

So 3.x is API-incompatible with IronChests 5.0.2 and the **nested 2.0.6 must be ported** (or its
Fabric networking shim bridged) instead of swapped.

## Next step

Bridge ResourcefulLib 2.0.6's raw Fabric networking onto 1.21.1 payloads — the same shape as
`BalmNetworkingBridge`, but for raw buffers:

- `ServerPlayNetworking.send(ServerPlayer, Identifier, PacketByteBuf)`
- `ClientPlayNetworking.send(Identifier, PacketByteBuf)`
- `ServerPlayNetworking.registerGlobalReceiver(Identifier, handler)`
- `ClientPlayNetworking.registerGlobalReceiver(Identifier, handler)`

Each channel id needs a `CustomPayload` type carrying the raw bytes plus a receiver that rebuilds a
`PacketByteBuf` and invokes the mod's handler.

## Status

| step | result |
|---|---|
| IronChests client model | fixed (P66 shim, work-only) |
| chest block placement | pass |
| block-entity sync NBT | **fixed (2 rules + packet widening)** |
| chest menu open | blocked by ResourcefulLib raw networking |
| GUI screenshot | not yet |

## Evidence

- `latest-rl2.log`, `crash-rl3.txt`, `patch.log`
- `IronChestsNbtBridge.java`, `NbtPacketBridge.java`, `ironchests-nbt.json`, `nbt-packet.json`

## Correction (P70)

This page's first NBT bridge direction was **wrong**. The converted class swapped the method
**bodies**, not the call sites: `method_11007` writes the inventory into the tag, `method_11014`
clears and reads it. The bridge here called `method_11014` for `getSyncTag`, so every chest open ran
the read path with an empty tag and wiped the contents. P70 swaps the bridge calls and proves the
close/reopen persistence (`runs/p70-ironchests-persist/`).
