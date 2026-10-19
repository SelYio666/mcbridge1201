# P84: lithium TPS sample — 20.03 over 60 seconds with 289 chunks

Date: 2026-10-19 (Asia/Shanghai). A concrete stability sample for the lithium port.

## Setup

Dedicated Fabric server (Java 21) with `lithium-final.jar` (the ported 1.21.1 lithium) and a probe
that force-loads a 17x17 chunk area and measures the average TPS over 1200 ticks.

## Result

```text
TPS_START loaded=289/289
TPS_AVG tps=20.03 ticks=1200 seconds=59.92
```

- 289/289 chunks loaded through the chunk-access path lithium mixes into;
- 1200 ticks took 59.92 s → **20.03 TPS**, no tick loss over the minute.

## Scope

- single 60-second sample, no players connected;
- no mob AI, redstone, or multi-hour soak;
- this is a TPS sanity check, not a full performance benchmark.

## Evidence

- `server.log`, `compile.log`, `TpsProbe.java`, `tpsprobe.jar`
