# P90: FallingTree join path with the legacy networking bridge

Date: 2026-10-19. End-to-end check of the server `send` → client `receive` path.

## Setup

- dedicated server: `work/instances/fabric-1.21.1-server` with Fabric API, Balm, the existing test
  probes and the patched `fallingtree-legacy.jar`;
- client: PCL 1.21.1 instance, same patched FallingTree jar plus Fabric API;
- client connects to `127.0.0.1:25565` (offline test identity `TestPlayer`).

## Result

```text
[23:00:25] [Server thread/INFO]: TestPlayer[/127.0.0.1:65490] logged in with entity id 124
[23:00:25] [Server thread/INFO]: TestPlayer joined the game
```

- the previous join crash
  `NoSuchMethodError: void ServerPlayNetworking.send(ServerPlayerEntity, Identifier, PacketByteBuf)`
  did **not** occur;
- the client stayed connected (`Minecraft* 1.21.1 - Multiplayer (3rd-party Server)`);
- the server log contains no `NoSuchMethodError` / `NoClassDefFoundError` for FallingTree; only the
  environment's JNA warnings are present (the same warnings appear for other mods).

FallingTree sends its config to the client from `FabricServerPacketHandler.onPlayerConnected`; that
call now goes through `FabricLegacyNetworking.sendToPlayer`, and the client-side receiver registered
through the `PlayChannelHandler` shim accepts it.

## Scope

- no tree-felling test: no controlled tree/log setup was built for this run;
- no check that the client applied the received config (no UI assertion);
- only this one mod in the join test; other expansion mods untouched.

## Evidence

- `server.log`, `server.err`, `client/client.log`
- patched jar stays out of git; rules in `rules/fabric-1.21.1/fabric-legacy-networking.json`.
