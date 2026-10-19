# P78: two clients act on the same chest — no duplication

Date: 2026-10-19 (Asia/Shanghai). Concurrency edge case for the two-client chest.

## Setup

Dedicated server (online-mode=false). The server puts 7 diamonds in the chest and opens it for the
guest; the host opens it a couple of seconds later. Both clients then click chest slot 0 and put the
result into their own slot 54. The server logs the chest plus both inventories afterwards.

## Result

```text
GUEST  LAN_MENU player=GuestB slot0=7 minecraft:diamond
GUEST  LAN_TAKE player=GuestB slot0=0 minecraft:air slot54=7 minecraft:diamond slots=90
HOST   LAN_MENU player=HostA slot0=0 minecraft:air
HOST   LAN_TAKE player=HostA slot0=0 minecraft:air slot54=0 minecraft:air slots=90
SERVER DED_TOTAL chest=0 minecraft:air hostSlot54=0 minecraft:air guestSlot54=7 minecraft:diamond
```

Total diamonds: chest 0 + host 0 + guest 7 = **7**, the original amount. No duplication.

## Honest scope

The host opened the chest ~2 seconds after the guest had already taken the stack, so this is
**sequential contention**, not a true same-tick race. It does show that a second client operating on
the same chest sees the authoritative empty state and cannot duplicate the stack. A same-tick
concurrent click test would need both menus opened in the same server tick.

## Evidence

- `server.log`, `host.log`, `guest.log`
- `DedicatedSyncProbe.java`, `LanSyncProbe.java`
