# P49: extract `@At.ordinal`

Date: 2026-10-18 (Asia/Shanghai). Parses the injection-point ordinal instead of dropping it.

## Change

- `Injection.atOrdinal` (`Integer`).
- The `@At` visitor reads `ordinal`; `copyAt` preserves it for every method in an injection
  array.
- `Analyzer` counts `mixinAtOrdinals`; `Main` emits `atOrdinals` in `mixins`.
- Synthetic test `parsesAtOrdinal` uses `ordinal = 2`.

## Real data

Converted lithium: `mixinAtTargets=86`, **`mixinAtOrdinals=10`**, unresolved still 3.

This is extraction only: the analyzer does **not** yet count the matching instructions in the
target method and therefore does not fail an out-of-range ordinal. Slice/local capture remain
unparsed.

## Tests

`gradle --no-daemon test --rerun-tasks`: **22/22 pass**.

## Evidence

- `gradle-test.log`
- `install-dist.log`
- `analyze.log`
- `lithium-converted.json`
