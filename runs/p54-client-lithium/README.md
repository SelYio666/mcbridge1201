# P54: client in-world with lithium varint bridge

Date: 2026-10-19 (Asia/Shanghai). The client now joins and renders a singleplayer world.

## Fix

Lithium's palette serialized size called the 1.20.1 `FriendlyByteBuf.getVarIntSize(int)`, which
CenturyBridge tombstoned. Added `LithiumVarIntBridge.getByteSize(int)` →

```java
net.minecraft.class_8703.method_53015(value)
```

(`VarInt.getByteSize`), plus `rules/fabric-1.21.1/lithium-varint.json`. The rule is applied to the
P13 chunk-port jar: 2 call sites, one bridge.

## Result

The client logged in, generated the spawn area and rendered the world:

```text
Preparing start region for dimension minecraft:overworld
TestPlayer joined the game
Loaded 2 advancements
```

Window title: `Minecraft* 1.21.1 - Singleplayer`. `world.png` shows the player in survival with
terrain, HUD and hotbar.

## Not tested

- Opening the inventory/trash GUI: synthetic `E` key events did not open it in this automation
  session (`inventory*.png` are unchanged world frames), so this is not claimed.
- ironchests GUI, trash-slot move/persistence, clientbound delivery, two-client sync.
- The magenta main-menu background is still the missing panorama asset, not a crash.

## Status

| item | result |
|---|---|
| client loads all mods | pass |
| main menu | pass |
| world join + terrain rendering | **pass** |
| inventory / trash GUI | not executed (key injection failed) |
| container / trash persistence / sync | not executed |

## Evidence

- `world.png`, `inventory.png`, `inventory2.png`
- `latest.log`, `client.log`, `patch.log`, `launch.pid`
