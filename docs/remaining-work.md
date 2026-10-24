# Remaining work / client boundary

This file records what is intentionally not verified in the current environment. It is not a
claim that these paths work.

## Update 2026-10-23 (current state)

- ImmediatelyFast 1.21.1 batching port is **verified** (HUD/items/overlay, per-lighting, Iris
  1.8.1/1.8.14 + shader pack r5.3, dedicated-server multiplayer, 95s soak, A/B checks,
  SimpleImmediate fallback): see `runs/p134`-`p150`.
- The port jar still reports **2 inert classes**, but they are **1.20.4-only leftovers**, not pending
  features. The official 1.21.1 jar has no `core/MixinBufferBuilder` or
  `fast_text_lookup/MixinFontManager` class at all (native audit `listed=37 inert=0`); their
  1.21.1 targets are gone (`field_1555`, `field_24256`/`method_27541`/`method_27542`). They stay
  inert rather than being registered as fake passes; see `runs/p180-inert-closure/` and
  `runs/p169-inert-analysis/`.
- The previously re-registered ChatHud/MinecraftClient/BufferRenderer, map atlas and VertexBuffer
  mixins are active; the port's HUD batching uses the verified 1.20.4 architecture, not the
  native 1.21.1 layered-drawer set.
- Dynamic vertex-buffer fast upload is **enabled** (`runs/p178-vertex-upload/`): the 1.21.1 mixin
  redirects `method_43442`, `method_43443` and the new `method_60829`, keeps static (35044)
  buffers on `glBufferData`, and reuses larger dynamic buffers with `glBufferSubData`. An
  80-armor-stand scene (camera locked, 60/79 fast markers, up to 76k sub-data uploads) shows no
  GL/mixin errors and an off/on screenshot difference of 0.0087%, below the off/off control
  (0.214%). No performance gain is claimed; only one GPU and one synthetic scene were tested.
- Map atlas generation is **restored** (`runs/p175-map-atlas/`): `MixinMapRenderer` reads
  `class_9209.comp_2315()`, `MixinMapRenderer_MapTexture` uses the 1.21.1 `method_60803` slice and
  a 1x1 never-registered dummy instead of the lenni allocate, and `MapAtlasTexture` is embedded.
  A real singleplayer run holding `filled_map` (map id 1, `components:{"minecraft:map_id":1}`)
  rendered the map, logged `map-atlas bind … immediatelyfast:map_atlas/0`, and produced no
  ClassCastException/crash. `runs/p177-map-atlas-edge/` extends this to two maps (tile 0/1,
  packed 0 and 256) and an item frame with map 2, rendered in the same screenshot.
  `runs/p181-map-atlas-lifecycle/` adds a `locked=0` held map that gets a second atlas upload
  (terrain replaces the pattern) and a normal client stop (`keep-dummy -> close -> clear
  atlases=1`, exit 0), and fixes a real crash where a queued map frame wrote into the closed
  NativeImage after the atlas was released. Atlas overflow (1024 maps) is still untested.- Dedicated servers: Forge and NeoForge **vanilla and with Farmer's Delight** verified
  (`runs/p159`, `p161`, `p163`, `p164`); real mrpack with files+overrides verified (`p160`).
- Performance: no reproducible gain; 80-armor-stand interleaved runs are ~13% slower with
  universal batching (`runs/p148`, `p157`). Do not claim a speedup.
- Sodium conversion probe: `blocked_static` 13/15/16 (`runs/p158`); needs its rendering core
  ported, out of scope.
- Shulker grid item icons and real server-item sync are now restored (`runs/p187-grid-draw-probe/`,
  2026-10-24): two real bugs fixed. (1) Every component "read" in the bridges/companion used
  `ItemStack.method_57379(type, null)`, which is `set(type, value)` and **cleared** the CONTAINER
  component on first read - that is what made the server-synced box look like `!minecraft:container`
  since p110; all reads now go through `getComponents().get(type)`. (2) The conversion stripped the
  mod's ItemStackMixin entries, so nothing ever supplied `PreviewTooltipData`; the companion now
  injects `getTooltipData` and registers a component-first provider over the mod's one for all 17
  shulker items. With `preview.alwaysOn=true` (the stock mod wants the preview key held), the grid
  draws the diamond icon with its count and the server-synced box renders the same way
  (`GRID_DRAWITEMS ... first=minecraft:diamondx5`, `GRID_SERVERBOX slot=3 nonAir=1`).
  Still open: FULL preview type (3x9), multi-item grids, the real mouse-hover path (the harness
  drives the same pipeline through HudRenderCallback because OS cursor injection is unreliable),
  the preview-keybind interaction, and TrashSlot creative/multi-client variants.

## Already verified (dedicated server)

| area | evidence |
|---|---|
| ironchests container place/insert/NBT/restart | `runs/p14-lithium-ironchests/`, `runs/p26-codec-safe/` |
| lithium boot + 225-chunk save/restart | `runs/p23-chunk-stress/`, `runs/p24-chunk-stress-tool/` |
| trashslot boot + Balm init/network + three packet codecs | `runs/p17-balm-net/`, `runs/p33-all-packets/` |
| all three samples + Balm coexist | `runs/p41-all-three/` |
| all-three chunk stress + CodecDispatch probe | `runs/p42-all-three-chunk/`, `runs/p43-all-three-codec/` |
| safe CodecDispatch semantics | `runs/p26-codec-safe/`, `runs/p37-codec-probe/` |
| static mixin target/refmap/at-target analysis | `runs/p21-refmap/`, `runs/p35-at-refmap/`, `runs/p36-patched-at/` |
| profiles | `profiles/` |

## Blocked: client GUI / network / multiplayer

A PCL-based Fabric 1.21.1 client joins a singleplayer world, renders terrain/HUD, shows the
inventory + TrashSlot button, and can receive a real 5-diamond stack. A direct `TrashHelper`
probe reads the stack back in-session; rejoin-empty is **TrashSlot's own login reset**
(`setTrashItem(ItemStack.EMPTY)` in `PlayerLoginEvent`), not a bridge persistence failure. A probe
shows the trash slot is **not in `ScreenHandler.field_7761`** (`indexOf = -1`, 46 slots); it is a
client-side `TrashSlotComponent`, so ordinary `clickSlot` cannot target it. After adding the
serverbound Balm bridge, clicking a stack then the trash widget **moves it into the trash slot**
(`runs/p59-trash-send/after-send.png`), and the server probe reads 5 diamonds. The same real GUI
click path also **returns** the stack to the cursor and clears both client/server trash
(`runs/p63-trash-debug/`: `carried=5`, server `serverTrash=0`; cursor-away screenshot confirms it).
P61's "return failed" was a screenshot misread: the returned stack was on the cursor over the
trash icon. Clientbound `MessageTrashSlotContent` also arrives (`S2C_CLIENT trash=3`,
`runs/p64-trash-s2c/`), and the provider-level empty action clears both sides via the new reply
bridge (`runs/p65-trash-empty/`). `runs/p183-trash-key/` now passes the **real GUI empty key**:
inventory hovered over the trash slot, extended Delete (`key=261`, not KP_DECIMAL 330) reaches
`ScreenKeyEvent.Press.Post`, `DEBUG_EMPTY_PROVIDER` fires, and the server reports
`SERVER_TRASH empty=true count=0`. Still **not verified** for TrashSlot:

- legacy Fabric networking bridge (`runs/p89-legacy-networking/`, `runs/p90-fallingtree-join/`):
  AppleSkin init/SyncHandler, the HUD food path and the status-effect tooltip path
  (`runs/p95-appleskin-tooltip/`) now pass, and a real hover appends AppleSkin's
  `FoodOverlayTextComponent` through the new ItemTooltipCallback bridge
  (`runs/p101-appleskin-hover/`); the numbers are unreadable here because `icons.png` is
  missing. FallingTree: join and a real single-log break now pass after bridging two more
  tombstones (enchantment map, mining speed), but tree felling does **not** trigger: only the
  broken log disappears and there is no crash/tombstone (`runs/p102-fallingtree-fell/`).
  Felling now works end to end (`logsBefore=20 logsAfter=16`) after bridging the enchantment
  map, mining speed and `ItemStack.damage`; the earlier failures were the test harness (no axe
  in the main hand makes `isValidTool` abort with INVALID_PLAYER_STATE) plus that damage API
  change. Only oak and a small artificial tree were tested; other wood types, big trees and
  the in-game toggle command are untested. See runs/p102-fallingtree-fell/. Original bullet: the deleted
  `PlayChannelHandler` shim, old `ServerPlayNetworking.send` / `CustomPayloadC2SPacket` redirects and
  the one-arg `Identifier` factory are implemented; AppleSkin now gets past init and packet
  construction but still hits a `FoodHelper` tombstone at HUD render, and FallingTree's join path is
  not re-tested;
- chunk-stress marker matching: `tools/run_chunk_stress.py --self-test` now proves a `# >`
  command echo is not counted while a real `[Server] STRESS_OK_A` line is;
- hash manifest: `tools/check_hashes.py` verifies every `runs/SHA256SUMS.txt` entry, and
  `tools/hash_evidence.py` now refuses to write a manifest with missing files
  (`MISSING` placeholder lines removed);
- Bridge consistency is now a tool + a patcher behaviour (`runs/p98-bridge-consistency/`):
  `tools/check_bridge_consistency.py` hashes every embedded bridge and fails on stale copies;
  `JarPatcher.embedUsedBridges` overwrites present bridge classes with the canonical bytes but keeps
  unreferenced ones (a multi-stage pipeline such as IronChests still needs `CodecDispatch`).
- Combined smoke passes with AppleSkin + Mod Menu + ShulkerBoxTooltip + TrashSlot + IronChests +
  Lithium + Balm (`runs/p96-combined-smoke/`): world loads with no tombstones/crash. Shulker's
  ender-chest sync is re-serialised as Slot/id/Count; item components beyond id/count are not carried.
  Rebuild every patched jar against the same bridge dir after a bridge change, because each jar embeds
  its own bridge copy and the first loaded one wins;
- Clumps orb merging passes through the companion in `java/src/compat-clumps/` (built by
  `tools/build_clumps_companion.py`): 3 + 7 orbs merge to 10 on a dedicated server
  (`runs/p93-clumps-merge/`). Vanilla canMerge cannot be reused (same value + 40-tick phase only) and
  vanilla merge() keeps min(value); the companion writes the summed value and discards the other orb.
  Residual: tick-driven instead of inside ExperienceOrbEntity.tick, fixed 2-block radius, ignores
  Clumps' config;
- Mod Menu mod list opens, stays stable and now draws its rows (`runs/p94-modmenu-list/`): the
  `render-widget-override` rule no longer renames `Screen.render`, and `bodyRedirects` replaces the
  two shader-based list renderers with a DrawContext row renderer. The row backdrop is simplified and
  the magenta checkerboard is this machine's missing assets; scrolling/search/config interaction is
  scrolling state and search filtering are verified with screenshots (0→40 rows move; "menu" 8→2);
  real mouse-wheel/keyboard events are still unverified (three OS injection methods left the
  scroll amount at 0.0, so this is an input-injection limitation, not a conversion regression;
  see runs/p104-wheel-input/); Mod Menu's own config screen opens and
  draws ten option rows (`runs/p97-modmenu-config/`), but other mods' Cloth-Config screens and
  individual toggles are untested;
- Mod Menu title screen passes (`runs/p92-modmenu/`): the private field is read reflectively and the
  button widget overrides `renderWidget` after a `methodRenames` rule; the mod list screen itself
  and config UI are untested;
- ShulkerBoxTooltip provider contract passes (`runs/p91-shulker-provider/`): the old
  BlockEntityTag/fromNbt tombstones, the DyeColor float[] accessor and the client/server channel
  shims are bridged, and a real GUI hover now shows the item-summary tooltip (`Diamond x5`,
  `runs/p100-shulker-hover/`). The full grid preview is unavailable because the conversion
  stripped the `ItemStackMixin` / `ShulkerBoxBlockMixin` entries (dead 1.21.1 targets). A
  companion mixin supplies `PreviewTooltipData` from the current `getTooltipData()` and an
  NBT-compat bridge restores `contains(key, 9/99)` semantics. `runs/p186-shulker-grid-client-item/`
  now proves the component is **not** empty (client-side item: `SBT_ITER raw1=1`), a
  `ComponentPreviewProvider` wrapper supplies the 27-slot inventory, and t2/t4 (`getNbt`/`setNbt`)
  bridges let the grid renderer reach the tooltip: the preview frame and `Diamond ×5` appear in
  `grid.png`. Still missing: the item icons inside the grid slots, and a real server item (the
  `/item replace` stack still shows `!minecraft:container` on the client).
- TrashSlot remaining UI variants: creative-mode deletion keys and multi-client sync. Plain
  Delete empty (`runs/p183`), Shift+Delete cross-slot delete_all (`runs/p184`: 5+3, all=true,
  8→0), and empty-cursor right-click undelete (`runs/p185`: 1 to cursor, 4 left in trash) pass;
  the p85/p86 "key never fires" was the injection missing `KEYEVENTF_EXTENDEDKEY` (KP_DECIMAL
  330 instead of DELETE 261), not Balm;
- lithium gameplay/rendering: a smoke test passes (81/81 forced chunks, place + real block break,
  server and client alive; `runs/p73-lithium-play/`), a 60-second TPS sample reports 20.03 with
  289/289 chunks (`runs/p84-lithium-tps/`), a four-minute dedicated soak reports 20.00 TPS with
  flat heap growth (`runs/p99-lithium-soak/`), and a three-minute soak with 40 zombies ticking
  and pathfinding also holds 20.00 TPS (`runs/p103-mob-soak/`). An observer redstone clock also
  holds 20.00 TPS for three minutes (`runs/p105-redstone-soak/`, clock activity inferred from the
  construction). A combined five-minute soak (168 forced chunks + 40 zombies + the redstone
  clock + IronChests) also holds 20.00 TPS after the chunk-generation window
  (`runs/p108-combined-soak/`). Large redstone machines and multi-hour sessions are still
  unverified;
- **six new mods do not generalize the three-mod result** (`runs/p88-mod-expansion/`,
  `docs/mod-expansion.md`): AppleSkin, Mod Menu, Clumps, FallingTree and ShulkerBoxTooltip have
  concrete blockers (Fabric networking bridge, private title-screen field, removed orb-merge mixin,
  old `ServerPlayNetworking.send`, NBT tombstone), and FerriteCore is boot-only with two mixins
  removed. These need new rules/bridges; the analyzer's multi-loader misdetection is fixed;
- ironchests GUI/render: **chest GUI opens, renders and supports put/take round trips**
  (`runs/p68-ironchests-gui/`, `runs/p69-ironchests-interaction/`; server-side menu state agrees at
  ticks 220/260/300). Ported the nested ResourcefulLib 2.0.6 server networking (work-only), fixed the
  channel location to `ironchests:main/sync`, and added the `screen.render-background-one-arg` +
  `ironchests.draw-nine-sliced` rules. The background now renders the real nine-slice panel
  (`runs/p72-ironchests-nine-slice/`). Persistence across close/reopen and the clientbound
  chest-content sync also pass (`runs/p70-ironchests-persist/`; the P67 NBT bridge direction was
  corrected there). The ResourcefulLib server-helper port now lives in the repo
  (`java/src/nested/java/`) and the whole pipeline is one command
  (`tools/rebuild_ironchests_client.py`, `runs/p71-rebuild-pipeline/`).

**Two-client sync passes both ways** (`runs/p75-two-client-server/`, `runs/p76-two-client-move/`):
after splitting the ResourcefulLib port into server-safe `RawChannel` + client-only
`FabricClientPacketHelper`, a dedicated server with `online-mode=false` sends chest contents to a
second client, and the guest's take-out click is written back to the server and observed by the host
(`LAN_GUEST_MOVED slot0=air` → `DED_AFTER slot0=air` → `LAN_MENU player=HostA slot0=air`). The
earlier LAN attempt (`runs/p74-two-client/`) is superseded.

**Close-screen now passes** (`runs/p77-two-client-close/`): `setScreen(null)` only closed the client,
but calling `Screen.close()` (`method_25419`) makes both the client and the server drop the chest
menu (`LAN_CLOSED slots=46`, `DED_MENUS hostSlots=46 guestSlots=46`). The physical ESC key path is
untested.

**Same-chest contention is conserved** (`runs/p78-two-client-race/`): after the guest took 7
diamonds, the host acted on the same chest and the server total stayed 7
(`DED_TOTAL chest=0 hostSlot54=0 guestSlot54=7`).

**Same-tick concurrent clicks** (`runs/p79-two-client-simultaneous/`,
`runs/p80-two-client-clean/`): both clients clicked on the same world tick (2700). Both predicted
success, but the server granted the stack to one player only. In the clean re-run (both inventories
and the chest cleared first) the winner kept `slot54=7`, the loser was corrected to
`slot54=air`, and the server total stayed 7 — no duplication.

**Physical ESC key now passes** (`runs/p83-esc-teleport/`): after clearing the target block and
placing a fresh chest, then teleporting the player next to it, the chest screen stays open
(`slots=90`); a physical ESC injection closes it and both the client and server handlers fall back to
46 slots. The earlier blocked attempts (`runs/p81-esc-key/`, `runs/p82-esc-onuse/`) were caused by the
player being out of menu range / a stale block entity.

**Source check (TwelveIterations/TrashSlot v21.1.11):** `TrashSlotGuiHandler.onMouseClick` does
not use `Slot` placement. It checks `callIsHovering(trashSlot, mouseX, mouseY)` and then calls
`DeletionProvider.deleteMouseItem(player, mouseItem, trashSlot, rightClick)`; `TrashSlotComponent`
draws the slot and updates the `TrashSlotSlot` x/y in `drawBackground`. P58's stored `152,165` was
read before/without that draw update, so the next probe must log `screen.leftPos/topPos`, the
draw-updated slot position, and `component.getRectangle()` before clicking.

To close these, provide a Fabric 1.21.1 client instance with:

- the same Fabric loader/API versions as the server profiles;
- the patched mods and native Balm 21;
- a display/GPU (or a supported software GL stack);
- a way to capture a screenshot and drive the client (key/mouse or a test client harness).

Acceptance would be: open the trash GUI, move a stack to/from the trash slot, restart, reopen;
and a two-client sync check. Do not mark the profiles as client-compatible without that.

### Input-method caveat (observed in PCL)

On this machine, with a Chinese IME active, letter keys such as W/E are captured by the IME
candidate window: W shows the IME box and does not move the player; switching to English makes
movement work. This is a client input/focus issue, not a mod compatibility result.

Therefore:

- keyboard tests (WASD, E inventory, hotbar keys) must be run with the IME in **English** mode, and
  the mode must be recorded in the evidence;
- chat/sign/book text tests intentionally use the Chinese IME;
- mouse/probe-driven tests (P55/P56) are not affected by the IME; P56's trash-drop gap still needs
  its own GUI slot/hit-test investigation.

## Optional, not blocking the above

- **Chunk optimization**: the P13 port delegates to vanilla `method_14134`; the old lithium
  multi-entry cache/off-thread fast path is not reimplemented. It is a performance loss, not a
  correctness gap.
- **Nested mixins**: now expanded (P48); `@At` ordinal is extracted but not validated against the
  target method, and slice/local capture remain unparsed. A structural audit exists now:
  `tools/audit_mixins.py` finds missing and inert (`@Mixin` but unlisted) entries, which caught
  the stripped AppleSkin/Shulker/FerriteCore mixins (`runs/p107-mixin-audit/`).
- **Forge member-level analysis**: out of the current Fabric 1.21.1 target; would need an SRG /
  NeoForge index and a separate loader target.
- **Client-only samples** (`appleskin`, `modmenu`): they cannot be meaningfully booted on a
  dedicated server; no new profile is claimed.
