# Remaining work / client boundary

This file records what is intentionally not verified in the current environment. It is not a
claim that these paths work.

## Update 2026-10-28 (documentation encoding)

- The three documents corrupted during p195 (UTF-8 read as cp936 and re-saved) are readable again:
  `README.md`, `docs/FINAL-STATUS.md`, `runs/p125-final-acceptance/README.md`. Repair is **not** a
  full restoration: of 13385 damaged characters only 2599 (19.4%) round-trip back through
  GBK→UTF-8; the other 10786 (80.6%) had bytes already replaced by `?` and were rewritten from
  the surrounding intact sentences, path/number skeletons and the `runs/` evidence they cite
  (386 lines untouched, 12 lines restored, 306 rewritten). See `runs/p198-text-encoding/`.
- `tools/check_text_encoding.py` is a direct `verify_evidence` check (`text_encoding`), not only a
  case inside the review suite, so it cannot be skipped together with the built CLI. It covers
  bad UTF-8, `U+FFFD`, GBK user-area characters, the UTF-8-as-cp936 signature set, `?` byte-loss
  patterns and the general double-encoded run.
- Still open: **the writer that damaged the files was never traced** (only "must not re-enter" is
  guarded); the guard scans `*.md` only; rewritten prose is semantically equivalent, not the
  author's verbatim wording.

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
  NativeImage after the atlas was released. Atlas overflow was verified in `runs/p188-atlas-overflow/` (2026-10-25): 1026 map ids were
  assigned through the public update path, atlas 1 was created exactly once at id 1025
  (packed 65536), the tile encoding is correct, a real `MapRenderer.draw` uploaded the map
  into atlas 1 (pixel-level check, 0 mismatches), and the normal exit cleared atlases=2.
  A third atlas (2048+ maps) and cross-atlas on-screen binds/pixels are covered by `runs/p194-atlas-third/` (2050 ids, atlas 2 packed 131072/131328, map 1/1025/2049 in one HUD frame, pixel 0/0, clear atlases=3). `runs/p200-atlas-layout/` closes the two things p194 could not show: every one of the 2050 ids is verified at the slot the allocator reported (a 12-bit per-map code read back from the atlas image, 0 mismatches - not a sample, and not the shared-content check p194 had), and the three 4096^2 atlases are on screen side by side at logged coordinates (3 x 256 px, spacing 272, one window offset). Still open: a real dedicated server pushing 1024+ real maps, filling all 3072 slots, and any VRAM measurement (p200 measures the process working set and says so).- Dedicated servers: Forge and NeoForge **vanilla and with Farmer's Delight** verified
  (`runs/p159`, `p161`, `p163`, `p164`); real mrpack with files+overrides verified (`p160`).
- Performance: no reproducible gain; 80-armor-stand interleaved runs are ~13% slower with
  universal batching (`runs/p148`, `p157`). Do not claim a speedup.
- Sodium conversion probe: `blocked_static` 13/15/16 (`runs/p158`); needs its rendering core
  ported, out of scope. Dated assessment: `docs/sodium-plan.md` (p199, 2026-10-28) resolves every
  entry against the 1.20.1 / 1.21.1 mappings → of 44 entries, 6 come only from the 1.20.1-era
  Fabric API modules bundled in Sodium's `META-INF/jars` (not Sodium's code, unverified), 7 are
  pure intermediary id changes, 7 are signature changes with a clear 1.21.1 spelling, and 24 sit
  on the immediate-mode vertex pipeline (`BufferBuilder`/`Tesselator`/`DefaultVertexFormat`),
  which 1.21.1 replaced with `ByteBufferBuilder` + `MeshData`. Conclusion unchanged: not feasible
  without rewriting that path; no rule was written and no game was launched.
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
  p193 (2026-10-26) closed the residuals: multi-item (3 diamond + 2 emerald), FULL (3x9), the
  real tooltip path (pre-FULL `DRAWTOOLTIP data=PreviewTooltipData`; p191's Mouse-raw +
  GLFW-callback input) and the server box (2 diamond + 4 emerald, `/item replace container.10`):
  `runs/p193-shulker-grid-residual/` (result.json 4/4 true; after-full/after-server/after-compact.png).
  OS-cursor-level hover, 27-slot full grid and preview key rebinding were closed later: keys by
  p197, hover + heterogeneous NBT by p202. TrashSlot creative/multi-client was closed by
  p189/p191/p192 (see their runs).

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
- Mod Menu mod list opens and stays stable (`runs/p94-modmenu-list/`): the `render-widget-override`
  rule no longer renames `Screen.render`, and `bodyRedirects` replaces the two shader-based list
  renderers with a DrawContext row renderer. **Fixed in p205:** the rows do paint now
  (`runs/p205-modmenu-rows/`). p204's correction stands for the record - the list was black in p94's
  own committed screenshots and in all four p204 shots, and only the scrollbar drew. The cause was
  the bridge's entry call: `Entry.render` takes `(ctx, index, y, x, width, height, ...)` and the old
  body passed `(left, top, ...)`, so icons and names were laid out elsewhere while the row backdrop
  (which uses left/top directly) still painted. The bridge now mirrors vanilla `renderList` +
  `method_44397`: y before x, row width from `getRowWidth()` (294 for ModListWidget, not
  widgetWidth - 8), height `itemHeight - 4`, visibility against `getY()`/`getBottom()`, hover from
  `getEntryAtPosition`, and `Entry.drawBorder` before `Entry.render`. Matched runs (same client,
  mods, window and cursor; only the bridge differs) go from 0 bright / 0 coloured list pixels to
  11147 / 20211 with six icon bands, and the rows move exactly 36 device px for a 36 px scroll
  delta. Still degraded: the original textured backdrop is not restored (flat 0x80000000 band), the
  selection highlight (`method_44398`) is not drawn, and the description panel's rows are untested
  (it uses the same bridge but had `count=0` in this run).
  Real wheel and keyboard input now work (`runs/p204-wheel-input/`, closing p104): nine OS wheel
  notches over the list stepped the scroll 18/36/54/72/90/108/126/144 and clamped at max 147,
  each notch showing up as one `dy=-1.0` at `Mouse.onMouseScroll`; a wheel outside the window
  produced no event, a wheel over the right pane produced events but did not move the list; a real
  left click focused the search box and four `KEYEVENTF_UNICODE` characters typed "menu", filtering
  11 entries down to 1. p104's "this machine cannot receive wheel input" was the same window-not-on-
  top problem p202 found. Still untested: arrow keys / PageDown (unicode injection only sends
  characters). Mod Menu's own config screen opens and draws ten option
  rows (`runs/p97-modmenu-config/`), but **Cloth-Config screens cannot open at all**: the only Cloth
  Config here is the 1.20.1 JiJ (`cloth-config-fabric-11.1.136` bundled inside AppleSkin /
  ShulkerBoxTooltip) and `ConfigBuilderImpl.<init>` dies on the removed `class_437.field_44669`,
  which Mod Menu's per-mod config probe hits for appleskin / fallingtree / shulkerboxtooltip /
  trashslot (stack trace in `runs/p204-wheel-input/client.log`). Individual toggles are untested;
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
- TrashSlot creative deletion keys and multi-client isolation are now verified (`runs/p189`,
  `runs/p190`, 2026-10-25). p189 also fixed a real defect: the 1.21.1 creative screen keeps
  hoveredSlot null and has no SlotWrapper, so the converted creative branch could never run; the
  `trashcreativefix` companion re-implements it (hotbar 45..53 -> InventoryMenu 36..44,
  generalized in p191 to the class_484 wrapper whose list position IS the InventoryMenu index).
  Plain Delete empty (`runs/p183`), Shift+Delete cross-slot delete_all (`runs/p184`), right-click
  undelete (`runs/p185`), the creative variants (`runs/p189`: hotbar + delete_all chain;
  `runs/p191`: inventory tab main slots SERVER_DELETE slot=18, creative list slots are
  upstream-ignored, creative right-click undelete is not applicable - no trash canvas on the
  creative screen and the upstream undeleteLast is a stub) and the multi-client cases
  (`runs/p190`: A drains, B untouched; `runs/p192`: three clients, B actively drains its own
  trash, C constant, A's rejoin resets its trash to empty by upstream PlayerLoginEvent design)
  all pass. Concurrent same-tick operations from two clients now pass too: `runs/p203` fires both
  clients on one shared epoch-ms instant and both writes land in the same server tick (819,
  `P203_SET side=SERVER thread=Server thread`, 4 ms apart, A empty / B `diamondx3`), with the
  serverbound messages (`MessageDeleteFromSlot`, `MessageTrashSlotClick`) stamped in that same
  tick. Still untested: four+ clients, and two operations on the *same* player in one tick;
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

- p195 delivery validation (2026-10-26): v0.5.6 portable on a fresh work/tmp/p195-portable root RESULT OK (deps, /api/status, /guide); tools/pcl_panel.py UI smoke with 103 release versions (panel-smoke.png). PCL2 is absent on this machine, the panel asset download was partial (3,361,813/12,361,982), and a clean/offline other machine was not available; full panel install E2E and clean-host portable remain open (runs/p195-delivery-validation/). Clean-host portable closed by p208: the shipped zip runs in a scrubbed environment (no system Python or JDK visible, fresh HOME/APPDATA) at 8/8, twice - as shipped and with the current launcher sources overlaid (runs/p208-cross-platform/). Full panel install E2E is still open.

- p196 (2026-10-26): 27 distinct items in the shulker box render 27 grid icons (GRID_SETRENDER inv=27, GRID_DRAWITEMS items=27), FULL/server box/real tooltip path all pass (runs/p196-shulker-grid27/). Its claim that the mod ignores the config previewKey was WRONG: the key was written under the `preview` category and F is vanilla swap-offhand. 27 distinct NBT/enchant stacks untested (closed by p202).
- p197 (2026-10-26): preview keys ARE rebindable through the mod config. `javap` shows `ShulkerBoxTooltipClient.isKeyPressed` reads `config.controls.<key>.get().getCode()` and calls `InputConstants.isKeyDown` (defaults 340/342). With `controls.previewKey=key.keyboard.j(74)`, `controls.fullPreviewKey=key.keyboard.k(75)` and `alwaysOn=false`, the mod's own state machine runs NO_PREVIEW -> COMPACT (J) -> FULL (J+K) -> COMPACT (release K) -> NO_PREVIEW (release J) over a server-provided 27-item box (runs/p197-preview-key/). Boundary: held state is synthesised at the isKeyDown poll boundary, not an OS-level physical key press. 27 distinct NBT/enchant stacks still untested (closed by p202).

- p201 (2026-10-28): the hash manifest is now verifiable by a fresh clone. Cloning the p200 commit gave `check_hashes` ok=646 mismatch=623 missing=20 while this machine printed 1289/1289: `core.autocrlf=true` with no `.gitattributes` made git write CRLF on checkout while the hashes were taken from a mixed worktree (1224 LF / 422 CRLF / 264 mixed), and 20 entries pointed at gitignored `work/` build output. Fixed with `.gitattributes` pinning `* -text`, `git checkout-index -a -f` to normalise the worktree to the blob bytes (line endings only, 394940 insertions = 394940 deletions, no content change), dropping the 20 `work/` entries, and `git ls-files -z` in hash_evidence.py (git quotes non-ASCII names, which made three tracked share/ files look untracked). A clone of the fix gives ok=1269 mismatch=0 missing=0 (runs/p201-eol-determinism/). Boundary: inside a bare clone test_review_fixes.py gives 125/125 with ISSUE-02 skipped (that module needs the built Java CLI and network; the authoring machine reports 130/130). Verified on Windows / Git for Windows only. p208 audits the other side without claiming to run it: the delivery modules all import with `sys.platform=linux` and the Windows-only stdlib blocked (4/4), and the static hits on the delivery path drop from 28 to 22, with 24 to 4 of them unguarded - the 4 leftovers are the portable package being Windows-only by construction (python-embed-amd64 + run.bat). WSL is present on this machine but blocked by security policy, so no Linux kernel was involved (runs/p208-cross-platform/).

- p202 (2026-10-28): hover now comes from the window system and the 27 slots carry 27 different component maps. The probe writes no mouse state at all (its two mouse/screen accessors are getters only), so the only way `P202_HOVER_OK index=10 keysSent=false` can appear is a real cursor position travelling WM_MOUSEMOVE -> GLFW callback -> `Mouse.onCursorPos` -> `Mouse.tick` -> `Screen.render(mouseX, mouseY)` -> `HandledScreen.focusedSlot`. The harness moves the OS cursor from outside the process and logs what it asked for, where Windows put it, and which window is under that point; the probe independently logs `glfwGetCursorPos`, the raw callback fields and `Mouse.getX/getY`, and all four agree on `686,378`. Heterogeneity: the server places a 27-slot box whose entries differ in item id, count, custom name and a mix of lore / enchantments / custom_model_data; the client reads back `stacks=27 distinctComponents=27 distinctItems=27 distinctNames=27`, 27 distinct payloads reach `drawItem`, and `verify_grid.py` measures the screenshot (autocorrelated 36 px pitch = 18*guiScale 2, phase within half a cell of the panel origin the probe logged) to find 27 non-blank, mutually distinct cells. It also corrects an inherited claim: p191/p193/p197 recorded "this machine does not deliver OS cursor moves" - the control run with only `user32.SetCursorPos`, but with the window raised via `SetWindowPos(HWND_TOPMOST)`, hovers too (runs/p202-hover-nbt/repeat/run3-control-warp.log). The problem was never the injection mechanism; it was that the window under the cursor was the terminal. Keyboard input is still forged at the poll boundary, unchanged. Boundary: single machine / single monitor, one screenshot (FULL), no nested shulkers, no per-slot custom models.

- p208 (2026-10-28): delivery is verified in a scrubbed environment, and the non-Windows side is
  audited rather than assumed. `run_clean_host.py` builds an environment with `PATH` reduced to
  `System32`+`Windows`, no `PYTHON*`, no `JAVA_HOME`, and `HOME`/`USERPROFILE`/`TEMP`/`APPDATA`/
  `LOCALAPPDATA` pointing at fresh empty directories; it first proves the scrub worked (`which
  python` and `which java` both `None`), then starts the shipped zip's bundled interpreter and polls
  `/api/status` and `/guide` - 8/8 as shipped and 8/8 with the current `launcher/*.py` overlaid. The
  package carries 0 `.jar` and only `run.bat`. Four real defects were found by `probe_behaviour.py`
  (2/6 before, 6/6 after): `default_root()` returned a relative `.minecraft` from `Path("")` when
  `APPDATA` is unset; `find_java()` only looked for `bin/java.exe`, so `JAVA_HOME` was ignored on
  POSIX; macOS was sent to `xdg-open` with no exception guard; and a `JAVA_FALLBACK` constant pointing
  at `C://Program Files\Java\...` was defined and never used. `tools/build_portable.py` now refuses
  to build when `minecraft_launcher_lib` cannot be vendored (it used to print "missing dependency,
  skipped" and still print `done` with exit 0). Boundary: same machine, different environment - not a
  different computer; `os.name` is not faked because a Windows CPython cannot instantiate `PosixPath`,
  so the dynamic pass proves the import graph only; the portable package is Windows-only by
  construction; `install_jvm_runtime`'s download was not exercised; and a full rebuild was not
  possible here because this machine has no `minecraft_launcher_lib`, so the changed sources were
  overlaid into the 0.5.6 package instead.
