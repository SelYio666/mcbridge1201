# P60: TrashSlot undelete/return path works at the provider + server level

Date: 2026-10-19 (Asia/Shanghai). Direct provider test; quick-play used to avoid menu clicks.

## Setup

- client launched with `--quickPlaySingleplayer "New World"`;
- server tick 40 seeds `TrashHelper.setTrashItem(player, 5 diamonds)` **after** TrashSlot's login
  reset;
- client at tick 80 sets the client trash slot to 5 diamonds, then calls:

```java
TrashSlotConfig.getDeletionProvider().undeleteLast(player, trashSlot, false);
```

## Result

```text
RETURN_GUI    trash=5 minecraft:diamond provider=DefaultDeletionProvider
RETURN_AFTER  cursor=5 minecraft:diamond trash=0 minecraft:air
RETURN_FINAL  cursor=5 minecraft:diamond trash=0 minecraft:air
RETURN_SERVER empty=true count=0
```

So:

- `undeleteLast` moves the stack from the trash slot to the cursor;
- the serverbound packet is sent;
- the server trash is emptied;
- no `NoSuchMethodError`.

## Scope

This verifies the **return logic + packet + server state**, not the GUI mouse click that should
call it. The earlier P59 second click did not trigger return; that remains a GUI hit/event issue,
not a broken `undeleteLast` implementation.

A follow-up diagnostic called `screen.method_25402(235,210,0)` (slot top-left, absolute GUI
coordinates) with the trash holding 5 diamonds:

```text
RETURN_CLICK x=235 y=210
RETURN_AFTER cursor=0 trash=5 minecraft:diamond
RETURN_SERVER empty=false count=5
```

The direct screen call did not trigger the handler either. The external OS click at
`743,687` (physical) had worked for move-in, so the next step is to log the component's true
`getRectangle()` and use its center, not the slot top-left.

## Not verified

- actual mouse click that invokes `undeleteLast`;
- empty-trash action;
- restart persistence (login reset by design);
- ironchests GUI / clientbound delivery / two-client sync.

## Evidence

- `client.log` (contains both render and server stdout)
- `latest-screen-click.log`, `client-screen-click.log`
- `latest.log` (server lines)
- `TrashReturnProbe.java`
