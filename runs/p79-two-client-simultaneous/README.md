# P79: same-tick concurrent clicks — one winner, no duplication

Date: 2026-10-19 (Asia/Shanghai). True same-tick race between the two clients.

## Setup

Dedicated server (online-mode=false). The server opens the chest for both players in the same tick
and puts 7 diamonds in slot 0. Both clients wait for the same world-time boundary
(`world.getTime() % 100 == 0`) and then click chest slot 0 → their slot 54.

## Run 1 (clean)

```text
GUEST  LAN_MENU slot0=7 diamonds
HOST   LAN_MENU slot0=7 diamonds
GUEST  LAN_TAKE player=GuestB time=2700 slot0=air slot54=7 diamonds slots=90
HOST   LAN_TAKE player=HostA  time=2700 slot0=air slot54=7 diamonds slots=90
SERVER DED_TOTAL chest=air hostSlot54=air guestSlot54=7 diamonds
```

Both clients clicked in the **same world tick (2700)**. Both clients *predicted* success
(`slot54=7`), but the server granted the stack to exactly one player (guest); the host's server-side
slot is empty. Total is still 7 — no duplication server-side.

## Run 2 (correction check, state partly contaminated)

A second run reused the still-running server (inventories were not cleared), so the numbers are
noisy: the guest showed `slot54=14` at click time (7 old + 7 predicted), then a later `LAN_POST`
showed `slot54=0` — the server's slot update corrected the client prediction. The server total for
that run was `hostSlot54=7 guestSlot54=0`.

## Conclusion

- server authority holds: concurrent same-tick clicks cannot duplicate a stack;
- client-side prediction can briefly show the stack on both clients;
- the server's slot update corrects the loser (observed in run 2);
- a fully clean re-test needs the server to clear both inventories and the chest before the race
  (run 2 was polluted by persisted player data).

## Evidence

- `server.log`, `guest.log`, `host.log` (run 1)
- `DedicatedSyncProbe.java`, `LanSyncProbe.java`
