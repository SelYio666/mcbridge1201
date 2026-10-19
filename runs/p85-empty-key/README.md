# P85: empty-trash real key — blocked by the hover requirement

Date: 2026-10-19 (Asia/Shanghai). Attempted, not passed.

## Setup

Client probe opens the inventory (`InventoryScreen`), seeds the trash slot with 5 diamonds via
`TrashSlotGuiHandler.getTrashSlot().setStack(...)`, then logs the trash state every 40 ticks. With
the inventory open, the probe injected **Shift+Delete** through the OS keyboard API.

## Result

```text
TRASH_SEED  trash=5 minecraft:diamond
TRASH_STATE tick=200 screen=InventoryScreen trash=5 minecraft:diamond
TRASH_STATE tick=240 ... trash=5
TRASH_STATE tick=280 ... trash=5
TRASH_STATE tick=320 ... trash=5
TRASH_STATE tick=360 ... trash=5
TRASH_STATE tick=400 screen=class_418 trash=5
```

The trash was not emptied; the key did nothing without the mouse hovering the trash icon (the screen
changed later, but the trash remained).

## Interpretation

TrashSlot's key handler checks whether the cursor is inside the trash component before acting
(`isInside`/`callIsHovering`). A pure keyboard injection is therefore not enough; the probe must
also position the mouse over the icon, which requires the component's screen rectangle and the
window/GUI-scale conversion.

The empty-trash action itself is already verified at provider level in P65
(`EMPTY_BEFORE trash=5` → `EMPTY_AFTER trash=0`, server empty). Only the physical key path is open.

## Next

Compute the trash component rectangle at runtime (scan `TrashSlotComponent.isInside` over the screen
area), convert to physical pixels with the window position and GUI scale, move the OS cursor there,
then inject Shift+Delete.

## Evidence

- `latest.log`, `TrashEmptyKeyProbe.java`, `trashemptykey.jar`, `compile.log`
