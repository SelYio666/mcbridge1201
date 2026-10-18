# P16: Balm initializer call-site bridge works; networking API still blocks trashslot

Date: 2026-10-18 (Asia/Shanghai). This continues P15 with native Balm 21.0.66 for 1.21.1.

## What was adapted

TrashSlot 15.1.5 calls the old `Balm.initialize(String, Runnable)`. Native Balm 21 replaced it
with `initialize(String, BalmRuntimeLoadContext, Runnable)`. A call-site bridge
(`BalmInitializeBridge`) supplies `EmptyLoadContext.INSTANCE`:

```java
Balm.initialize(modId, EmptyLoadContext.INSTANCE, initializer);
```

The rule `trashslot.balm.initialize-context` matches exactly:
`net/blay09/mods/balm/api/Balm.initialize(Ljava/lang/String;Ljava/lang/Runnable;)V` -> bridge.
Patch applied 1 time; the previous `NoSuchMethodError: Balm.initialize(String,Runnable)` is gone.

## Next failure

`server-balm2.log`:

```text
NoSuchMethodError: void net.blay09.mods.balm.api.network.BalmNetworking.registerServerboundPacket(
  net.minecraft.class_2960, java.lang.Class, java.util.function.BiConsumer,
  java.util.function.Function, java.util.function.BiConsumer)
  at net.blay09.mods.trashslot.network.ModNetworking.initialize(ModNetworking.java:12)
```

Balm 21's networking API is payload-based:

```java
registerServerboundPacket(PacketType<T>, Class<T>, StreamCodec<RegistryFriendlyByteBuf,T>,
                          BiConsumer<ServerPlayer,T>)
```

or a default overload with `BiConsumer<RegistryFriendlyByteBuf,T>` +
`Function<RegistryFriendlyByteBuf,T>`. The old API keyed packets by `Identifier` and had no
`PacketType`/`StreamCodec`; this is a **networking protocol shape change**, not a descriptor
that can be bridged by passing a context. A real adapter would need to create a
`CustomPayload`/`PacketType` + codec for each trashslot packet and register it with the new
Fabric networking API.

## Result

No `Done`; `doneSeen=false`, runner exit 11. The trashslot NBT bridges + Balm initializer bridge
are prepared and the initializer bridge is verified to advance the boot, but the overall sample
is still **not boot-verified**. Do not mark trashslot as passed.

## Commands / logs

```powershell
python tools/build_bridges.py --stub work/cb/data/jars/client-1.21.1-intermediary.jar `
  --lib <gson> --lib <datafixerupper> --lib work/corpus/deps/balm-fabric-1.21.1-21.0.66.jar `
  --lib work/target/fabric-api-0.102.0+1.21.1.jar --lib <netty-buffer> --lib <netty-common> `
  --out work/bridges
mcbridge1201 patch --in work/cb/out/trashslot/trashslot-fabric-1.20.1-15.1.5+1.21.1.jar `
  --out work/cb/out/trashslot/trashslot-patched-balm.jar `
  --rules rules/fabric-1.21.1/trashslot.json --bridge-dir work/bridges
python tools/inject_aw.py --jar ... --out ...-aw.jar --aw rules/fabric-1.21.1/mcbridge.accesswidener
python tools/run_server.py --instance work/instances/fabric-1.21.1-server-trashslot `
  --log runs/p16-balm/server-balm2.log --timeout 240
```

Hashes (SHA-256):

| Artifact | SHA-256 |
|---|---|
| `trashslot-patched-balm.jar` | `f1fe52ff3d5af3b590bb538f559f930384afe891740f9d244b7006552e40f99d` |
| `trashslot-patched-balm-aw.jar` | `89ec3d7263d2ffc99c85317283cf410b21e5731f7416066f1f2ad766952d5339` |
| `server-balm2.log` | `e22860d949d2938d91108cd2f2fabc37a4de1ec9c2d598174d3bb4cb09dde5f6` |
| `patch.log` | `a49d99ead24860705642b425897e885c30f037dfe9f45fdfab0e62861cce849e` |

## Next step

Implement a Balm networking adapter (PacketType + StreamCodec + Fabric payload registration)
or use a Balm build whose networking API still accepts `Identifier` + byte-buf lambdas.
