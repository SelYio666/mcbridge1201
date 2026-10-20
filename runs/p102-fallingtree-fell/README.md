# P102: FallingTree tree felling

Date: 2026-10-20.

## Final status: **felling works**

```text
TREE_FIXED pos=class_2338{x=30, y=65, z=83} logsBefore=20
TREE_ARRIVED at={32.6,65.2,83.5}
TREE_BROKEN ticks=13
TREE_RESULT logsBefore=20 logsAfter=16
```

A textbook oak (four oak logs plus persistent leaves, placed via RCON next to spawn) is broken with a
real client break while holding a diamond axe in survival. All four trunk logs disappear, so
FallingTree's server-side felling ran end to end; the server log has no tombstone or
`NoSuchMethodError`.

## What had to be fixed

| problem | fix |
|---|---|
| `EnchantmentHelper.get(ItemStack)` tombstoned (`class_1890.method_8222`) | `FallingTreeBridge.enchantments` reads the 1.21.1 component and unwraps `RegistryEntry.comp_349()` |
| `Item.getMiningSpeedMultiplier` tombstoned | `miningSpeed` calls the renamed `method_58404` |
| `ItemStack.damage(int, LivingEntity, Consumer)` removed (server crashed mid-felling) | `damage` forwards to `method_7970(int, LivingEntity, EquipmentSlot.MAINHAND)`; the bridge keeps the legacy `Consumer` parameter so the call-site stack stays valid |

`rules/fabric-1.21.1/fallingtree-tombstones.json` applies all three (2 + 1 + 1 sites).

## What the failures were

- Without an axe in the main hand, `isValidTool` rejects the player, so `TreeHandler.breakTree`
  returns `ABORTED(INVALID_PLAYER_STATE)` and only the broken log disappears. This is the mod's
  default behaviour, not a conversion gap.
- The earlier "no felling" runs were therefore a test-harness issue; the only real conversion gaps
  were the three API bridges above.

## How the test works

1. RCON `setblock` builds the tree at `30,65..68,83` with leaves, and
   `item replace entity TestPlayer weapon.mainhand with minecraft:diamond_axe`.
2. A client probe walks to the trunk, breaks the bottom log with the real interaction manager.
3. The probe counts logs in a 13x25x13 box before and after.
4. Server runs with `gamemode=survival` and `force-gamemode=true`.

## Earlier failed runs (kept as evidence)

- `runs/p102-fallingtree-fell/server.log` etc.: hand-breaking, creative mode, no axe; only one log
  removed.
- `server-call*.log`: direct `TreeHandler.breakTree` calls returning `ABORTED(INVALID_PLAYER_STATE)`.
- `server-events.log`: proves `PlayerBlockBreakEvents.BEFORE/AFTER` fire.
- `server-tag.log`: `LOGS_TAG present=true`.
- `server-axe.log`: server crash from the damage tombstone before the bridge was fixed.

## Evidence

`client-success.log`, `server-fell2.log`, `commands.txt`; failure logs listed above.
