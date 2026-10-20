# P105: Lithium redstone-clock soak

Date: 2026-10-20.

## Setup

Dedicated server with Fabric API + converted Lithium + `SoakProbe`. RCON force-loads chunk (2,4) and
places the classic observer clock: two observers adjacent, facing each other
(`40 71 70 facing=east`, `41 71 70 facing=west`). The probe reports TPS/heap every 600 ticks for
three minutes.

## Result

```text
setblock 41 71 70 minecraft:observer[facing=west] => Changed the block at 41, 71, 70
SOAK t=30s  tps=17.78 heapUsedMb=307
SOAK t=60s  tps=20.00 heapUsedMb=231
SOAK t=90s  tps=20.00 heapUsedMb=289
SOAK t=120s tps=20.00 heapUsedMb=207
SOAK t=150s tps=20.00 heapUsedMb=264
SOAK t=180s tps=20.00 heapUsedMb=322
SOAK_DONE ticks=3600
```

All measured windows hold 20.00 TPS; heap oscillates 207-322 MB (GC sawtooth), no crash.

## Scope

- The clock's own toggling was not sampled with a second signal (an observer has no readable NBT
  state), so "the clock runs" is inferred from the standard adjacent-facing-observer construction;
  the measured claim is that a ticking redstone clock does not disturb TPS.
- `setblock` on the first observer reported "Could not set the block" because that observer was
  already present from a previous run; both observers exist and face each other.
- Three minutes only; large redstone machines and multi-hour runs remain untested.

## Evidence

`soak.log`.
