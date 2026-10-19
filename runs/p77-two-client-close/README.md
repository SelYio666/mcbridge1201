# P77: two-client close — fixed by calling Screen.close()

Date: 2026-10-19 (Asia/Shanghai). Initially a finding, then fixed in the same round.

## First attempt: setScreen(null) is not enough

Both clients closed with `MinecraftClient.setScreen(null)`:

```text
GUEST  LAN_CLOSED player=GuestB screen=null
HOST   LAN_CLOSED player=HostA screen=null
SERVER DED_MENUS hostSlots=90 guestSlots=90   (tick 420)
SERVER DED_MENUS hostSlots=90 guestSlots=90   (tick 520)
```

The UI disappeared locally, but the server kept the 90-slot chest menus for 100+ ticks.

## Fix

The probe now calls `Screen.close()` (`method_25419`) on the open screen instead of
`setScreen(null)`:

```java
if (client.field_1755 != null) {
    client.field_1755.method_25419();
} else {
    client.method_1507(null);
}
```

## Result (second run)

```text
GUEST  LAN_CLOSED player=GuestB screen=null slots=46
HOST   LAN_CLOSED player=HostA screen=null slots=46
SERVER DED_MENUS hostSlots=46 guestSlots=46   (tick 420)
SERVER DED_MENUS hostSlots=46 guestSlots=46   (tick 520)
```

Both the client handlers and the server handlers fall back to the 46-slot inventory handler.
Closing the chest from both clients works.

## Scope

Probe-driven, one client closing at a time (guest first, then host). Real keyboard ESC uses the same
`Screen.close()` path, but that physical key path is still untested.

## Evidence

- `server-close.log`, `guest-close.log`, `host-close.log`
- `LanSyncProbe.java` (updated), `DedicatedSyncProbe.java`
- the earlier failed run: `server.log`, `guest.log`, `host.log`
