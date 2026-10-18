# P52: client reaches the main menu, then fails on Balm payload encoding

Date: 2026-10-19 (Asia/Shanghai). First client boot with all five mods loaded.

## Installed client

- PCL home: `D:\我的世界\.minecraft`
- base 1.21.1 + Fabric Loader 0.19.5 (`fabric-loader-0.19.5-1.21.1`)
- Java: PCL's Microsoft Java 21
- mods: Fabric API 0.102.0, Balm 21.0.66, lithium P13, ironchests P26, trashslot P29

The client **loaded all mods and reached the main menu** (screenshot `main-menu.png`). The magenta
background is a missing panorama asset (asset index 17 was not fully populated), not a crash.

## Client-side bridges applied in this experiment

1. **ResourcefulLib networking** (P51): replaced nested 2.0.6
   `FabricClientPacketHelper` with 1.21.1 `CustomPayload` coding.
2. **Balm client initializer**: added `BalmClientInitializeBridge` +
   `trashslot.balm.client-initialize-context`; old
   `BalmClient.initialize(String,Runnable)` → `BalmClient.initialize(String, EmptyLoadContext, Runnable)`.
3. **ironchests model loading**: work-only replacement of `IronChestsFabricClient` using
   `ModelLoadingPlugin` and the same locked/unlocked/chest lid/base model ids.
4. **Balm `sendTo`**: added `BalmNetworkingBridge.sendTo` + `trashslot.balm.send-to`; this removed
   the earlier `NoSuchMethodError`.

## Current failure

Creating/joining the world triggers trashslot's login sync; the server disconnects with:

```text
EncoderException: Failed to encode packet 'clientbound/minecraft:custom_payload'
  (trashslot:trash_slot_content)
Caused by: ClassCastException:
  class net.minecraft.class_9129 cannot be cast to
  class net.blay09.mods.trashslot.network.MessageTrashSlotContent
  at top.mcbridge1201.bridge.BalmNetworkingBridge.lambda$codec$2
```

The `Payload` wrapper/codec is receiving/sending the `RegistryFriendlyByteBuf` where the packet
object is expected. The next fix is in the bridge codec/value wiring (not in trashslot), then the
world join can be retried.

## Status

- **Client main menu: reached** with all mods loaded.
- **World join: not reached** (payload encode failure).
- **Trash GUI / clientbound delivery / persistence / two-client sync: not executed.**
- These are work-only patches; only the Balm client initializer and `send-to` rule are in the
  repository. The ResourcefulLib and ironchests class replacements still need a general
  class-replacement rule before this is reproducible from the repo alone.

## Evidence

- `main-menu.png`, `focused.png`, `world-create.png`
- `latest.log`, `crash-report.txt`
- `IronChestsFabricClient.java`
- `build-bridges*.log`, `patch*.log`, `launch*.pid`
