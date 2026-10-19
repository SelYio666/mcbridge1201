# P77: two-client close attempt — local close works, server menu stays open

Date: 2026-10-19 (Asia/Shanghai). Edge-case probe, recorded as a finding (not a pass).

## Setup

Same dedicated server as P75/P76. After the server opens the chest for the guest and then the host,
each client closes its screen with `MinecraftClient.setScreen(null)` and logs the result.

## Result

```text
GUEST  LAN_GUEST_MOVED slot0=air slot54=7 minecraft:diamond
GUEST  LAN_CLOSED player=GuestB screen=null
HOST   LAN_CLOSED player=HostA screen=null
SERVER DED_MENUS hostSlots=90 guestSlots=90   (tick 420)
SERVER DED_MENUS hostSlots=90 guestSlots=90   (tick 520)
```

- both clients close the screen locally and do not crash;
- the **server** still reports 90-slot chest menus for both players 100+ ticks later, i.e. the
  server-side `currentScreenHandler` did not fall back to the 46-slot inventory handler.

## Interpretation

`setScreen(null)` alone is not enough to make the server drop the menu in this port; the client's
`HandledScreen.removed()` / `closeHandledScreen()` path needs to be checked, or the close should be
driven through the screen's `close()` / an explicit `CloseHandledScreenC2SPacket`. Until then the
chest menu can stay "open" server-side after the UI is gone.

## Evidence

- `server.log`, `guest.log`, `host.log`
- `DedicatedSyncProbe.java`, `LanSyncProbe.java`
