# P22: cross-sample static injection check (converted vs patched lithium)

Date: 2026-10-18 (Asia/Shanghai). Verification of P21 against the real patch history.

## Runs

Same target index (`client-1.21.1-intermediary.jar` + `intermediary-1.21.1-v2.jar`, Fabric):

| artifact | mixins | injection targets | unresolved |
|---|---:|---:|---:|
| lithium converted | 202 | 214 | **3** |
| lithium patched (chunk-port build) | 202 | 209 | **0** |
| Balm 7.3.44 converted | 32 | 43 | 0 |
| ironchests converted | 0 | 0 | 0 |
| trashslot converted | 0 | 0 | 0 |

The lithium converted 3 are the known constructor changes (`class_4180` POI/storage,
`class_3610` FluidState, `class_1927` Explosion). After the P11/P13 rules (mixin callback
adaptations + mixin class replacement), the same analysis reports **0 unresolved** and 209
remaining injection targets. The five fewer targets are the callbacks replaced/ported by
those rules, not silently dropped checks.

`ironchests` and `trashslot` show 0 because their top-level jars declare no mixins; ironchests'
nested ResourcefulLib mixins are not expanded by this scanner. Balm's 0 is likewise not a
complete mixin check: CenturyBridge had already stripped several Balm mixins from its config.

## What this shows

- P21's unresolved set is not just synthetic: it detects the exact blockers that P11/P13 had to
  fix at runtime.
- The patched lithium build clears those three targets, which matches the observed server
  progression to `Done`.
- The check is static only; it does not prove injection ordinal/slice/local capture or runtime
  behavior.

## Commands / evidence

```powershell
mcbridge1201 analyze --mods work/tmp/p22/<sample> `
  --client-jar work/cb/data/jars/client-1.21.1-intermediary.jar `
  --mappings work/target/intermediary-1.21.1-v2.jar `
  --target 1.21.1 --target-loader fabric --out runs/p22-cross-analyze/<sample>.json
```

Logs: `analyze-ironchests.log`, `analyze-trashslot.log`, `analyze-balm.log`,
`analyze-lithium-patched.log` (converted lithium log is in `runs/p21-refmap/`).
JSONs: `ironchests.json`, `trashslot.json`, `balm.json`, `lithium-patched.json`.
