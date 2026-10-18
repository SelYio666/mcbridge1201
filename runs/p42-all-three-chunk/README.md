# P42: 225-chunk stress with all three converted samples

Date: 2026-10-18 (Asia/Shanghai). Extends P41's coexistence check to the lithium chunk path.

## Setup

Same `fabric-1.21.1-server-all-three` instance as P41:

- lithium P13 chunk-port
- P26 safe-Codec ironchests
- P29 trashslot + native Balm 21
- Fabric API

## Result

`tools/run_chunk_stress.py --radius 7`:

```text
chunksExpected: 225
chunksMarked: 225
step1Done/Exit0: true
step2Done/Exit0: true
forceloadMarked: true
markerA/markerB: true
passed: true
```

Two processes, exit 0; far-corner blocks persist across the restart while all three mods are
loaded.

## Scope

Dedicated server + command API; no client/GUI/player/multiplayer. Lithium's mixinStrips and
chunk optimization loss remain.

## Evidence

- `run.txt`
- `step1.log`, `step2.log`
- `verdict.json`
