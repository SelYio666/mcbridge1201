# P23: lithium chunk-access stress (224 force-loaded chunks, save/restart)

Date: 2026-10-18 (Asia/Shanghai). Runtime verification of the P13 chunk port beyond the
single-chunk command probe.

## Scenario

Instance: `work/instances/fabric-1.21.1-server-lithium`, with
`lithium-0.11.4+1.21.1-patched.jar` (P13 chunk-port build).

Step 1:
- `/forceload add -112 -112 112 112` -> **224 chunks** marked (`[-7,-7]` to `[7,7]`)
- `/setblock 112 100 112 minecraft:diamond_block`
- `/setblock -112 100 -112 minecraft:emerald_block`
- `/save-all flush`; server stops cleanly

Step 2 (new JVM):
- `/forceload add -112 -112 112 112` -> "No chunks were marked" (the force-load set persisted)
- `/execute if block 112 100 112 minecraft:diamond_block run say STRESS_OK_A`
- `/execute if block -112 100 -112 minecraft:emerald_block run say STRESS_OK_B`

Both commands printed `STRESS_OK_A` / `STRESS_OK_B`; server reached `Done` in both runs and
exited 0.

## Why it matters

The P13 port replaced lithium's chunk access with `ServerChunkManager.method_14134` plus
`ChunkAccessPump`; the earlier probe only touched a small area. This run force-loads 224 chunks
in a 15x15 region, writes blocks at the far corners, saves, restarts, and reads them back. It
exercises the port on a larger chunk set and confirms the world save/load path.

## Scope

Dedicated server + command API only. No client connection, GUI, player interaction, mob AI or
multiplayer synchronization; the chunk optimization loss (no old multi-entry cache/off-thread
fast path) remains.

## Evidence

- `step1.log` / `step1.result.txt`
- `step1b.log` / `step1b.result.txt` (large forceload + far blocks)
- `step2.log` / `step2.result.txt` (restart + assertions)
- `verdict.json`
