# P107: mixin config integrity audit

Date: 2026-10-20.

## Tool

`tools/audit_mixins.py --jar a.jar --jar b.jar ...`

It parses every `*.mixins.json` / `*.mixin.json` in a jar and reports:

1. `MISSING` - a class listed in a config does not exist in the jar;
2. `INERT` - a class annotated with `@Mixin` sits in the mixin package but is not listed in any
   config (the signature of the conversion stripping dead mixin entries).

Sub-package entries spelled with dots (`client.fabric.ItemStackMixin`) are resolved against the
slashed class path; mixin helper classes and `Config` plugin classes are ignored. Exit code is
non-zero when anything is reported; `--allow-inert` downgrades inert findings.

## Run over the converted mods

```text
jar=appleskin...           configs=2 listed=6 inert=2 problems=2
jar=shulkerboxtooltip...   configs=2 listed=5 inert=3 problems=3
jar=FallingTree...         configs=1 listed=2 inert=0 problems=0
jar=ferritecore...         configs=9 listed=19 inert=2 problems=2
jar=modmenu...             configs=0 listed=0 inert=0 problems=0
```

Inert entries found:

| jar | inert mixins |
|---|---|
| AppleSkin | `ItemStackMixin`, `PlayerManagerMixin` |
| ShulkerBoxTooltip | `client.ItemStackMixin`, `client.ShulkerBoxBlockMixin`, `client.fabric.ItemStackMixin` |
| FerriteCore | `fastmap.FastMapStateHolderMixin`, `mrl.ModelResourceLocationMixin` |
| FallingTree | none |
| Mod Menu | none (it has no separate mixin configs) |

These are exactly the losses documented earlier: AppleSkin's tooltip mixin, Shulker's grid-preview
mixins, and FerriteCore's two memory optimisations. FallingTree is clean.

## Scope

- The audit is structural: it proves a mixin class is not wired in, not why. Re-enabling a stripped
  mixin still requires checking that its 1.21.1 target exists (the stripper removed entries whose
  targets died).
- Mod Menu has no mixin configs in this jar, so it trivially passes.

## Evidence

`report.txt` (raw tool output).
