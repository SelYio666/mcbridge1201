# P18: per-jar bridge embedding for nested jars

Date: 2026-10-18 (Asia/Shanghai). Engine change + regression check.

## Problem

`JarPatcher` collected every used bridge in one global set and embedded all of them at the
**top level** of the patched jar. A class inside a nested jar (`META-INF/jars/*.jar`) has its own
Fabric class loader, so a bridge that is only present at the top level is not reliably visible to
it. This is the documented JiJ call-site gap.

## Change

- `patchEntries` now carries a per-jar `used` set.
- `recordBridge(...)` records a bridge both globally (for reports) and in the current jar's set.
- `embedUsedBridges(...)` runs at the end of every `patchEntries` call, so generated ASM bridges
  and javac bridges are embedded **in the jar that references them**. A nested jar gets its own
  copy; a top-level jar that does not use a bridge does not get it.
- Mixin class replacements still go to the top level (they target top-level mixins).

## Tests

`JarPatcherCallSiteTest` gained `embedsBridgeInsideNestedJarThatUsesIt`:

- outer jar contains `META-INF/jars/nested.jar` with a synthetic caller;
- after patch, the bridge is present **inside** the nested jar;
- the top-level jar does not contain the bridge (no top-level use);
- the nested caller's invocation is rewritten to the bridge.

`gradle --no-daemon test --rerun-tasks`: **13/13 pass** (was 12), exit 0.

## Real-jar regression

Re-patched ironchests with `container.json` and the target index (same rule counts as P10:
36 classes, 123 constant-kind fixes, 3 handle fixes, etc.). Compared with the old patched jar:

- top-level classes and bridge list are identical;
- the only difference is `META-INF/jars/resourcefullib-fabric-1.20-2.0.6.jar`, which now contains
  its own `top/mcbridge1201/bridge/IdentifierFactory.class` (the old jar only had it at the top
  level). This is the intended change, so the overall jar hash necessarily differs:
  `7d89d452...bc9a1` -> `aa589bbb...0430` (before AW injection).

The new patched+AW jar boots and the container contract still passes:

```text
Done (19.4s) -> setblock/insert/NBT -> restart -> Done (17.4s) -> 5 diamonds read back
```

`runs/p18-nested-bridges/contract/verdict.json`: `passed=true`, all 5 steps true,
`blockDataAfterRestart` has `count: 5`.

## Scope

This is an engine/JiJ fix, not a new sample. Ironchests contract remains dedicated server +
command API only; no GUI/render/multiplayer. The trashslot/lithium results are unaffected.

## Files / commands

```powershell
# tests
cd java
gradle --no-daemon test --rerun-tasks

# regression patch (from repo root)
mcbridge1201 patch --in work/cb/out/ironchests/ironchests-5.0.2-fabric+1.21.1.jar `
  --out runs/p18-nested-bridges/ironchests-repatch3.jar `
  --rules rules/fabric-1.21.1/container.json `
  --client-jar work/cb/data/jars/client-1.21.1-intermediary.jar `
  --mappings work/target/intermediary-1.21.1-v2.jar `
  --lib work/instances/fabric-1.21.1-server/libraries/com/mojang/datafixerupper/8.0.16/datafixerupper-8.0.16.jar
python tools/inject_aw.py --jar ... --out ...-aw.jar --aw rules/fabric-1.21.1/mcbridge.accesswidener
python tools/run_contract.py --instance work/instances/fabric-1.21.1-server `
  --out runs/p18-nested-bridges/contract
```

Hashes (SHA-256). The two jars are kept under `work/tmp/p18/` and are intentionally **not**
committed (no game/mod/converted jars in the repository).

| Artifact | SHA-256 |
|---|---|
| `ironchests-repatch3.jar` (no AW) | `aa589bbb4ba9839089ab4cba980c4f37615eac7ea3ba1d223ac2bae882830430` |
| `ironchests-repatch3-aw.jar` | `547fd3fe77e5b181de5065f526cd50040727f78044f155e6887b05d695080755` |
| `contract/verdict.json` | `53579d7cedc31f92ada1172923376a3240d4ca7f4a4cfd1b75d829426930a410` |
| `gradle-test.log` | `0200098a5f2d6f486031ee151a68701c770a67dad07f9c1adef9a8d4b0a513c` |
