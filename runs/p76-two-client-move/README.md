# P76: two clients, put/take round trip across clients

Date: 2026-10-19 (Asia/Shanghai). Extends P75 (server → guest content sync) with a real guest → server
→ host round trip.

## What happened

1. dedicated server (`online-mode=false`) with the split ResourcefulCraft port and `dedprobe`;
2. `HostA` and `GuestB` connect;
3. server writes 7 diamonds into the chest and opens it for the guest;
4. the guest **takes the stack out** with two `clickSlot` calls;
5. the server logs the chest afterwards; the host opens the chest and sees the updated state.

## Result

```text
GUEST   LAN_MENU player=GuestB slot0=7 minecraft:diamond
GUEST   LAN_GUEST_MOVED player=GuestB slot0=0 minecraft:air slot54=7 minecraft:diamond
SERVER  DED_AFTER slot0=0 minecraft:air
SERVER  DED_OPEN_HOST
HOST    LAN_MENU player=HostA slot0=0 minecraft:air
```

- guest → server write works (the chest becomes empty on the server);
- server → host sync works (the host sees the emptied chest).

## Fixes made during this round

- the first attempt crashed the guest with `IndexOutOfBoundsException: Index 54 out of bounds for
  length 46`: the guest stood ~11 blocks from the chest, the chest menu's validity check closed it,
  and the client handler fell back to the 46-slot inventory. The probe now teleports the guest next
  to the chest before opening, and the client guards `slots <= 54` before clicking.

## Scope

Both clients are driven by probes, not by a human. The test covers one direction of item movement
(guest takes from the chest) plus the host observing it; simultaneous edits from both clients and
screen-close behaviour are still untested.

## Evidence

- `server.log`, `guest.log`, `host.log`
- `DedicatedSyncProbe.java`, `LanSyncProbe.java`, `dedprobe.jar`, `lansyncprobe.jar`
