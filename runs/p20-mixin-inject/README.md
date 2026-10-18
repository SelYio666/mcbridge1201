# P20: mixin injection-target extraction and conservative resolution

Date: 2026-10-18 (Asia/Shanghai). Static-analysis improvement.

## What changed

- `ArtifactScanner` now records each mixin handler's `@Inject`, `@Redirect`,
  `@ModifyConstant`, `@ModifyVariable`, `@ModifyArg`, `@ModifyArgs`,
  `@ModifyExpressionValue`, `@ModifyReturnValue`, `@WrapOperation` and
  `@WrapWithCondition` `method` values (single value or array, optional owner prefix).
- `Analyzer.Result` gained `mixinInjections` / `mixinInjectionsUnresolved` and the
  `unresolvedMixinInjections` list; a non-empty list now contributes to `blocked_static`.
- The resolver is deliberately conservative: only intermediary method names (`method_*`)
  with an explicit descriptor are checked against the 1.21.1 index. Named/Yarn targets,
  refmap indirection, and constructors (`<init>`) are not resolved and are left out rather
  than guessed.

## Tests

`gradle --no-daemon test --rerun-tasks`: **15/15 pass** (exit 0).

- `MixinInjectionScanTest` builds a synthetic `@Mixin` class with
  `@Inject(method = "method_59()V")` and asserts the scanner extracts
  `net/minecraft/class_14`, `method_59`, `()V`.
- `AnalyzerCoreTest.reportsMixinInjectionTargetsMissingInTheTargetIndex` builds a target
  index with `method_59()V`, supplies one existing and one missing injection target, and
  asserts the missing one is reported.

## Real data

Analyzed the converted lithium jar (`work/cb/out/lithium/lithium-fabric-mc1.20.1-0.11.4+1.21.1.jar`) with
the 1.21.1 intermediary index:

```text
mixins: 202
mixinInjections: 214
mixinInjectionsUnresolved: 0
```

The zero is expected for this sample: lithium's `ExplosionMixin` and POI storage targets
are written with Yarn names and/or constructors, which this conservative pass skips. The
extraction itself is exercised (214 targets), and the missing-target resolution is pinned
by the unit test.

## Scope / next

This is a static check only; it does not replace runtime mixin verification. A full check
needs refmap/named-descriptor mapping and constructor indexing in `TargetIndex`, which
remain open.

Evidence: `analyze-converted.log`, `lithium-converted.json`, `gradle-test.log`.
