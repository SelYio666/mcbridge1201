# P80: clean same-tick race — server grants one, loser is corrected

Date: 2026-10-19 (Asia/Shanghai). Closes the contaminated-state caveat from P79.

## Setup

Dedicated server (online-mode=false). Before the race the server now **clears both player
inventories and the chest**, then puts 7 diamonds into chest slot 0 and opens the chest for both
players in the same tick. Both clients wait for the same world-time boundary
(`world.getTime() % 100 == 0`) and click chest slot 0 → their slot 54.

## Result

```text
DED_SET cleaned slot0=7 minecraft:diamond hostInv=air guestInv=air
DED_OPEN guest=GuestB (same tick)
DED_OPEN host=HostA   (same tick)

GUEST  LAN_TAKE player=GuestB time=2700 slot0=air slot54=7 diamonds
HOST   LAN_TAKE player=HostA  time=2700 slot0=air slot54=7 diamonds
GUEST  LAN_POST player=GuestB slot0=air slot54=7 diamonds     (winner, server agrees)
HOST   LAN_POST player=HostA  slot0=air slot54=air             (loser, corrected)

DED_TOTAL chest=air hostSlot54=air guestSlot54=7 diamonds
```

- both clients predicted success on the same tick (2700);
- after 100 ticks the loser's client was corrected to `slot54=air`;
- the server total stayed 7 (chest 0 + host 0 + guest 7) — **no duplication**;
- the client that won kept the stack, matching the server.

## Conclusion

The clean run confirms P79's conclusion: under same-tick concurrent clicks the server is
authoritative, only one client keeps the stack, and the other client's prediction is corrected by a
slot update.

## Evidence

- `server.log`, `guest.log`, `host.log`, `compile.log`
- `DedicatedSyncProbe.java`, `LanSyncProbe.java`
