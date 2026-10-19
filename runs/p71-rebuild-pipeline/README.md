# P71: reproducible IronChests client rebuild

Date: 2026-10-19 (Asia/Shanghai). Turns the hand-run IronChests fix sequence into one repo script.

## Why

P68–P70 verified the chest GUI, the put/take round trip and close/reopen persistence, but the
ResourcefulLib port lived only in `work/tmp` and the jar was assembled by hand. This step moves the
sources into the repo and automates the whole sequence.

## What was added

- `java/src/nested/java/com/teamresourceful/resourcefullib/common/networking/fabric/`
  - `PacketChannelHelperImpl.java` (1.21.1 payload-based server half)
  - `FabricClientPacketHelper.java` (corrected channel location + shared payload type)
- `tools/rebuild_ironchests_client.py`

The script runs exactly the verified steps:

1. apply `ironchests-nbt.json` + `nbt-packet.json` to the converted+model-shim jar;
2. extract the nested `resourcefullib-fabric-1.20-2.0.6.jar`, compile the two helper sources
   against the client stub / nested jar / Fabric client networking / loader / netty, replace the
   three classes, and put the nested jar back;
3. apply `ironchests-screen.json` + `ironchests-draw.json` to the outer jar;
4. print the SHA-256.

## Determinism check

The rebuilt jar has the **same SHA-256** as the hand-verified jar:

```text
sha256 c0589eebace4b318089492c29f613191f5a7e06d1fea5e140b5366d4fb61cf4b
```

## Smoke test

Launched the rebuilt jar and ran the same probe:

```text
IRONCHESTS_SCREEN=tech.thatgravyboat.ironchests.client.ChestScreen
IRONCHESTS_PUT slot0=50 minecraft:diamond
IRONCHESTS_BE tick=320 slot0=50 minecraft:diamond
IRONCHESTS_REOPEN screen=ChestScreen sync=2 slot0=50 minecraft:diamond
```

GUI opens, put works, the block entity keeps the stack after close/reopen, and the reopened client
menu shows it (S2C sync).

## Usage

```bash
JAVA_HOME=/path/to/jdk python tools/rebuild_ironchests_client.py \
  --fabric-api "D:/.../fabric-api-0.102.0+1.21.1.jar" \
  --out work/client/ironchests-rebuilt.jar
```

`--input` defaults to `work/client/ironchests-modelbridge2.jar` (the converted jar with the
work-only model shim); `--bridges`, `--stub`, `--loader` and `--netty` have defaults matching this
workspace.

## Evidence

- `latest.log`, `rebuild.log`
