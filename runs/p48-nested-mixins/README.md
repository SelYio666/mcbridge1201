# P48: nested-jar mixin config expansion

Date: 2026-10-18 (Asia/Shanghai). The scanner now reads mixin configs inside `META-INF/jars/*.jar`.

## Change

- `scanNested` keeps each nested jar's bytes.
- `readNestedMixinConfigs` parses every `*.mixins.json` inside the nested jar with a
  `META-INF/jars/<jar>!/` prefix, including refmaps and injection/at-target extraction.
- `mixinConfigs` now lists nested configs, so the aggregate `configs` count is no longer 0 for
  a nested-only mod.
- Added `scansMixinConfigInsideNestedJar` synthetic test.

## Real data

P26 ironchests jar (contains `resourcefullib` nested):

| | before | after |
|---|---:|---:|
| mixin configs | 0 | **1** |
| mixin classes | 0 | **1** |
| injections | 0 | **1** |
| unresolved injections | 0 | 0 |

The one nested ResourcefulLib mixin resolves cleanly. lithium converted remains
`202 / 214 / 86 / 3` (configs/classes/injections/at-targets), so the refactor did not duplicate
or drop top-level entries.

## Tests

`gradle --no-daemon test --rerun-tasks`: **21/21 pass** (new nested test).

## Evidence

- `gradle-test.log`
- `install-dist.log`
- `analyze.log`, `analyze-lithium.log`
- `ironchests.json`, `lithium-converted.json`
