# P65: empty-trash path fixed with the Balm reply bridge

Date: 2026-10-19 (Asia/Shanghai). New real crash + fix.

## Crash

Calling `DefaultDeletionProvider.emptyTrashSlot` produced:

```text
NoSuchMethodError: 'void net.blay09.mods.balm.api.network.BalmNetworking.reply(java.lang.Object)'
at MessageDeleteFromSlot.handle(MessageDeleteFromSlot.java:44)
```

Balm 21's `reply(T extends CustomPayload)` has a different erasure. `MessageDeleteFromSlot.handle`
uses `reply` to send the updated trash content back to the player who sent the delete packet.

## Fix

- `BalmNetworkingBridge` tracks the current serverbound player in a `ThreadLocal` around the
  handler call;
- new `reply(BalmNetworking, Object)` looks up the registered clientbound payload and calls
  `ServerPlayNetworking.send(currentPlayer, payload)`;
- `trashslot-sendtoserver.json` gets the `trashslot.balm.reply` redirect (2 call sites);
- rebuilt/patch -> `trashslot-client-empty.jar`.

## Result

```text
EMPTY_PROBE_SEEDED
EMPTY_BEFORE trash=5 minecraft:diamond
EMPTY_AFTER trash=0 minecraft:air
EMPTY_SERVER empty=true count=0
```

Client and server trash both empty; no `NoSuchMethodError`; no server crash.

## Scope

This verifies the provider-level empty action and its serverbound/clientbound round trip. The real
keyboard/UI action that invokes `emptyTrashSlot` is now also verified in
`runs/p183-trash-key/`: a real Delete key (extended scan code) over the trash slot reaches
`ScreenKeyEvent.Press.Post`, calls the provider, and the server reads `empty=true count=0`. The
earlier p85/p86 "Delete does nothing" was an input-injection bug: `keybd_event` without
`KEYEVENTF_EXTENDEDKEY` delivered KP_DECIMAL (GLFW 330), not DELETE (261), so the key binding never
matched. Shift+Delete/creative/multi-client variants are still untested.

## Evidence

- `crash-report.txt`, `latest.log`, `build-bridges.log`, `patch-reply.log`, `TrashEmptyProbe.java`
