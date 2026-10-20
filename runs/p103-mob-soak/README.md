# P103: Lithium mob-pressure soak

Date: 2026-10-20.

## Setup

Dedicated server with Fabric API + converted Lithium + `SoakProbe`. RCON sets midnight and clear
weather (so zombies do not burn), then summons 40 zombies around spawn (20..34, 69, 76..88). The
probe reports TPS and heap every 600 ticks and finishes at 3600 ticks (three minutes).

## Result

```text
time: Set the time to 18000
weather: Set the weather to clear
summoned 40
SOAK t=30s  tps=17.77 heapUsedMb=307
SOAK t=60s  tps=20.00 heapUsedMb=221
SOAK t=90s  tps=20.00 heapUsedMb=273
SOAK t=120s tps=20.00 heapUsedMb=326
SOAK t=150s tps=20.00 heapUsedMb=226
SOAK t=180s tps=20.00 heapUsedMb=278
SOAK_DONE ticks=3600
```

- Every measured window after startup is a clean 20.00 TPS with 40 zombies ticking and pathfinding.
- Heap oscillates 221-326 MB (normal GC sawtooth), no upward runaway.
- No crash or exception in `soak.log`.

Post-run RCON check: `data get entity @e[type=minecraft:zombie,limit=1] Health` answered
`Zombie has the following entity data: 20.0f`, so mobs were still alive at the end.

## Scope

- The exact survivor count at the end was not measured (RCON `execute as` feedback is not returned
  in this setup); 40 were summoned and at least one was alive after the run.
- No player was connected; zombie AI targeted nobody, so this is pathfinding/ticking pressure, not
  combat pressure.
- Three minutes only; multi-hour runs and redstone machines remain untested.

## Evidence

`soak.log`.
