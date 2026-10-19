# P89: legacy Fabric networking bridge (AppleSkin / FallingTree)

Date: 2026-10-19. Follow-up to the six-mod expansion report.

## What was added

- `java/src/bridge/java/top/mcbridge1201/bridge/FabricLegacyNetworking.java`:
  - `registerClientReceiver(Identifier, Object)` — registers a raw payload type and invokes the
    legacy handler's `receive(client, networkHandler, buf, sender)`;
  - `createClientPacket(Identifier, PacketByteBuf)` — factory for the old
    `new CustomPayloadC2SPacket(Identifier, PacketByteBuf)`;
  - `sendToPlayer(ServerPlayer, Identifier, PacketByteBuf)` — old
    `ServerPlayNetworking.send(player, id, buf)`.
- `java/src/bridge-shim/java/.../ClientPlayNetworking.java`: the deleted
  `ClientPlayNetworking$PlayChannelHandler` interface (only the nested class is embedded; the outer
  class is never shipped, so the real Fabric API class is not shadowed).
- `java/src/bridge/java/.../IdentifierBridge.java` + `rules/fabric-1.21.1/identifier-single-arg.json`:
  the removed `new Identifier(String)` constructor (8 sites in AppleSkin, 2 in FallingTree).
- `rules/fabric-1.21.1/fabric-legacy-networking.json`: call-site redirects for the two old
  networking signatures plus the old C2S packet constructor.
- `RuleSet`/`JarPatcher`: `extraBridgeClasses` lets a rule embed API shims alongside its bridge.
- `tools/build_bridges.py`: compiles the shim separately and copies only the nested class.

## Runtime results

**AppleSkin 2.5.2** (converted + patched, launched in the real client):

1. previous `NoClassDefFoundError ClientPlayNetworking$PlayChannelHandler` at init — **gone**;
2. previous `NoSuchMethodError class_2658.<init>(Identifier, PacketByteBuf)` in
   `SyncHandler.makeSyncPacket` — **gone**;
3. next real blocker: HUD rendering reaches a CenturyBridge tombstone in
   `squeek.appleskin.helpers.FoodHelper.isFood` (old item food API) —
   `at centurybridge.gen.Tombstones_appleskin...t0` (see `client.log`).

**FallingTree 4.3.4** (converted + patched, launched in the real client):

- previous init `NoClassDefFoundError` — **gone**; the client starts with no new crash report
  (`fallingtree-client.log`). The server-side `send` redirect is applied to the jar
  (`fabric.legacy.server-send applied 1 time(s)`) but the join-time path was not re-run here.

## Food bridge (second pass)

`rules/fabric-1.21.1/appleskin-food.json` + `AppleSkinFoodBridge` replace the five tombstones the
converter emitted for 1.20.4-era Item/FoodComponent getters:

| tombstone | old member | bridge |
|---|---|---|
| `t0` | `Item.isFood` | `new ItemStack(item).get(DataComponentTypes.FOOD, null) != null` |
| `t1` | `Item.getFoodComponent` | `get(FOOD, null)` |
| `t2` | `FoodComponent.isAlwaysEdible` | `comp_2493()` |
| `t3` | `FoodComponent.getHunger` | `comp_2491()` |
| `t4` | `FoodComponent.getSaturationModifier` | `comp_2492()` |

Runtime: the previous `UnsupportedOperationException` tombstone in `FoodHelper.isFood` is **gone**;
the client stays in the singleplayer world and the only remaining AppleSkin-related line is a
missing vanilla texture:

```text
[22:57:00] [Render thread/WARN]: Failed to load texture: minecraft:textures/gui/icons.png
```

That path is a vanilla asset (the cached asset set is incomplete on this machine, as the expansion
report also noted); it is logged twice and does not crash the client. AppleSkin HUD visuals were not
compared manually.

## Not done

- AppleSkin status-effect tooltip still calls tombstone `t5` (`FoodComponent.getStatusEffects`
  returning a `List`); not exercised by the HUD run;
- FallingTree multiplayer join (server send + client receive end-to-end) and tree-felling behavior
  are still unverified;
- no other mod from the expansion was retried.

## Evidence

- `client.log` (AppleSkin init), `appleskin-hud.log` (food bridge + in-world HUD),
  `fallingtree-client.log` (FallingTree run);
- rule files and bridge sources are in the repository; converted jars stay out of git.
