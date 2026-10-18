# P21: refmap-aware mixin injection targets (catches the known constructor changes)

Date: 2026-10-18 (Asia/Shanghai). Extends P20.

## What changed

- `ArtifactScanner` now reads the mixin config's `refmap`, loads its `mappings` table, and
  applies it to each handler's `@Inject`/`@Redirect`/... `method` target.
- `Injection` records `rawTarget`, `targetOwner`, `targetName`, `targetDesc`.
- Refmap values of the form `Lnet/minecraft/class_X;method_y(desc)V` populate the owner;
  this also works for constructors.
- `Analyzer` now checks constructors (`<init>`) as well as `method_*` targets, and uses the
  refmap owner when present. A missing/mismatched constructor descriptor is reported.
- `Main` emits `mixins.injections` and `mixins.unresolvedInjections` in the analyze JSON and
  the generated static matrix column.

## Tests

`gradle --no-daemon test --rerun-tasks`: **16/16 pass** (exit 0).

New: `MixinInjectionScanTest.mapsNamedInjectionTargetThroughRefmap` builds a config with
`"refmap":"test.refmap.json"`, a `named()V` annotation target, and a refmap entry
`named()V -> Lnet/minecraft/class_14;method_59()V`; it asserts the scanner ends up with
`targetOwner=class_14`, `targetName=method_59`, `targetDesc=()V`.

## Real validation

Analyzed converted lithium (`lithium-fabric-mc1.20.1-0.11.4+1.21.1.jar`) with the 1.21.1
intermediary index:

```text
mixins: 202
mixinInjections: 214
mixinInjectionsUnresolved: 3
```

The 3 are exactly the known constructor changes (matching the P11/P13 blockers):

```text
net/minecraft/class_4180.<init>(Path, Function, Function, DataFixer, class_4284, Z,
    class_5455, class_5539)V   (POI/storage)
net/minecraft/class_3610.<init>(class_3611, ImmutableMap, MapCodec)V  (FluidState)
net/minecraft/class_1927.<init>(class_1937, class_1297, class_1282, class_5362, D, D, D, F, Z,
    class_1927$class_4179)V     (Explosion)
```

This is the first static-analysis result that independently rediscovers those runtime
blockers before boot.

## Scope

Static only; no game launch. The check is only exact descriptor existence in the 1.21.1
index; ordinal/slice/local capture and non-refmap named targets remain out of scope.

Evidence: `gradle-test.log`, `install-dist.log`, `analyze-converted.log`,
`lithium-converted.json`.
