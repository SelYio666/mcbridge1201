# P63: TrashSlot second-click event reaches the handler but does not return

Date: 2026-10-19 (Asia/Shanghai). Debug mixin at `TrashSlotGuiHandler.onMouseClick` HEAD.

## Result

Three real clicks in a clean run:

```text
DEBUG_CLICK button=0 x=99.19 y=193.0 hovering=false carried=0 ... enabled=true provider=DefaultDeletionProvider
DEBUG_CLICK button=0 x=245.48 y=218.67 hovering=true carried=5 minecraft:diamond ... enabled=true provider=DefaultDeletionProvider
DEBUG_CLICK button=0 x=245.48 y=218.67 hovering=true carried=0 minecraft:air trash=5 minecraft:diamond ... enabled=true provider=DefaultDeletionProvider
```

Third click is the return attempt. At handler entry it satisfies every visible precondition:

- event arrived;
- `hovering=true`;
- carried is empty;
- trash has 5 diamonds;
- settings enabled;
- deletion provider is present.

Yet after the click the trash still has the diamonds. So the failure is **inside the handler path after
HEAD**, not an absent event and not a hit-test failure. The next step is a RETURN injection and a
server-side log around `MessageTrashSlotClick.handle` to see whether `undeleteLast` is entered and
whether the client is overwritten by a server update.

## Not verified

- whether `undeleteLast` is called (needs RETURN/provider injection);
- whether the server receives and accepts the return packet;
- empty-trash;
- ironchests GUI / clientbound / two-client sync.

## Evidence

- `latest.log`, `TrashGuiDebugMixin.java`, `trashdebug.mixins.json`
