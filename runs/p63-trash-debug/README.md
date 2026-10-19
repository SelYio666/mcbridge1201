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

Adding a provider HEAD mixin and an `onMouseClick` RETURN mixin showed the handler **does** run the
return:

```text
DEBUG_PROVIDER_UNDELETE trash=5 minecraft:diamond right=false
DEBUG_AFTER_CLICK carried=5 minecraft:diamond trash=0 minecraft:air
```

So the client handler/provider succeed. The item later reappears in the trash, which means the
server state or a server update reverts the client. The remaining issue is serverbound return
handling / sync, not the GUI event or `undeleteLast`.

## Not verified

- whether the server receives the return packet (a server-side mixin was not applied in the
  integrated server in this run);
- whether the server handler rejects `MessageTrashSlotClick(EMPTY)` because of server carried state;
- empty-trash;
- ironchests GUI / clientbound / two-client sync.

## Evidence

- `latest.log`, `latest-provider-return.log`, `TrashGuiDebugMixin.java`,
  `TrashProviderDebugMixin.java`, `trashdebug.mixins.json`
