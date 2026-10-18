# P11: mixin target-descriptor adaptation (lithium ExplosionMixin + POI storage)

Date: 2026-10-18 (Asia/Shanghai). This continues the lithium line after P10: the
`NoSuchMethodError` from `class_14.method_59` is gone, so the next blockers are Mixin
`@Inject` targets whose constructor descriptors changed. Two are adapted; no mixin is
deleted to hide them.

## What was adapted (adopted)

1. `lithium.explosionmixin.ctor-callback`
   - Target: `net.minecraft.class_1927` (`Explosion`).
   - 1.20.1 constructor: `(Level, Entity, DamageSource, ExplosionBehavior, DDD F Z Explosion$DestructionType)`.
   - 1.21.1 constructor: the same plus `ParticleOptions, ParticleOptions, Holder<SoundEvent>`.
   - The callback body only reads shadow fields; the three new argument slots are appended
     before `CallbackInfo`, existing locals shift by 3, and the `@Inject` target is rewritten
     to the intermediary 13-arg descriptor.
2. `lithium.poi.serializing-storage-ctor-callback`
   - Target: `net.minecraft.class_4180` (`SectionStorage`).
   - 1.20.1 constructor: `(Path, Function, Function, DataFixer, class_4284, boolean, class_5455, class_5539)`.
   - 1.21.1 constructor: `(SimpleRegionStorage, Function, Function, RegistryAccess, ChunkIOErrorReporter, LevelHeightAccessor)`.
   - The callback body only uses `this`; the captured args are replaced with the new ones,
     and the refmap entry `"<init>" -> Lnet/minecraft/class_4180;<init>(... old ...)V` is
     rewritten to the new descriptor. The `@Inject` annotation itself is `method="<init>"`.

The engine support is `mixinCallbackAdaptations` in `RuleSet`/`JarPatcher`, with append and
replace modes, local shifting, `MethodParameters`/`LocalVariableTable` maintenance, annotation
rewrite, and optional refmap rewrite.

## Commands, exit codes, logs

| # | Step | Exit | Evidence |
|---|---|---|---|
| 1 | `gradle --no-daemon installDist` in `java/` | 0 | `gradle-install.log` |
| 2 | `mcbridge1201 patch --in <converted lithium> --out lithium-patched-explosion3.jar --rules rules/fabric-1.21.1/lithium-degraded.json --rules rules/fabric-1.21.1/lithium.json --bridge-dir work/bridges` | 0 | `patch-lithium3.log` |
| 3 | `python tools/run_server.py --instance work/instances/fabric-1.21.1-server-lithium --log runs/p11-lithium-explosion/server-explosion3.log --timeout 240` | 11 (runner); JVM 0; `doneSeen=false` | `server-explosion3.log`, `server-explosion3.result.txt` |
| 4 | `gradle --no-daemon test --rerun-tasks` in `java/` | 0 | `gradle-test.log`; 11 tests, 0 failures |

Patch output:

```text
classes changed=4
  rule lithium.explosionmixin.ctor-callback applied 1 time(s)
  rule lithium.poi.serializing-storage-ctor-callback applied 1 time(s)
  rule lithium.poi.serializing-storage-ctor-callback/refmap applied 1 time(s)
  rule lithium.strip.entity.collisions.movement applied 2 time(s)
  rule walknodeevaluator.checkneighbourblocks.view-to-context applied 2 time(s)
  sha256 44a49bcdf5e2ae2f370c818fcdb1996821a67370fe899ddcc6a117b884b1e05e
```

Patching the same input again with the final installed CLI produced a byte-identical jar
(`patch-lithium-recheck.log`), so the result is deterministic. Re-patching ironchests with
`container.json` also stayed byte-identical (`7d89d452...bc9a1`, `ironchests-patch-recheck.log`),
so the new Mixin rule type did not change existing rules.

## Result

`server-explosion3.log`:

- no `NoSuchMethodError`;
- no `ExplosionMixin` or `SerializingRegionBasedStorageMixin` injection failure;
- the server reaches `Preparing level "world"`, loads 1290 recipes and 1399 advancements;
- next real failure: `ClassCastException: net.minecraft.class_3193 cannot be cast to
  me.jellysquid.mods.lithium.common.world.chunk.ChunkHolderExtended` at
  `class_3215.getChunkBlocking`.

This is **not** a successful boot: `doneSeen=false`, runner exit 11, JVM exit 0.

## Why the next failure is not another descriptor rewrite

CenturyBridge's conversion removed `world.chunk_access.ChunkHolderMixin` from
`lithium.mixins.json` (the target field `field_16425` and `class_3193$class_3724` no longer
exist), but left `world.chunk_access.ServerChunkManagerMixin`, which casts a `ChunkHolder`
to `ChunkHolderExtended`. Two experiments were recorded and **not adopted**:

- Re-adding `ChunkHolderMixin` as-is: `server-readd.log` shows
  `@Shadow field field_16425 was not located in the target class net.minecraft.class_3193`.
- Localizing the shadow field (a private mixin field with lazy init) gets past the cast, but
  then hits the CenturyBridge tombstone `class_3898.method_17236`
  (`server-chunkholder-local2.log`). That changes chunk-future bookkeeping semantics without
  a full port of the 1.21.1 chunk API, so it is not adopted and no mixin strip is used to
  hide it. The next step is a real port of the chunk-access mixin or a non-degrading bridge
  for the tombstone.

## Hashes (SHA-256)

| Artifact | SHA-256 |
|---|---|
| `lithium-patched-explosion3.jar` (adopted) | `44a49bcdf5e2ae2f370c818fcdb1996821a67370fe899ddcc6a117b884b1e05e` |
| `lithium-patched-explosion2.jar` (no refmap rewrite) | `56a5c12424b6adf87fcc81dbeb0faeebdb89dd5cc700cffce4b0f479d213b84c` |
| re-add experiment jar | `4d2a69b4d4383f446b24815b2d7c2b929f94f548484f4bda2effb0e8293c5f61` |
| local-field experiment jar | `31e7bbc725604b0c23b621d76f2f8b8e653a71a18dc93cef815647ceb59d39ed` |
| `server-explosion3.log` | `e1572ac0a83ee0357f05daf43e7d80fa230feae5ddf68686809e03d00788b485` |
| `server-readd.log` | `b9e2fc3368083807173e0cdb8fa0d8ca02ec4830bdb079faf60955fbb16f8f2` |
| `server-chunkholder-local2.log` | `045b573d391938f7b6704415b4509eb4dded7f034a718b26ff15518d16be9fef` |

## Reproduce

```powershell
$env:JAVA_HOME='C:\Users\27682\Documents\新建文件夹\.toolchain\jdk'
cd java; gradle --no-daemon installDist; cd ..

java\build\install\mcbridge1201\bin\mcbridge1201.bat patch `
  --in work/cb/out/lithium/lithium-fabric-mc1.20.1-0.11.4+1.21.1.jar `
  --out work/cb/out/lithium/lithium-patched-explosion3.jar `
  --rules rules/fabric-1.21.1/lithium-degraded.json `
  --rules rules/fabric-1.21.1/lithium.json --bridge-dir work/bridges

python tools/run_server.py --instance work/instances/fabric-1.21.1-server-lithium `
  --log runs/p11-lithium-explosion/server-explosion3.log --timeout 240
```

## Limits

- Dedicated-server startup only; GUI/render/multiplayer remain pending.
- The two mixin adaptations are **not** a claim of lithium compatibility; the next failure is
  a chunk-API shape change plus a CenturyBridge tombstone.
- No game jar, mod jar, or converted artifact is committed; only logs, hashes, rules, and tools.
