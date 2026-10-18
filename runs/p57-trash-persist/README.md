# P57: trash persistence probe — corrected: login reset is TrashSlot behavior

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
TRASH_PROBE_NBT balmKeys={TrashSlot} trash={count:5,id:"minecraft:diamond"}
```

The two NBT bridges work in-session: the 5-diamond stack is read back immediately, and the live
`BalmData/TrashSlot` compound contains the item.

Then **Save and Quit to Title**, reopen the same `New World`, and join again:

```text
TRASH_PROBE_SET after=5 empty=false
```

The second join sees an empty trash. The saved player NBT has `BalmData/TrashSlot`, but it is an
empty compound (verified with a small NBT parser: `TrashSlot (10, {})`).

## Correction: this is not a bridge persistence bug

`TrashSlot.lambda$initialize$0(PlayerLoginEvent)` explicitly does:

```text
TrashHelper.setTrashItem(player, ItemStack.EMPTY)
BalmNetworking.sendTo(player, new MessageTrashSlotContent(ItemStack.EMPTY))
```

So TrashSlot **clears the trash on every login by design** (or at least by its own code). The
rejoin-empty result is therefore expected mod behavior, not evidence that the NBT bridge failed.
The probe ran at `ServerPlayConnectionEvents.JOIN`; the mod's login event clears it afterward.

## Status

- in-session `setTrashItem` → `getTrashItem`: works (5 diamonds);
- reload persistence: **not a valid contract for this mod version**, because login resets it;
- GUI drag (P56) still did not transfer an item; that remains an independent issue to investigate;
- no persistence-pass claim either way.

## Next

- Check TrashSlot's intended lifecycle (is trash meant to be session-only?); do not "fix" the
  login reset without evidence.
- Focus the remaining GUI issue on the trash slot widget/hit-test, not on NBT.

## Evidence

- `latest.log`, `client.log`, `pause.png`, `pause2.png`
