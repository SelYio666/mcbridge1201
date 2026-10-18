# P35: refmap-aware `@At` target resolution

Date: 2026-10-18 (Asia/Shanghai). Extends P34's conservative `@At` pass with refmap mapping.

## What changed

- `Injection` records `atRawTarget`.
- `resolveRefmapTarget` now also maps the `@At target` string through the mixin refmap and
  populates `atTargetOwner`/`atTargetName`/`atTargetDesc`/`atTargetField`.
- The scanner test's refmap case now maps both the handler method and the at-target:
  `namedAt()V -> Lnet/minecraft/class_14;method_60()V`.

## Result

Converted lithium after the change:

```text
mixinInjections: 214
mixinAtTargets: 86
mixinInjectionsUnresolved: 3
```

86 at-targets are now resolved instead of skipped; the 3 unresolved entries are still exactly
the known POI/FluidState/Explosion constructor changes, so the added mapping produced no new
false positives.

`gradle --no-daemon test --rerun-tasks`: **18/18 pass**.

## Evidence

- `gradle-test.log`
- `install-dist.log`
- `analyze.log`
- `lithium-converted.json`
