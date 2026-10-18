# P57: trash persistence probe — in-session works, reload loses it

Date: 2026-10-19 (Asia/Shanghai). Direct TrashHelper test, no GUI ambiguity.

## Probe

On player join:

```java
class_1799 before = TrashHelper.getTrashItem(player);
if (before.method_7960()) {
    TrashHelper.setTrashItem(player, new class_1799(class_1802.field_8477, 5));
    System.out.println("TRASH_PROBE_SET after=" + after.method_7947());
} else {
    System.out.println("TRASH_PROBE_PERSIST ...");
}
```

## Result

First join:

```text
TRASH_PROBE_SET after=5 empty=false
```

So the two NBT bridges do work in-session: the 5-diamond stack is read back immediately.

Then **Save and Quit to Title**, reopen the same `New World`, and join again:

```text
TRASH_PROBE_SET after=5 empty=false
```

The second join sees an empty trash, so the data written through `TrashHelper.setTrashItem` did not
survive the player save/reload. The saved player NBT does contain `BalmData/TrashSlot`, but no
`diamond`/`minecraft:diamond` string was present in that compound — the written trash payload is
empty/not round-tripped.

## Interpretation

This is a **real persistence gap** in the current trashslot patch path, separate from the GUI
drag issue:

- in-session `setTrashItem` → `getTrashItem` works (5 diamonds);
- after save/reload the player's trash is empty;
- GUI drag (P56) also did not transfer an item.

The next investigation is the save path: whether `TrashHelper.setTrashItem` mutates the live
Balm persistent-data compound, and why the saved `BalmData/TrashSlot` compound has no item payload
(the `ItemStack.CODEC` encode target/copy may be wrong for this player-data path).

## Status

- trash persistence: **not verified / currently failing**
- no claim that `setTrashItem` or the GUI is a pass
- do not ship this as a core-save fix until the NBT round-trip is correct

## Evidence

- `latest.log`, `client.log`, `pause.png`, `pause2.png`
