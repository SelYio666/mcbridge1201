# P68: IronChests chest GUI opens and renders

Date: 2026-10-19 (Asia/Shanghai). The first full IronChests container GUI pass in 1.21.1.

## Result

```text
IRONCHESTS_SERVER block=Block{ironchests:iron_chest} item=1 ironchests:iron_chest
IRONCHESTS_PLACED=true
IRONCHESTS_STATE=Block{ironchests:iron_chest}[facing=north,lock=no_lock,open=false,waterlogged=false]
IRONCHESTS_USE result=CONSUME state=Block{ironchests:iron_chest}[...open=false...]
IRONCHESTS_SCREEN=tech.thatgravyboat.ironchests.client.ChestScreen@2a5b1267
IRONCHESTS_SCREEN_LATE=tech.thatgravyboat.ironchests.client.ChestScreen@2a5b1267
```

`chest-gui.png` shows the real screen: the "Iron Chest" title, a 9x6 chest grid, the 9x4 inventory
grid, and two items in the hotbar. No crash.

## What it took (this round)

1. **ResourcefulLib server networking ported** (work-only, nested jar swap).
   The 1.20.1 `PacketChannelHelperImpl` used the removed raw channel API
   (`ServerPlayNetworking.send(ServerPlayer, Identifier, PacketByteBuf)`,
   `registerGlobalReceiver(Identifier, ...)`). It is replaced with a payload-based implementation
   (`RawPayload` + `PayloadTypeRegistry` + `ServerPlayNetworking.send(player, CustomPayload)`),
   sharing the payload type with the client helper.
   The earlier client helper also had a **wrong channel location** formula
   (`ironchests/ironchests:main/sync`, invalid namespace); both helpers now build
   `ironchests:main/sync` (`namespace:channelPath/packetPath`).
2. **Screen render fix** — rule `screen.render-background-one-arg`:
   `ChestScreen.method_25420(DrawContext)` -> `ScreenRenderBridge` ->
   `Screen.renderBackground(context, 0, 0, 0)` (1.21.1 four-argument form). Hit once.
3. **Texture draw fix** — rule `ironchests.draw-texture`:
   tombstone `t8` (`DrawContext.drawTexture` with 12 ints) -> `DrawContextTextureBridge` ->
   `method_25293(texture, x, y, w, h, u, v, rw, rh, tw, th)`. Hit once.

## Visual caveat

The generated background is flat gray. The legacy call passed 12 ints and only the first 10 have a
1.21.1 counterpart (`u=4, v=4, rw=4, rh=4, tw=256, th=256`); the two trailing ints are ignored.
Slots, title, items and inventory render correctly.

## Evidence

- `chest-gui.png`, `latest.log`
- `patch-screen.log`, `patch-draw.log`
- `ScreenRenderBridge.java`, `DrawContextTextureBridge.java`, `ironchests-screen.json`, `ironchests-draw.json`
- `PacketChannelHelperImpl.java`, `FabricClientPacketHelper.java`, `repack_rl.py` (work-only RL port)

## Still open

- port the ResourcefulLib server helper into the repo workflow (tool/rule), instead of the manual
  nested-jar swap;
- verify GUI interaction (take/put items) and closing the screen;
- ironchests clientbound item sync and two-client synchronization.
