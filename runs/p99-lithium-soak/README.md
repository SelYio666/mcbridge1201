# P99: Lithium four-minute soak

Date: 2026-10-20.

## Setup

Dedicated server (`online-mode=false`, no players), Fabric API + converted Lithium + rebuilt
IronChests + `SoakProbe`, which reports a TPS window and heap usage every 1200 ticks and stops after
4800 ticks (four minutes).

## Result

```text
Done (4.535s)!
SOAK t=60s  tps=17.81 heapUsedMb=261
SOAK t=120s tps=20.00 heapUsedMb=269
SOAK t=180s tps=20.00 heapUsedMb=276
SOAK t=240s tps=20.00 heapUsedMb=282
SOAK_DONE ticks=4800
```

- The first window includes world generation/startup, hence 17.81; every later window is a clean 20.00.
- Heap grows about 7 MB per minute (261 → 282 MB over three minutes), which is ordinary warm-up, not
  an unbounded leak signal at this length.
- No crash report, no exception in `soak.log`/`soak.err`.

## Scope

- Four minutes with no players, no mob AI pressure, no redstone machines; a long-session or
  mob/redstone-heavy soak is still untested.
- `client.log` is this machine's latest client log at collection time and is not part of the soak;
  `soak.log` is the evidence.

## Evidence

`soak.log`.
