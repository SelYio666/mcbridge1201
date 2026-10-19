# P63: TrashSlot GUI move-in and return both pass

Date: 2026-10-19 (Asia/Shanghai). Debug mixin + clean real-mouse run; **corrected from the earlier
"return fails" interpretation**.

## Move-in

Third-click debug at `onMouseClick` HEAD (second real click, moving the stack in):

```text
DEBUG_CLICK ... hovering=true carried=5 minecraft:diamond trash=0
DEBUG_AFTER_CLICK carried=0 minecraft:air trash=5 minecraft:diamond
DEBUG_PACKET_HEAD msg=5 minecraft:diamond serverCarried=5 serverTrash=0
DEBUG_PACKET_RETURN serverCarried=0 serverTrash=5
```

## Return

Next click (empty carried):

```text
DEBUG_CLICK ... hovering=true carried=0 minecraft:air trash=5 minecraft:diamond
DEBUG_PROVIDER_UNDELETE trash=5 minecraft:diamond right=false
DEBUG_AFTER_CLICK carried=5 minecraft:diamond trash=0 minecraft:air
DEBUG_PACKET_HEAD msg=0 minecraft:air serverCarried=0 serverTrash=5
DEBUG_PACKET_RETURN serverCarried=5 minecraft:diamond serverTrash=0
```

## Screenshot correction

`final-return.png` looked like the trash still had diamonds because the returned stack is held on
the **cursor**, which was over the trash icon. Moving the cursor away (`cursor-away.png`) shows the
5-diamond stack following the cursor at the top-left; the trash is empty.

So:

- GUI move-in: **pass**;
- GUI return: **pass**;
- server packet delete: **pass**;
- server packet return: **pass**;
- no duplication.

## Still not verified

- empty-trash action;
- ironchests GUI / clientbound delivery / two-client sync;
- restart persistence (TrashSlot login reset by design).

## Evidence

- `latest-provider-return.log` (client provider/RETURN)
- `latest-packet-return.log` (server packet HEAD/RETURN)
- `final-return.png`, `cursor-away.png`
- `TrashGuiDebugMixin.java`, `TrashProviderDebugMixin.java`, `TrashPacketDebugMixin.java`
