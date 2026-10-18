# P12 analysis: chunk access is an API-shape change, not a descriptor change

Date: 2026-10-18. This is the analysis behind stopping at the `ChunkHolderExtended` cast in
`runs/p11-lithium-explosion/server-explosion3.log`; no code was adopted from this analysis.

## What fails

`me/jellysquid/mods/lithium/mixin/world/chunk_access/ServerChunkManagerMixin#getChunkBlocking`
is an `@Overwrite` of `ServerChunkManager.method_12121(x, z, status, create)`. After the local
`ChunkHolder` cast, it does:

1. `((ChunkHolderExtended) holder).getFutureByStatus(status.method_16559())`;
2. if there is no immediately usable future and `status` is at least `LIGHT`, calls the
   CenturyBridge tombstones:
   - `t3(ChunkMap, ChunkHolder, ChunkStatus)` — old `ChunkMap.method_17236`;
   - `t4(ChunkHolder, CompletableFuture, String)` — old future-tracking helper.

The tombstone `t3` is what `server-chunkholder-local2.log` hits. `ChunkHolderMixin`, which
implements `ChunkHolderExtended`, was removed from `lithium.mixins.json` by the conversion; the
remaining consumer cast fails first (`server-explosion3.log`).

## Why re-adding / localizing the mixin is not enough

- Re-adding `ChunkHolderMixin` as-is fails because its `@Shadow field_16425` does not exist in
  1.21.1 `class_3193` (`server-readd.log`).
- Localizing the shadow field (private mixin field + lazy init) gets past the cast, but then
  `t3` is called (`server-chunkholder-local2.log`).
- `t3` cannot be fixed with a descriptor rewrite: 1.20.1 `ChunkMap.method_17236(ChunkHolder,
  ChunkStatus)` returns `CompletableFuture<Either<ChunkAccess, ChunkHolder.Unloaded>>` and uses
  `ChunkHolder.getFutureForStatus`, `ChunkStatus.progressTo/isAtLeast`, and the old
  `class_3193$class_3724`. 1.21.1 removed that method and the `Unloaded` type; its futures are
  `CompletableFuture<ChunkResult<...>>` (`class_9259`), and `ChunkHolder` exposes separate
  futures. Even a synthetic `t3` returning a 1.21.1 future would then fail the mixin's
  `checkcast Either` a few instructions later.

So the fix is a real port of `ServerChunkManagerMixin.getChunkBlocking` +
`ChunkHolderExtended` to the 1.21.1 `ChunkResult`/`ChunkHolder` API (or an equivalent vanilla
fallback that is explicitly recorded), not a call-site or mixin-target descriptor rule.

## Evidence commands

```powershell
$env:JAVA_HOME='C:\Users\27682\Documents\新建文件夹\.toolchain\jdk'
javap -p -c -classpath work/remap/client-1.20.1-intermediary.jar net.minecraft.class_3898
javap -p -c -classpath work/remap/client-1.21.1-intermediary.jar net.minecraft.class_3898
javap -p -c -classpath work/cb/out/lithium/lithium-patched-explosion3.jar `
  me.jellysquid.mods.lithium.mixin.world.chunk_access.ServerChunkManagerMixin
```

The raw `javap` dumps are intentionally not committed (large generated text); the conclusions
above are reproducible with the three commands.
