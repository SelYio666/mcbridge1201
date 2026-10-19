# P74: two-client sync attempt — blocked by LAN authentication

Date: 2026-10-19 (Asia/Shanghai). Attempted, not passed; the blocker is recorded precisely.

## Setup

- host client A: `--quickPlaySingleplayer "New World"`, probe opens LAN on port 25566
  (`IntegratedServer.method_3763`), then (once two players are present) writes 7 diamonds into the
  chest at `(78,65,-68)` and opens it server-side for the guest;
- guest client B: separate game dir/mod set, `--quickPlayMultiplayer 127.0.0.1:25566`, probe logs the
  chest menu slot when a `ChestScreen` appears;
- launcher extended with `MC_USERNAME`, `MC_GAME_DIR`, `MC_CWD`, `MC_LOG_DIR`, `QUICK_PLAY_MP`
  (copied here as `launch_client.py`).

Host side worked: `LAN_OPEN ok=true port=25566`, `Started serving on 25566`.

## Result

The guest connects and is immediately disconnected:

```text
[19:38:40] [Server thread/INFO]: GuestB (/127.0.0.1:65026) lost connection: Disconnected
```

The guest screen shows the reason (`guest-screen3.png`):

```text
Failed to connect to the server
Failed to log in: Invalid session (Try restarting your game and the launcher)
```

So the integrated server's LAN runs with online-mode authentication, and the offline test client
(`--accessToken 0`) cannot join. No `LAN_HOST_SET` / `LAN_GUEST_MENU` was reached.

## What was tried

- writing `server.properties` with `online-mode=false` into the Fabric profile dir before opening
  LAN — did not change the integrated server's behaviour;
- separate game dir + `onboardAccessibility:false` so quick-play is not blocked by the accessibility
  onboarding screen (that part works).

## Next step (needs a code change)

A dedicated server with `online-mode=false` would sidestep authentication, but the nested
ResourcefulLib port currently shares `FabricClientPacketHelper`, which references client-only
Fabric API classes (`ClientPlayNetworking`). On a dedicated server the chest sync path
(`sendToPlayer` → `idFor`/`RawPayload`) would load that class and fail. Before the two-client test
can run:

1. split the RL port into server-safe common parts (`RawPayload`, `idFor`, codec) and client-only
   registration/send paths;
2. run a dedicated server with `online-mode=false` and the patched IronChests jar;
3. connect two offline clients (`127.0.0.1:25565`) and repeat the host/guest probe.

## Evidence

- `guest-screen3.png`, `host.log`, `guest.log`
- `LanSyncProbe.java`, `launch_client.py`, `lansyncprobe.jar`
