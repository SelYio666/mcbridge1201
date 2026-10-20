# P95: AppleSkin status-effect tooltip path

Date: 2026-10-20. Follow-up to the AppleSkin HUD verification (p89).

## Blocker

AppleSkin 2.5.2 reads a food's status effects through the 1.20.1
`FoodComponent.getStatusEffects()` (tombstone `t5`). 1.21.1 stores a
`List<FoodComponent.StatusEffectEntry>` (`comp_2495()`, entry accessors `comp_2496`/`comp_2497`), so
the converted tooltip loop could not run.

## Fix

`AppleSkinFoodBridge.statusEffects(class_4174)` rebuilds the old
`List<Pair<StatusEffect, Float>>` from the 1.21.1 entries; `appleskin-food.json` redirects tombstone
`t5` to it. This is the same value/shape AppleSkin's tooltip loop already expects, not a stub.

## Contract probe (real client, golden apple)

```text
APPLESKIN_TOOLTIP hunger=4 sat=9.6 healthInc=0.0
APPLESKIN_EFFECTS size=2 probability=1.0
```

- `hunger=4 sat=9.6` — the default food values the HUD path already produced;
- `size=2` — golden apple's two effects (absorption, regeneration) are returned with the correct
  probability; if `t5` were still a tombstone the call would throw `UnsupportedOperationException`;
- `healthInc=0.0` — expected for a full-health player (the estimate only counts missing health).

## Scope

- Verified: the `FoodHelper` code path that uses `t5` runs end to end, and the rebuilt effect list
  has the right size/probability.
- Not verified: an actual in-game tooltip hover with a real mouse; the visible tooltip layout and
  effect lines were not screenshotted.

## Evidence

`client.log`.
