# P24: reusable chunk-stress contract tool

Date: 2026-10-18 (Asia/Shanghai). Turns the P23 manual stress run into a reproducible tool.

## Tool

`tools/run_chunk_stress.py`:

```powershell
python tools/run_chunk_stress.py `
  --instance work/instances/fabric-1.21.1-server-lithium `
  --out runs/p24-chunk-stress-tool --radius 7
```

It runs two server processes:

1. `forceload remove all`, then `forceload add -112 -112 112 112` (225 chunks), set diamond/
   emerald blocks at the far corners, `save-all flush`, stop.
2. Restart, re-add the force-load region, `execute if block` both corners (`STRESS_OK_A/B`),
   `save-all flush`, stop.

The tool writes `step1.log`, `step2.log`, `step1.result.json`, `step2.result.json` and
`verdict.json`, and exits 0 only when both runs reached `Done` and both markers appear.
`--command-delay` is set to 2.5 s for step 1 because a `/forceload add` followed immediately by
`/setblock` can race the asynchronous chunk load; the first tool version failed exactly that way
and is preserved in the run history.

## Result

```json
{
  "chunksExpected": 225,
  "chunksMarked": 225,
  "steps": {
    "step1Done": true, "step1Exit0": true,
    "step2Done": true, "step2Exit0": true,
    "forceloadMarked": true,
    "markerA": true, "markerB": true
  },
  "passed": true
}
```

`verdict.json` and `run.txt` are the evidence; logs are in this directory.

Scope remains dedicated server + command API; client GUI/player/multiplayer are not covered.
