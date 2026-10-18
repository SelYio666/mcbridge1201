# P25: guard `Codec.dispatch`'s unsafe MapCodec fallback against null-success

Date: 2026-10-18 (Asia/Shanghai). Runtime hardening for the remaining `Codec.dispatch`
fallback.

## What changed

`CodecDispatch$Adapter` still uses `MapCodec.assumeMapUnsafe(codec)` when the old dispatch
function returns a plain `Codec`, but the returned MapCodec is now wrapped with
`MapCodec.mapResult(new CodecDispatch$Guard())`:

- `Guard.apply(ops, mapLike, result)` checks `result.result().get() == null`; a successful null
  decode becomes `DataResult.error("null result from Codec.dispatch adapter")` instead of letting
  `Optional.of(null)` escape into DFU callers.
- `Guard.coApply(...)` returns the incoming `RecordBuilder` unchanged (encoding is unaffected).
- `BridgeGenerator.generate` emits `CodecDispatch$Guard` with `CodecDispatch`.

## Verification

- `gradle test --rerun-tasks`: **17/17 pass**; new `AnalyzerCoreTest` assertion checks the guard
  is emitted, implements `MapCodec$ResultFunction`, and has both `apply`/`coApply`.
- Re-patched converted ironchests with `container.json` + target index: 36 classes, same rule
  counts as before; the jar contains `CodecDispatch`, `CodecDispatch$Adapter`,
  `CodecDispatch$Guard`.
- Injected AW and ran the full container contract: `passed=true`, all 5 steps true, two `Done`
  processes, exit 0.

Logs: `patch.log`, `inject-aw.log`, `contract.log`, `gradle-test.log`, `install-dist.log`.

## Scope / remaining

This is a **guard**, not a replacement for `assumeMapUnsafe`: a legitimately non-map codec can
still have shape limitations. It turns a possible null-success into an explicit decode error.
The container contract is still dedicated server + command API; no GUI/render/multiplayer.
