# P64: clientbound TrashSlot content delivery works

Date: 2026-10-19 (Asia/Shanghai). Server-to-client `MessageTrashSlotContent` through the Balm
payload bridge.

## Probe

- server tick 60 sends a `MessageTrashSlotContent` with 3 diamonds through
  `BalmNetworkingBridge.sendTo(BalmNetworking, Player, Object)` (reflection because the patched
  old message does not satisfy Balm 21's generic bound);
- client tick 140 reads `TrashSlotGuiHandler.getTrashSlot()`.

## Result

```text
S2C_SENT
S2C_CLIENT trash=3 minecraft:diamond
```

The client receiver registered by `BalmNetworkingBridge$Client` received the payload and updated the
trash slot to 3 diamonds. No exception.

## Scope

- verifies clientbound payload registration + `sendTo` bridge + client receiver for TrashSlot;
- does not verify ironchests clientbound traffic or two-client synchronization;
- empty-trash still not verified.

## Evidence

- `latest.log`, `TrashS2CProbe.java`
