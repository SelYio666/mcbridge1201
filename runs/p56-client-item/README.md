# P56: real ItemStack in the client inventory; trash drop not observed

Date: 2026-10-19 (Asia/Shanghai). Item injection + GUI interaction attempt.

## How

A test probe adds 5 diamonds to the joining server player and opens the inventory:

```java
ServerPlayConnectionEvents.JOIN.register((handler, sender, server) ->
        handler.method_32311().method_7270(new class_1799(class_1802.field_8477, 5)));
```

`inventory-with-diamonds.png` shows the 5 diamonds in the inventory and hotbar, so the
client/server item path works.

## Interaction attempt

The trash button is visible at the bottom-right. Tried:

- click the diamond stack, then click the trash button;
- click the stack into an empty slot, then drag it onto the trash button.

Each time the stack remained on the cursor (`trash-content.png`, `trash-drag.png`); the trash
slot did not visibly accept the item. No exception appears in `latest.log`.

This is **not** recorded as a pass. It may be a GUI hit-test/coordinate or slot-handler issue,
or a real TrashSlot client-side gap; the next step is to inspect the TrashSlot slot widget and
click path, not to claim item transfer.

## Not verified

- trash slot acceptance/persistence;
- reopening after restart;
- ironchests container GUI;
- two-client sync.

## Evidence

- `inventory-with-diamonds.png`, `trash-content.png`, `trash-drag.png`
- `GuiProbe.java`, `latest.log`, `client.log`
