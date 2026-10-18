# P10: call-site signature adaptation (lithium `class_14.method_59`)

Date: 2026-10-18 (Asia/Shanghai). Scope: implement and exercise a call-site signature
adaptation rule for `WalkNodeEvaluator.checkNeighbourBlocks` and use lithium 0.11.4 as the
acceptance sample. No game jar, mod jar, or converted artifact is committed.

## Commands, exit codes, logs

| # | Step | Command (abridged; `JAVA_HOME` = toolchain JDK 21) | Exit | Log / evidence |
|---|---|---|---|---|
| 1 | Body-preserving remap of 1.20.1 client (to inspect the old method body) | `mcbridge1201 remap-jar --in work/cb/data/jars/client-1.20.1-obf.jar --out work/remap/client-1.20.1-intermediary.jar --mappings work/cb/data/mappings/intermediary-1.20.1.tiny` | 0 | `remap-client-1.20.1.log` |
| 2 | Body-preserving remap of 1.21.1 client (to inspect the new method body) | `mcbridge1201 remap-jar --in work/target/client-1.21.1.jar --out work/remap/client-1.21.1-intermediary.jar --mappings work/cb/data/mappings/intermediary-1.21.1.tiny` | 0 | `remap-client-1.21.1.log` |
| 3 | Compile Java-source bridges against the 1.21.1 intermediary stub | `python tools/build_bridges.py --stub work/cb/data/jars/client-1.21.1-intermediary.jar --lib work/lib/gson-2.11.0.jar --lib work/instances/fabric-1.21.1-server/libraries/com/mojang/datafixerupper/8.0.16/datafixerupper-8.0.16.jar --out work/bridges` | 0 | `build-bridges.log`, `bridge-javap.txt` |
| 4 | Patch lithium with the call-site rule + recorded mixin strips | `mcbridge1201 patch --in work/cb/out/lithium/lithium-fabric-mc1.20.1-0.11.4+1.21.1.jar --out work/cb/out/lithium/lithium-patched-callsite.jar --rules rules/fabric-1.21.1/lithium-degraded.json --rules rules/fabric-1.21.1/lithium.json --bridge-dir work/bridges` | 0 | `patch-lithium.log` |
| 5 | Embed the javac-compiled bridge with the standalone injector | `python tools/inject_bridges.py --jar work/cb/out/lithium/lithium-patched-callsite.jar --out work/cb/out/lithium/lithium-patched-final.jar --classes work/bridges --replace top/mcbridge1201/bridge/WalkNodeEvaluatorCheckNeighbourBlocks` | 0 | `inject-bridges.log` |
| 6 | Boot Fabric 1.21.1 dedicated server with patched lithium | `python tools/run_server.py --instance work/instances/fabric-1.21.1-server-lithium --log runs/p10-lithium-signature/server-callsite.log --timeout 240` | 11 (runner; JVM 1) | `server-callsite.log`, `server-callsite.result.txt`, `verdict.json` |
| 7 | Java unit tests | `gradle --no-daemon test` in `java/` | 0 | `gradle-test.log`; 8 tests, 0 failures |

## Patch result

```text
patched lithium-fabric-mc1.20.1-0.11.4+1.21.1.jar -> lithium-patched-callsite.jar (classes changed=2)
  rule lithium.strip.entity.collisions.movement applied 2 time(s)
  rule walknodeevaluator.checkneighbourblocks.view-to-context applied 2 time(s)
  bridges embedded: [top/mcbridge1201/bridge/WalkNodeEvaluatorCheckNeighbourBlocks]
  javac bridges: [top/mcbridge1201/bridge/WalkNodeEvaluatorCheckNeighbourBlocks]
  sha256 0f383be3f18fbe5dc47ba5afa9d275d5f658076e953118af96d32ee4b4d2824f
```

The two rewritten call sites are `PathNodeCache.getNodeTypeFromNeighbors` and
`mixin/ai/pathing/AbstractBlockStateMixin.init`. `javap -c` on the patched jar shows:

```text
260: invokestatic  top/mcbridge1201/bridge/WalkNodeEvaluatorCheckNeighbourBlocks.checkNeighbourBlocks:
     (Lnet/minecraft/class_1922;Lnet/minecraft/class_2338$class_2339;Lnet/minecraft/class_7;)
     Lnet/minecraft/class_7;
```

No exact `net/minecraft/class_14.method_59(BlockView, MutableBlockPos, BlockState)` call remains
in the patched jar. Patching the same input again with the final installed CLI produced a
byte-identical jar (SHA-256 `0f383be3...d2824f`), so the result is deterministic; log:
`lithium-patch-recheck.log`.

Regression check: re-patching ironchests with `rules/fabric-1.21.1/container.json` (same
`--client-jar`/`--mappings`/DFU inputs) produced **byte-identical** output, SHA-256
`7d89d4529899dd4c6b71b2aed0b0dc38cf1915b8bb8af075716ab5a92b4bc9a1`, so the new call-site
mechanism did not change existing rules. Log: `ironchests-patch-recheck.log`.

## Boot result

Before (baseline, `runs/p6-lithium/server.log`):

```text
NoSuchMethodError: 'net.minecraft.class_7 net.minecraft.class_14.method_59(
  net.minecraft.class_1922, net.minecraft.class_2338$class_2339, net.minecraft.class_7)'
  at net.minecraft.class_4970$class_4971.handler$zij001$lithium$init
```

After (`server-callsite.log`):

- `NoSuchMethodError` is absent; the initializer that used to fail runs.
- Boot advances to the next real failure: lithium's `world.explosions.ExplosionMixin` cannot
  find its `@Inject` target because the 1.21.1 `Explosion` constructor changed
  (`class_1927.<init>(Level, Entity, DamageSource, Explosion.BlockInteraction, double, double,
  double, float, boolean, Explosion.BlockInteraction)` is gone). This is a mixin-target change,
  not a call-site descriptor rewrite; it is left as the next unresolved item.
- `doneSeen=false`, runner exit 11, JVM exit 1. This is the expected "next failure" outcome, not
  a successful boot. The generated check `no-nsm-check.txt` records `NoSuchMethodError` matches = 0
  in the new log and the first `InvalidInjectionException` line.

## Artifact hashes (SHA-256)

| Artifact | SHA-256 |
|---|---|
| converted lithium `lithium-fabric-mc1.20.1-0.11.4+1.21.1.jar` | `2a94fff311bf5b30d0890865f4016f4a4252d9169129fbe333a5962d3cd3b52b` |
| patched `lithium-patched-callsite.jar` | `0f383be3f18fbe5dc47ba5afa9d275d5f658076e953118af96d32ee4b4d2824f` |
| final (injected) `lithium-patched-final.jar` | `4d9e5374e01d5ce51e0ded94293c307bfda7c0d33a43ccaf28b85be0320a9822` |
| compiled bridge `WalkNodeEvaluatorCheckNeighbourBlocks.class` | `679ed5ac5d33cd8e88caf517439e25d84df214323196593fcbadf345789e6ead` |

## Reproduce

```powershell
$env:JAVA_HOME='C:\Users\27682\Documents\新建文件夹\.toolchain\jdk'
cd java; gradle --no-daemon installDist; cd ..

python tools/build_bridges.py --stub work/cb/data/jars/client-1.21.1-intermediary.jar `
  --lib work/lib/gson-2.11.0.jar `
  --lib work/instances/fabric-1.21.1-server/libraries/com/mojang/datafixerupper/8.0.16/datafixerupper-8.0.16.jar `
  --out work/bridges

java\build\install\mcbridge1201\bin\mcbridge1201.bat patch `
  --in work/cb/out/lithium/lithium-fabric-mc1.20.1-0.11.4+1.21.1.jar `
  --out work/cb/out/lithium/lithium-patched-callsite.jar `
  --rules rules/fabric-1.21.1/lithium-degraded.json `
  --rules rules/fabric-1.21.1/lithium.json `
  --bridge-dir work/bridges

python tools/inject_bridges.py --jar work/cb/out/lithium/lithium-patched-callsite.jar `
  --out work/cb/out/lithium/lithium-patched-final.jar --classes work/bridges `
  --replace top/mcbridge1201/bridge/WalkNodeEvaluatorCheckNeighbourBlocks

# instance: copy of work/instances/fabric-1.21.1-server with ironchests removed and the
# final lithium jar in mods/
python tools/run_server.py --instance work/instances/fabric-1.21.1-server-lithium `
  --log runs/p10-lithium-signature/server-callsite.log --timeout 240
```

## Limits

- Only dedicated-server startup was exercised. GUI/render/multiplayer remain pending.
- The bridge does not call the new `PathfindingContext` overload: `PathfindingContext` can only
  be constructed from `(CollisionGetter, Mob)`, while the old call sites pass an arbitrary
  `BlockGetter` (lithium's `SingleBlockBlockView` is not a `CollisionGetter` and has no entity).
  The bridge ports the old 1.20.1 neighbour scan exactly; this is recorded in the rule evidence.
- The rule only applies to direct calls and method handles in the top-level jar. Nested-jar call
  sites are not covered by the external-bridge embedding (same limitation as generated bridges).
