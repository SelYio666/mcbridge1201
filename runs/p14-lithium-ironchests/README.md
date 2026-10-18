# P14: lithium + ironchests together — container contract passes

Date: 2026-10-18 (Asia/Shanghai). This combines the two converted samples in one Fabric 1.21.1
dedicated-server instance:

- `lithium-patched-chunkport.jar` (P13: call-site bridge, Explosion/POI mixin targets, chunk
  access port);
- `ironchests-5.0.2-fabric+1.21.1-aw.jar` (P5: NBT signature adaptation + access widener).

The point is to check that the chunk-access port does not break container NBT persistence and
that the two samples can coexist.

## Command and result

```powershell
$env:JAVA_HOME='C:\Users\27682\Documents\新建文件夹\.toolchain\jdk'
python tools/run_contract.py `
  --instance work/instances/fabric-1.21.1-server-lithium-ironchests `
  --out runs/p14-lithium-ironchests
```

Exit code: **0**. Two real server processes (place/insert then restart/read), both reached
`Done`. Verdict:

```json
{
  "steps": {
    "place": true,
    "insert": true,
    "nbt_after_insert": true,
    "nbt_after_restart": true,
    "count_after_restart": true
  },
  "blockDataAfterInsert": "{z: 0, x: 0, id: \"ironchests:iron_chest\", y: 100, Items: [{count: 5, Slot: 0b, id: \"minecraft:diamond\"}]}",
  "blockDataAfterRestart": "{z: 0, x: 0, id: \"ironchests:iron_chest\", y: 100, Items: [{count: 5, Slot: 0b, id: \"minecraft:diamond\"}]}",
  "passed": true
}
```

Logs:

- [run.txt](run.txt) — both server-run JSON results
- [step1-place-insert.log](step1-place-insert.log) — place + insert + `data get block`
- [step2-restart-read.log](step2-restart-read.log) — restart + read back
- [verdict.json](verdict.json)

Hashes (SHA-256):

| File | SHA-256 |
|---|---|
| `verdict.json` | `db94700abaa63997b5c1d604518eaaee676435c168a7fc854cd42cf0a345f05c` |
| `step1-place-insert.log` | `bb6beb117640ff248a0f4e01ac61311ba3c204c792314eded8de3b7e67202892` |
| `step2-restart-read.log` | `b044b21449c78e2bb8559611e920fd750d66fbabd6a700b05f29531e7fe1f80b` |
| `run.txt` | `6fceae8204c4baaf2bdaa0fd74478f0c233adeffa825895cc47fdc7b55eafd2e` |

## Scope

This is a **dedicated server + command API** contract (place/insert/NBT/restart/readback). It
does not verify GUI, rendering, player interaction, drops, or two-client synchronization. It
also does not restore lithium's reduced chunk-cache optimization.

## Reproduce

Copy the P13 lithium jar and the P5 ironchests AW jar into a fresh Fabric 1.21.1 server
instance, then run the command above. The instance used here is
`work/instances/fabric-1.21.1-server-lithium-ironchests` (local only, not committed).
