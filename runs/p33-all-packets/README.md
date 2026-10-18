# P33: all three trashslot packet codecs round-trip

Date: 2026-10-18 (Asia/Shanghai). Extends P32 from `MessageTrashSlotClick` to both remaining
trashslot packets.

## Probe cases

At `ServerLifecycleEvents.SERVER_STARTED`:

- `MessageTrashSlotClick`: empty + `ItemStack(DIAMOND, 5)`, assert empty/count/item;
- `MessageTrashSlotContent`: empty + `ItemStack(DIAMOND, 5)`, same assertions;
- `MessageDeleteFromSlot(3, true)`: assert `slotNumber=3` and `isDeleteAll=true`.

## Result

```text
Done (4.993s)! For help, type "help"
[STDOUT]: TRASHSLOT_ALL_CODEC_OK
```

`doneSeen=true`, runner/JVM exit 0.

This covers all three trashslot packet encode/decode paths and the ItemStack/NBT bridges for
both directions. Client delivery, the GUI and player actions remain unverified.

## Evidence

- `compile.log`
- `jar.log`
- `server.log` / `server.result.json`
