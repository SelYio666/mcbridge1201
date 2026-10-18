# P26: full safe `Codec.dispatch` adapter (no assumeMapUnsafe)

Date: 2026-10-18 (Asia/Shanghai). Replaces the P25 guard on the active ironchests path.

## What changed

`top/mcbridge1201/bridge/CodecDispatch` is now a **javac-compiled** bridge:

```java
public static Codec<?> dispatch(Codec codec, Function type, Function codecFn) {
    return codec.dispatch(type, value -> wrap((Codec) codecFn.apply(value)));
}
```

`wrap(Codec)` implements a real `MapCodec` via `MapCodec.of(MapEncoder, MapDecoder)`:

- decode: materialize the map with `DynamicOps.createMap(input.entries())`, then
  `codec.decode(ops, value).map(Pair::getFirst)`;
- encode: `codec.encodeStart(ops, input)`, get the resulting map and copy its entries into the
  `RecordBuilder`;
- `MapCodecCodec` values are unwrapped instead of wrapped twice;
- empty `keys`/`KeyCompressor` (the dispatch key itself is handled by `Codec.dispatch`).

`JarPatcher` now prefers a supplied `CodecDispatch.class` over the generated ASM fallback
(other generated bridges keep their ASM path). The old generated `CodecDispatch$Guard` remains
only as a fallback when no `--bridge-dir` is supplied.

## Verification

- `gradle test --rerun-tasks`: **17/17 pass**.
- Re-patched converted ironchests with `--bridge-dir work/bridges`: 36 classes, same rule
  counts; `javac bridges: [CodecDispatch]`; jar has
  `CodecDispatch`/`$1`/`$2`, **no** `$Guard`.
- AW + container contract: `passed=true`, all 5 steps true, two `Done` runs, exit 0.

Hashes: `ironchests-safe.jar` `b4730d00b6df95a875bd89ea6c796e764b49ea85cfd9a5372c90366783a17a6e`
(no AW); AW jar under `work/tmp/p26-final/` (not committed).

## Scope

The adapter is a safe map wrapper, not a full proof for arbitrary non-map codecs; the empty
keys/compressor is intentional for dispatch values. Contract remains dedicated server +
command API; no client/GUI/multiplayer.
