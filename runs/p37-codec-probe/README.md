# P37: safe CodecDispatch semantic probe

Date: 2026-10-18 (Asia/Shanghai). Direct encode/decode test for P26's javac `CodecDispatch`.

## Probe

A Fabric test mod runs at `SERVER_STARTED` with a record codec:

```java
record Box(int a) {}
Codec<Box> valueCodec = RecordCodecBuilder.create(i -> i.group(
        Codec.INT.fieldOf("a").forGetter(Box::a)).apply(i, Box::new));
Codec<Box> dispatched = CodecDispatch.dispatch(Codec.STRING,
        value -> "k", key -> valueCodec);
```

It encodes `Box(1)` and expects the dispatch shape `{"a":1,"type":"k"}`, then parses that JSON
back and expects `Box(1)`.

## Result

```text
Done (4.847s)! For help, type "help"
[STDOUT]: CODEC_DISPATCH_PROBE_OK
```

`doneSeen=true`, runner/JVM exit 0.

This directly exercises the safe `MapCodec.of(MapEncoder, MapDecoder)` wrapper: encode copies
the value codec's map entries into the dispatch record, decode delegates to the value codec.
It is stronger than the P26 container contract, which only proves the ironchests path.

Earlier probe attempts with `Codec.INT` / `Codec.unboundedMap` failed correctly (a dispatch
value must encode a map, and the value codec must ignore the dispatch key); the record codec is
the valid shape.

## Limits

The probe is a synthetic record, not ironchests `ShapeTypes`; client delivery is still not
covered.

## Evidence

- `compile.log`
- `jar.log`
- `server.log` / `server.result.json`
