# P73: Lithium gameplay smoke test

Date: 2026-10-19 (Asia/Shanghai). The lithium port survives real chunk loading and block changes.

## What the probe does

1. force-loads a 9x9 chunk area around the player (`World.getChunk`);
2. places a stone block with `setBlockState`;
3. breaks that same stone through the real server interaction path
   (`ServerPlayerGameMode.destroyBlock`);
4. keeps ticking while the client stays in the world.

## Result

```text
LITHIUM_CHUNKS loaded=81/81 center=4,4
LITHIUM_PLACE placed=true state=Block{minecraft:stone}
LITHIUM_BREAK_BEFORE state=Block{minecraft:stone}
LITHIUM_BREAK_REAL broke=true after=Block{minecraft:air}
LITHIUM_SERVER_ALIVE tick=160 pos=78.5,65.0,65.57
LITHIUM_SERVER_ALIVE tick=240 pos=78.5,65.0,65.38
LITHIUM_CLIENT_ALIVE screen=null pos=78.5,65.0,66.13
```

- 81/81 chunks loaded through the chunk-access path that lithium mixes into;
- the stone block was really broken (state changes to air, `broke=true`);
- the integrated server kept ticking and the client stayed in the world with no crash,
  `NoSuchMethodError` or `NoClassDefFoundError` in the log.

## Scope

This is a **smoke test**, not a full gameplay/rendering verification: it does not measure TPS,
mob AI, redstone or long-session stability. It does show that the chunk-access port and the
block place/break paths work with lithium installed.

## Evidence

- `latest.log`, `LithiumPlayProbe.java`, `lithiumplayprobe.jar`, `compile.log`
