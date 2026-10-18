# P41: all three converted samples in one server

Date: 2026-10-18 (Asia/Shanghai). Integration milestone.

## Setup

Instance: `work/instances/fabric-1.21.1-server-all-three`

- Fabric API `0.102.0+1.21.1`
- lithium `0.11.4+1.21.1-patched.jar` (P13 chunk port)
- ironchests `ironchests-safe-aw.jar` (P26 safe CodecDispatch)
- trashslot `trashslot-client-aw.jar` (P29 client bridge build)
- native Balm `21.0.66`

## Result

Boot:

```text
Loaded configuration file for Lithium: 131 options available
Found new data pack ironchests, loading it automatically
Done (4.632s)! For help, type "help"
```

Container contract (two fresh processes):

```text
Done (21.4s) -> place/insert/NBT -> restart -> Done (17.9s) -> 5 diamonds read back
```

`contract/verdict.json`: `passed=true`, all 5 steps true, both runs exit 0.

This is the first run where lithium, ironchests and trashslot (plus Balm) are loaded together in
one dedicated server; the ironchests container persistence still works in that combination.

## Scope

Dedicated server + command API only. No client connection, trash GUI, lithium gameplay or
multiplayer synchronization. Lithium's two mixinStrips and chunk optimization loss remain.

## Evidence

- `server.log` / `server.result.json`
- `contract/verdict.json`
- `contract/step1-place-insert.log`
- `contract/step2-restart-read.log`
- `contract.log`
