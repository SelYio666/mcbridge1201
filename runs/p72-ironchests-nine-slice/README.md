# P72: IronChests background is the real nine-slice texture

Date: 2026-10-19 (Asia/Shanghai). Closes the "flat gray background" caveat from P68.

## Root cause of the gray background

The P68 bridge treated the 12-int call as a plain `blit`. Upstream source
(`thatgravyboat/Ironchests`, branch `1.20.x`, `GeneratedScreenRenderer`) shows it is a nine-slice:

```java
graphics.drawNineSlicedTexture(BACKGROUND, x, y, type.width(), type.height(),
        4, 4, 4, 4, 256, 256, 0, 0);
```

1.20.1 `DrawContext.drawNineSlicedTexture(Identifier, int x, int y, int width, int height,
int leftSliceWidth, int topSliceHeight, int rightSliceWidth, int bottomSliceHeight,
int centerSliceWidth, int centerSliceHeight, int u, int v)` — 1.21.1 removed it, so the tombstone
call is redirected to `DrawContextTextureBridge.drawNineSliced`, which rebuilds the nine patches
from `method_25293` blits (corners, four edges, stretchable center).

## Result

`chest-nine.png` shows the actual IronChests panel: light beige background with its border and
correctly framed slots, instead of the flat gray from P68.

```text
IRONCHESTS_SCREEN=tech.thatgravyboat.ironchests.client.ChestScreen
IRONCHESTS_PUT slot0=64 minecraft:diamond
IRONCHESTS_REOPEN screen=ChestScreen sync=2 slot0=64 minecraft:diamond
```

## Reproducibility

`tools/rebuild_ironchests_client.py` now recompiles the bridges before patching (a stale
`work/bridges/DrawContextTextureBridge.class` had produced a `NoSuchMethodError` once). The rebuilt
jar is byte-identical to the hand-built one:

```text
sha256 20864ad9046c2550efc5a3a0042f155062fe315f87b3afac64f9ac9b8b0fb8ef
```

## Evidence

- `chest-nine.png`, `latest.log`, `rebuild.log`
- `DrawContextTextureBridge.java`, `ironchests-draw.json`
