# P34: `@At` target extraction (conservative)

> P35 adds refmap mapping for the at-target; the converted lithium result becomes 86 at-targets
> (0 unresolved new) instead of 0. This P34 file is retained as the conservative step.

Date: 2026-10-18 (Asia/Shanghai). Extends P21/P22 injection analysis to the annotation's
injection-point target.

## What changed

- `Injection` now records `atValue`, `atTargetOwner`, `atTargetName`, `atTargetDesc`,
  `atTargetField`.
- The mixin scanner parses nested `@At(value=..., target=...)` annotations (single or array)
  attached to `@Inject`/`@Redirect`/... handlers, including multiple `method` entries.
- `Analyzer` checks `@At` INVOKE/FIELD targets against the 1.21.1 index when they are
  intermediary (`method_*`/`field_*`); missing members are reported in
  `unresolvedMixinInjections`.
- New count `mixinAtTargets`; `Main` emits it in the analyze JSON.

The check is conservative: named/Yarn `@At` targets and non-`INVOKE`/`FIELD` points are
skipped rather than guessed.

## Tests

`gradle --no-daemon test --rerun-tasks`: **18/18 pass**.

- `MixinInjectionScanTest` now includes `@At(INVOKE, Lnet/minecraft/class_14;method_59()V)`
  and asserts the parsed at-target;
- `AnalyzerCoreTest` adds an at-target that does not exist in the synthetic index and asserts
  it appears in `unresolvedMixinInjections` (alongside the method-level missing target).

## Real data

Converted lithium:

```text
mixins: 202
mixinInjections: 214
mixinAtTargets: 0
mixinInjectionsUnresolved: 3
```

`mixinAtTargets=0` is expected: lithium's `@At` targets use Yarn names/refmap indirection,
which this conservative pass does not map. The three unresolved entries are still the known
constructor changes (POI/FluidState/Explosion), so the new pass adds no false positives here.

## Scope

Static only; no runtime mixin verification. ordinal/slice/local capture and named `@At`
targets remain out of scope.

Evidence: `gradle-test.log`, `install-dist.log`, `analyze.log`, `lithium-converted.json`.
