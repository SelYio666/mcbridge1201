# P102: FallingTree break path and felling attempt

Date: 2026-10-20.

## Setup

Dedicated server (Fabric API + converted FallingTree 4.3.4) and a client with the same patched
FallingTree jar plus a probe. RCON builds a textbook oak tree next to spawn:

```text
setblock 30 65..68 83 minecraft:oak_log[axis=y]
leaves at 31/29,83; 30,84/82 (y=65/67) and 30,69,83
```

The probe walks to the trunk, breaks the bottom log with the real client interaction manager and
counts logs before/after within 13x25x13 blocks.

## What works

- FallingTree loads on both sides and the player joins (`TestPlayer joined the game`).
- The bottom log is really broken: `TREE_BROKEN ticks=72`.

Two more CenturyBridge tombstones surfaced on the break path and were bridged:

| tombstone | 1.20.1 call | 1.21.1 replacement |
|---|---|---|
| `t0` | `EnchantmentHelper.get(ItemStack)` → `Map<Enchantment,Integer>` | `EnchantmentHelper.method_57532` component, unwrap `RegistryEntry.comp_349()` |
| `t1` | `Item.getMiningSpeedMultiplier(ItemStack, BlockState)` | `Item.method_58404(ItemStack, BlockState)` |

`fallingtree-tombstones.json` redirects both call sites (2 + 1 occurrences).

## What does not work

Tree felling never happens: only the broken log disappears.

```text
TREE_FIXED pos=class_2338{x=30, y=65, z=83} logsBefore=19
TREE_ARRIVED at={32.6,65.2,83.5} yaw=-113.92363
TREE_BROKEN ticks=72
TREE_RESULT logsBefore=19 logsAfter=18
```

The same result was observed on a natural trunk earlier (18 -> 17) and after adding persistent
leaves directly next to the bottom log (19 -> 18). There is no tombstone, NoSuchMethodError or
exception in `server.log`; the mod's mixin config is byte-identical to the original and
`LevelMixin`/`AbstractBlockMixin` apply without warnings. `BlockBreakListener` (a
`PlayerBlockBreakEvents.Before`) is registered by `FallingTreeCommonsImpl.register()`.

Honest status: **break path verified, felling unverified/broken**. Remaining hypotheses, in order:

1. `PlayerBlockBreakEvents.Before` is not fired for this server break path in the converted setup
   (would need a probe listening to the same event);
2. the mod's tree detection rejects the artificial tree (`WHOLE_TREE`, `minimumLeavesAroundRequired=1`);
3. a silent early return inside `TreeHandler`/`FallingTreeCommon` after the conversion.

## Evidence

`client.log`, `server.log` (`server-final.log` is the same file after the run), `commands.txt`.
