# P55: inventory + TrashSlot GUI renders in-world

Date: 2026-10-19 (Asia/Shanghai). Test-harness GUI verification.

## How

Synthetic `E` key injection did not open the inventory reliably, so a tiny **client-only test mod**
opens `InventoryScreen` once after the player exists:

```java
ClientTickEvents.END_CLIENT_TICK.register(client -> {
    if (!opened && client.field_1724 != null) {
        opened = true;
        client.method_1507(new class_490(client.field_1724));
    }
});
```

Source: `InventoryProbe.java` (work-only test harness, not part of the patcher).

## Result

The client was already in a world (P54). The probe opened the inventory and the screenshot shows:

- the vanilla inventory GUI;
- the **TrashSlot trash button** at the bottom-right of the inventory;
- the world/hotbar rendered behind it.

`trash-click.png` is after clicking the trash button; the inventory stays open (the slot is empty,
so no visible transfer). This verifies **GUI rendering/integration**, not item transfer.

## Not verified

- Moving an ItemStack into/out of the trash slot (needs a real item and click sequence);
- persistence of the trash slot across restart;
- ironchests container GUI;
- clientbound sync / two clients.

## Evidence

- `inventory-probe.png`, `trash-click.png`
- `InventoryProbe.java`, `latest.log`, `client.log`
