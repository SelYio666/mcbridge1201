# P108: combined five-minute stress soak

Date: 2026-10-20.

## Setup

Dedicated server with Fabric API + converted Lithium + rebuilt IronChests + `SoakProbe`.
RCON: midnight, clear weather, force-load 168 chunks (`forceload add 0 0 200 200`), summon 40
zombies, and the adjacent observer redstone clock from P105 is present in the same world.

## Result

```text
[22:59:37] [Rcon: Marked 168 chunks ... from [0, 0] to [12, 12] to be force loaded]
summoned 40 zombies
SOAK t=30s  tps=15.75 heapUsedMb=464   (chunk generation window)
SOAK t=60s  tps=20.00 heapUsedMb=565
SOAK t=90s  tps=20.00 heapUsedMb=645
SOAK t=120s tps=20.00 heapUsedMb=305
SOAK t=150s tps=20.00 heapUsedMb=376
SOAK t=180s tps=20.00 heapUsedMb=449
SOAK t=210s tps=20.00 heapUsedMb=525
SOAK t=240s tps=20.00 heapUsedMb=600
SOAK t=270s tps=20.00 heapUsedMb=260
SOAK t=300s tps=19.98 heapUsedMb=348
SOAK_DONE ticks=6000
```

With 168 loaded chunks, 40 zombies and a redstone clock, every window after the initial chunk
generation stays at 20.00 TPS; the last window is 19.98. Heap sawtooths between 260 and 645 MB with
no monotonic climb. No crash or exception.

## Scope

- Both the zombie count and the observer clock activity are taken from the RCON actions and the
  standard construction; neither is sampled frame by frame.
- Five minutes, no players; multi-hour runs are still untested.
- `setblock` reported "Could not set" for both observers because they already existed from P105.

## Evidence

`soak.log`.
