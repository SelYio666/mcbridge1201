# P31: regression test for supplied CodecDispatch selection

Date: 2026-10-18 (Asia/Shanghai). Pins the P26 behaviour where a supplied javac
`CodecDispatch` must win over the generated ASM fallback.

## Test

`JarPatcherCodecDispatchTest.suppliedCodecDispatchIsEmbeddedInsteadOfGenerated`:

- synthetic caller invokes `top/mcbridge1201/bridge/CodecDispatch.dispatch(Codec, Function, Function)`;
- rule redirects that exact call to the same owner/method;
- `bridgeClasses` supplies a dummy `CodecDispatch.class`;
- after patch:
  - rule applied once;
  - `externalBridges` contains `CodecDispatch`;
  - output `CodecDispatch.class` is the supplied class (same class name);
  - no generated `CodecDispatch$Adapter.class` is embedded.

This is the unit-level guard for the P26 `JarPatcher` preference (`--bridge-dir` wins only for
`CodecDispatch`; other generated bridges keep their ASM path).

## Result

`gradle --no-daemon test --rerun-tasks`: **18/18 pass**, exit 0.

Evidence: `gradle-test.log`.
