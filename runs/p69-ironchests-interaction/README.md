# P69: IronChests GUI interaction passes (put + take back)

Date: 2026-10-19 (Asia/Shanghai). Follows P68 (the chest GUI opens and renders).

## Result

Client `clickSlot` on the open chest menu, with the server's own menu state sampled afterwards:

```text
CLICK_BEFORE  sync=1 slot0=air          slot54=air
CLICK_SOURCE=81
CLICK_PUT     slot0=25 diamonds         source=air
SERVER_MENU   tick=220 slot0=25 diamonds slot54=air
CLICK_AFTER_PUT slot0=25 diamonds       slot54=air
CLICK_TAKE    slot0=air                 slot54=25 diamonds
SERVER_MENU   tick=260 slot0=air        slot54=25 diamonds
SERVER_MENU   tick=300 slot0=air        slot54=25 diamonds
CLICK_FINAL   slot0=air                 slot54=25 diamonds
```

So the round trip really happened on both sides:

- the stack moved from hotbar slot 81 into chest slot 0 (server confirms at tick 220);
- the stack moved back out to inventory slot 54 (server confirms at tick 260 and 300);
- no duplication, no loss.

## How

The probe (extended `IronChestsGuiProbe`):

- server gives the iron chest plus 10 diamonds, places the chest, opens it through
  `GenericChestBlock.method_9534`;
- client finds the first non-empty inventory slot (`source=81`), then calls
  `ClientPlayerInteractionManager.method_2906(syncId, source, 0, SlotActionType.PICKUP, player)`
  and the same for chest slot 0;
- after 40 ticks it clicks slot 0 then slot 54 to take the stack back;
- the server logs `joined.field_7512` slot states at ticks 220/260/300.

## Status

| step | result |
|---|---|
| chest GUI opens/renders | pass (P68) |
| put item into chest | **pass** |
| take item back out | **pass** |
| server-side state agrees | **pass** |
| clientbound item sync / two clients | not yet |

## Evidence

- `latest.log`, `IronChestsGuiProbe.java`, `compile.log`
