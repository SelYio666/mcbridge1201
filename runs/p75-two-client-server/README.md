# P75: two-client sync passes on a dedicated server

Date: 2026-10-19 (Asia/Shanghai). Supersedes the P74 LAN attempt.

## What changed

The P74 attempt was blocked because a LAN world enforces online-mode. The dedicated-server route
needed one code fix first: the nested ResourcefulLib port shared `FabricClientPacketHelper`, which
references client-only classes. Calling `sendToPlayer` on a dedicated server loaded the client
lambda and crashed with `NoClassDefFoundError: net/minecraft/class_638` (ClientWorld).

Split into:

- `RawChannel` — server-safe: payload id/codec, channel location, `RawPayload`; no client imports;
- `FabricClientPacketHelper` — client-only: `ClientPlayNetworking` register/send, delegating to
  `RawChannel`;
- `PacketChannelHelperImpl` — uses `RawChannel` for the server paths.

`tools/rebuild_ironchests_client.py` now compiles/replaces `RawChannel` (and its nested payload) and
drops the stale `FabricClientPacketHelper$RawPayload`.

Server rebuilt jar: `sha256 7e9d341f143e54c508b148bed30803fd60dddc040654853a04c3342fff4d75aa`.

## Setup

- dedicated Fabric server (`work/instances/fabric-1.21.1-server`) with the rebuilt IronChests jar,
  `online-mode=false`, `enforce-secure-profile=false`, plus a `dedprobe` server mod;
- two offline clients: `HostA` (own game dir) and `GuestB` (separate game dir/mods), both
  `--quickPlayMultiplayer 127.0.0.1:25565`;
- server mod places a chest next to the first player, writes 7 diamonds into it, then opens it for
  the second player through `BlockEntity.createMenu` (avoids the client-only `onUse` path).

## Result

```text
DED_PLACED placed=false pos=class_2338{x=17, y=70, z=70}
DED_SET slot0=7 minecraft:diamond
DED_OPEN opened=OptionalInt[1] guest=GuestB
LAN_GUEST_MENU screen=tech.thatgravyboat.ironchests.client.ChestScreen sync=1 slot0=7 minecraft:diamond
```

The guest client, connected to a dedicated server, received the chest contents written by the
server-side probe: **two-client clientbound chest sync works**.

## Scope / notes

- `DED_PLACED placed=false` on the rerun only means the chest already existed from the previous run.
- The screenshot taken after the run shows the other client window (host), not the guest chest; the
  guest evidence is the `LAN_GUEST_MENU` log line.
- This verifies server → second-client content sync. Full two-client interaction (both clients
  moving items, closing screens on both sides) is still untested.

## Evidence

- `server.log`, `guest.log`, `host.log`
- `DedicatedSyncProbe.java`, `LanSyncProbe.java`, `launch_client.py`, `dedprobe.jar`, `lansyncprobe.jar`
