# P36: at-target analysis before/after the lithium patch

Date: 2026-10-18 (Asia/Shanghai). Cross-check for P35.

## Table

Same 1.21.1 index, Fabric:

| artifact | injections | at-targets | unresolved |
|---|---:|---:|---:|
| lithium converted | 214 | 86 | **3** |
| lithium patched (chunk-port build) | 209 | 84 | **0** |

The converted 3 are the known POI/FluidState/Explosion constructor changes. The patched build
clears them (`mixinInjectionsUnresolved=0`) while still resolving 84 at-targets. The five fewer
injections and two fewer at-targets correspond to the callbacks/classes replaced by the P11/P13
rules, not to skipped checks.

## Meaning

P35's refmap at-target resolution is consistent with the runtime patch history: the same
analysis that flags the converted jar clears the patched jar, matching the server reaching
`Done`. Static only; no runtime injection verification.

## Evidence

- `analyze.log`
- `lithium-patched.json`
