# P93: Clumps orb merging (companion bridge)

Date: 2026-10-20. Follow-up to the six-mod expansion report.

## Blocker

The converter removed Clumps' `MixinExperienceOrb` (flagged load-bearing), so the converted jar no
longer merges experience orbs: two orbs (3 and 7) stay separate forever.

## What was tried and rejected

1. Reusing vanilla `ExperienceOrbEntity.canMerge` via reflection is wrong for Clumps: 1.21.1 only
   merges orbs that have the **same value** and the **same 40-tick age phase**
   (`(orb.age - other.age) % 40 == 0 && orb.value == other.value`), which is exactly the restriction
   Clumps removes. Measured: `canMerge=false` for orbs of value 3 and 7 at the same position.
2. Reusing vanilla `merge(orb)` is also wrong: it adds an unrelated counter and takes
   `min(value)` of the two orbs, so 3 + 7 produced a surviving orb of **3**, not 10.

## Implemented

`java/src/compat-clumps/java/probe/ClumpsMerge.java` (built by
`tools/build_clumps_companion.py`) is a small server-side companion mod:

- every 20 server ticks it collects experience orbs per world;
- orbs within 2 blocks (squared distance 4.0) are combined;
- the survivor's value field (`field_6159`) is set to the saturated sum;
- the other orb is discarded with `Entity.discard()` (`method_31472`).

It is installed next to the converted Clumps jar; no client install is needed. Ships as source +
build script, no jars in the repository.

## Fixture

A dedicated server (fresh world, `online-mode=false`) with a probe that spawns two orbs of value 3
and 7 at the same position next to a loaded entity, then reports at tick 300.

Control (no companion):

```text
ORB_AFTER count=2 total=91 aValue=3 bValue=7 ... value=3 value=7
```

Companion installed (jar built by `tools/build_clumps_companion.py`):

```text
ORB_AFTER count=1 total=9 aValue=10 bValue=7 aPos=7.5,-36.5,40.5 value=10
```

## Scope

- The merge runs on the server tick, not inside `ExperienceOrbEntity.tick` like the original mixin;
  pickup animation/merging cadence therefore differs slightly.
- 2 blocks is a fixed constant (the original Clumps radius is configurable); it is documented in the
  source.
- The companion does not read Clumps' config file.

## Evidence

`anchor.log` (control), `companion.log` (companion), earlier diagnostic logs in the same directory.
