# P13: chunk-access port to 1.21.1 — lithium reaches Done

Date: 2026-10-18 (Asia/Shanghai). This continues after P11/P12: the `ChunkHolderExtended` cast
and `ChunkMap.method_17236` tombstone were a **ChunkResult/GenerationChunkHolder API shape
change**, so the mixin implementation itself was ported to 1.21.1. The mixin class is kept (same
name, same `@Overwrite`); it is not a mixin strip.

## What was ported

`me/jellysquid/mods/lithium/mixin/world/chunk_access/ServerChunkManagerMixin`:

- 1.20.1 implementation: own `ChunkHolderExtended` future cache, `ChunkMap.method_17236`
  returning `CompletableFuture<Either<ChunkAccess, Unloaded>>`, tombstone `t3`/`t4`.
- 1.21.1 port: keep the mixin class and `@Overwrite method_12121`, but:
  1. call the vanilla 1.21.1 `ServerChunkManager.method_14134(x,z,status,create)` (returns
     `CompletableFuture<ChunkResult<LevelChunk>>`);
  2. while the future is not done, pump the private chunk task queue via
     `ChunkAccessPump` (reflection on `field_18809.method_18857`; the field type is a
     package-private nested class, so a normal `@Shadow` cannot be used);
  3. join, convert with `ChunkResult.method_57130(null)`, and throw the vanilla
     `IllegalStateException` when `create && chunk == null`.

The reflection helper `top/mcbridge1201/bridge/ChunkAccessPump` is embedded in the mod jar.

During development, the first port (without the queue pump) hung at `Preparing level "world"`
(`server-chunk-port.log`); adding the pump produced a successful manual-inject boot
(`server-chunk-port2.log`), and then the same class was integrated as a rule
(`server-chunkport-rule.log`).

This is a real port, not a strip or a default-returning stub. The old multi-entry cache and
off-thread fast path are **not** reimplemented; that is a performance/optimization loss, not a
save/drop/sync semantic change. It is recorded here and in the rule evidence.

## Commands, exit codes, logs

| # | Step | Exit | Evidence |
|---|---|---|---|
| 1 | `python tools/build_bridges.py --stub work/cb/data/jars/client-1.21.1-intermediary.jar --lib gson --lib datafixerupper --out work/bridges` | 0 | `build-bridges.log` (4 bridges, including `ChunkAccessPump`) |
| 2 | `python tools/build_mixins.py --stub work/remap/server-intermediary.jar --lib <sponge-mixin> --lib work/bridges --out work/mixins` | 0 | `build-mixins.log` |
| 3 | `gradle --no-daemon installDist` in `java/` | 0 | `gradle-install.log` |
| 4 | `mcbridge1201 patch --in <converted lithium> --out lithium-patched-chunkport.jar --rules lithium-degraded.json --rules lithium.json --bridge-dir work/bridges --bridge-dir work/mixins` | 0 | `patch-lithium-chunkport.log` |
| 5 | `python tools/run_server.py --instance work/instances/fabric-1.21.1-server-lithium --log runs/p13-chunk-port/server-chunkport-rule.log --timeout 240` | 0; runner exit 0; `doneSeen=true` | `server-chunkport-rule.log` |
| 6 | Same with commands `forceload add 0 0`, `setblock 0 100 0 minecraft:stone`, `data get block 0 100 0` | 0; runner exit 0; `doneSeen=true` | `server-chunkport-commands.log` |
| 7 | `gradle --no-daemon test --rerun-tasks` | 0 | `gradle-test.log`; 12 tests, 0 failures |

Patch output:

```text
classes changed=4
  rule lithium.explosionmixin.ctor-callback applied 1 time(s)
  rule lithium.poi.serializing-storage-ctor-callback applied 1 time(s)
  rule lithium.poi.serializing-storage-ctor-callback/refmap applied 1 time(s)
  rule lithium.serverchunkmanager.chunkresult-port applied 1 time(s)
  rule walknodeevaluator.checkneighbourblocks.view-to-context applied 2 time(s)
  rule lithium.strip.entity.collisions.movement applied 2 time(s)
  bridges embedded: [top/mcbridge1201/bridge/WalkNodeEvaluatorCheckNeighbourBlocks]
  javac bridges: [me/.../ServerChunkManagerMixin, top/mcbridge1201/bridge/ChunkAccessPump,
                  top/mcbridge1201/bridge/WalkNodeEvaluatorCheckNeighbourBlocks]
  sha256 67013b3bbf079e2c1046b163f0aae1e60bf98c455ac4fbd8e4f8450eb26c02ee
```

## Result

`server-chunkport-rule.log`:

```text
[21:20:36] Preparing level "world"
[21:20:40] Done (4.772s)! For help, type "help"
[21:20:43] Stopping the server
...
ThreadedAnvilChunkStorage: All dimensions are saved
```

`server-chunkport-commands.log`:

```text
Done (4.664s)!
# > forceload add 0 0
Marked chunk [0, 0] in minecraft:overworld to be force loaded
# > setblock 0 100 0 minecraft:stone
Changed the block at 0, 100, 0
# > data get block 0 100 0
The target block is not a block entity
```

So lithium now **BOOTS on the Fabric 1.21.1 dedicated server and loads/saves the world**. This is
`BOOTED`, not a gameplay contract or compatibility pass: no lithium gameplay/client syncing was
exercised, and the two earlier `mixinStrips` remain.

Regression: re-patching ironchests with `container.json` still produces the byte-identical
`7d89d452...bc9a1` jar (`ironchests-patch-recheck.log`).

## Hashes (SHA-256)

| Artifact | SHA-256 |
|---|---|
| `lithium-patched-chunkport.jar` | `67013b3bbf079e2c1046b163f0aae1e60bf98c455ac4fbd8e4f8450eb26c02ee` |
| `server-chunkport-rule.log` | `66ceec9a9aa6dd4330ea0210f66f0dfa5a1e2920cca123ec95a463898e29e8e9` |
| `server-chunkport-commands.log` | `797cfbed990ec061bfbcae3826debd29f1d836b1da9f55b9341dd3f71fd5934a` |
| `patch-lithium-chunkport.log` | `18f37bb4f470cd8840f8fa95b6f3d1bb1a1e124783f43f43a071cd4ad0010cd2` |

## Reproduce

```powershell
$env:JAVA_HOME='C:\Users\27682\Documents\新建文件夹\.toolchain\jdk'
cd java; gradle --no-daemon installDist; cd ..

python tools/build_bridges.py --stub work/cb/data/jars/client-1.21.1-intermediary.jar `
  --lib work/lib/gson-2.11.0.jar `
  --lib work/instances/fabric-1.21.1-server/libraries/com/mojang/datafixerupper/8.0.16/datafixerupper-8.0.16.jar `
  --out work/bridges
python tools/build_mixins.py --stub work/remap/server-intermediary.jar `
  --lib work/instances/fabric-1.21.1-server-lithium/libraries/net/fabricmc/sponge-mixin/0.17.4+mixin.0.8.7/sponge-mixin-0.17.4+mixin.0.8.7.jar `
  --lib work/bridges --out work/mixins

java\build\install\mcbridge1201\bin\mcbridge1201.bat patch `
  --in work/cb/out/lithium/lithium-fabric-mc1.20.1-0.11.4+1.21.1.jar `
  --out work/cb/out/lithium/lithium-patched-chunkport.jar `
  --rules rules/fabric-1.21.1/lithium-degraded.json `
  --rules rules/fabric-1.21.1/lithium.json `
  --bridge-dir work/bridges --bridge-dir work/mixins

python tools/run_server.py --instance work/instances/fabric-1.21.1-server-lithium `
  --log runs/p13-chunk-port/server-chunkport-rule.log --timeout 240
```

## Limits

- Dedicated-server boot/world load only; no lithium gameplay, client GUI/render, or multiplayer.
- The port reduces the chunk-access optimization (no old multi-entry cache / off-thread fast
  path); vanilla correctness is preserved.
- The two explicit `mixinStrips` from P11 remain; lithium is not claimed as fully compatible.
- No game jar, mod jar, or converted artifact is committed.
