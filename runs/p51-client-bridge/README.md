# P51: ResourcefulLib client networking bridge — main entrypoint now passes

Date: 2026-10-19 (Asia/Shanghai). Follow-up to P50.

## Bridge

Replaced nested ResourcefulLib 2.0.6's
`com.teamresourceful.resourcefullib.common.networking.fabric.FabricClientPacketHelper` with a
1.21.1 implementation:

- old `clientOnlyRegister(Identifier, PacketHandler)` creates a `CustomPayload` id, registers a
  payload codec for S2C/C2S, and registers a `PlayPayloadHandler` that decodes the raw bytes with
  the original ResourcefulLib `PacketHandler`;
- old `sendToServerClientOnly(Identifier, Packet)` encodes with the original handler and sends a
  `CustomPayload`;
- the old `PacketHandler` / `Packet` / `PacketContext` classes are kept from ResourcefulLib 2.0.6.

Source: `FabricClientPacketHelper.java`; compile log: `compile.log`.

## Result

The client now gets past `ironchests` **main** entrypoint. Fabric loads all mods, then fails at the
**client** entrypoints:

```text
Could not execute entrypoint stage 'client' ... 'ironchests' at IronChestsFabricClient
Caused by: NoClassDefFoundError:
  net/fabricmc/fabric/api/client/model/ModelLoadingRegistry
```

and, suppressed:

```text
NoSuchMethodError: void net.blay09.mods.balm.api.client.BalmClient.initialize(
    java.lang.String, java.lang.Runnable)
  at trashslot...FabricTrashSlotClient.onInitializeClient
```

So the ResourcefulLib legacy networking bridge works; the next two client blockers are:

1. ironchests' old `ModelLoadingRegistry` model-provider path (1.21.1 uses `ModelLoadingPlugin`);
2. trashslot's old `BalmClient.initialize(String,Runnable)` (Balm 21 needs a
   `BalmRuntimeLoadContext`, like the server-side `Balm.initialize` bridge).

Neither is a pass; no client profile status is upgraded.

## Next

- Add `BalmClientInitializeBridge` and a trashslot client call-site rule.
- Port ironchests' model provider to `ModelLoadingPlugin` (or a model-loading bridge) rather than
  stubbing it; skipping it would break chest rendering.
- Then re-run to find the next client-only blocker.

## Evidence

- `client.log`, `crash-report.txt`, `FabricClientPacketHelper.java`, `compile.log`, `launch.pid`
