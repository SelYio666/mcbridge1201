# P27: combined lithium + safe-CodecDispatch ironchests contract

Date: 2026-10-18 (Asia/Shanghai). Regression check for P26 in the P14 combined instance.

## Setup

Instance: `work/instances/fabric-1.21.1-server-lithium-ironchests`

- lithium `lithium-0.11.4+1.21.1-patched.jar` (P13 chunk-port build)
- ironchests `ironchests-safe-aw.jar` built in P26 (javac `CodecDispatch`, no
  `CodecDispatch$Guard`, access widener injected)

## Result

`tools/run_contract.py` two-process container contract:

```text
Done (26.7s) -> setblock/insert/NBT -> restart -> Done (17.0s) -> 5 diamonds read back
```

`verdict.json`: `passed=true`; all 5 steps true; both processes `doneSeen=true`, exit 0.
This shows the P26 safe `CodecDispatch` does not break the lithium + ironchests coexistence
path that P14 established.

Scope: dedicated server + command API only; no client/GUI/player/multiplayer.

## Evidence

- `run.txt`
- `step1-place-insert.log`
- `step2-restart-read.log`
- `verdict.json`
