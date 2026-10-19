# P58: why the TrashSlot button did not accept item clicks

Date: 2026-10-19 (Asia/Shanghai). Programmatic slot inspection.

## Probe

The client probe gives the joining player 5 diamonds, opens `InventoryScreen`, then asks
`TrashSlotGuiHandler` for the actual slot/component and prints their positions:

```java
TrashSlotSlot trash = TrashSlotGuiHandler.getTrashSlot();
TrashSlotComponent component = TrashSlotGuiHandler.getTrashSlotComponent();
System.out.println("trash=" + trash.field_7873 + "," + trash.field_7872);
System.out.println("componentAnchor=" + getAnchoredX() + "," + getAnchoredY());
System.out.println("trashIndex=" + handler.field_7761.indexOf(trash)
        + " slots=" + handler.field_7761.size());
```

## Result

```text
TRASH_PROBE screen=net.minecraft.class_490@66f40de1 trash=152,165 component=...@1746d4d0
TRASH_PROBE componentAnchor=231,211
TRASH_PROBE rectangle=net.minecraft.class_768@11b64787
TRASH_PROBE leftTop=83,45
TRASH_PROBE diamond slot=36 count=5
TRASH_PROBE trashIndex=-1 slots=46
TRASH_PROBE_ABORT
```

`trash=152,165` is relative to the screen's `leftPos/topPos=83,45`, so its absolute GUI position
is about `235,210`; the component anchor `231,211` agrees. This is **not** the initial
`152,165` screen-coordinate rectangle. The rectangle is a `Rect2i` and must be read with its
x/y/width/height getters before clicking.

Key point: **`trashIndex=-1`**. The `TrashSlotSlot` is *not* in the screen handler's `field_7761`
slot list (46 vanilla/inventory slots). It is a client-side custom slot drawn by
`TrashSlotComponent`, with its own anchor at `231,211`; the rendered trash icon is placed by the
component's layout offsets, not by the slot's `152,165` position.

Therefore a normal screen-coordinate click cannot be translated into a normal
`ScreenHandler`/`ClientPlayerInteractionManager.clickSlot` on this slot. The component intercepts
mouse events itself (`TrashSlotGuiHandler` + `TrashSlotComponent.update`).

## Status

- This explains why the P56 mouse click/drag did not move the stack: there is no handler slot index
  to target, and the component's drag path was not hit.
- No item transfer/persistence claim is made.
- Next: drive `TrashSlotComponent.isInside`/its drag state with the component's actual anchor and
  offsets, or call the component's own click path, rather than `clickSlot`.

## Evidence

- `latest.log`, `TrashClickProbe.java`
