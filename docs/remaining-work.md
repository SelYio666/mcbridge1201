# Remaining work / client boundary

This file records what is intentionally not verified in the current environment. It is not a
claim that these paths work.

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
bridge (`runs/p65-trash-empty/`). Still **not verified**:

- legacy Fabric networking bridge (`runs/p89-legacy-networking/`, `runs/p90-fallingtree-join/`):
  AppleSkin init/SyncHandler, the HUD food path and the status-effect tooltip path
  (`runs/p95-appleskin-tooltip/`) now pass; a real tooltip hover is still untested, and
  FallingTree tree-felling
  behavior is untested. Original bullet: the deleted
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
  real mouse-wheel/keyboard events are still unverified; Mod Menu's own config screen opens and
  draws ten option rows (`runs/p97-modmenu-config/`), but other mods' Cloth-Config screens and
  individual toggles are untested;
- Mod Menu title screen passes (`runs/p92-modmenu/`): the private field is read reflectively and the
  button widget overrides `renderWidget` after a `methodRenames` rule; the mod list screen itself
  and config UI are untested;
- ShulkerBoxTooltip provider contract passes (`runs/p91-shulker-provider/`): the old
  BlockEntityTag/fromNbt tombstones, the DyeColor float[] accessor and the client/server channel
  shims are bridged; a real GUI hover and `shouldDisplay` were not checked;
- the real UI key/action that invokes empty-trash: the geometry is now known (rect
  `(227,207)-(258,231)`, scale 3, physical `(1176,873)`), but `Delete`, `Ctrl/Shift/Alt+Delete` all
  leave the trash at 5 (`runs/p86-empty-hover/`). A registered
  `ScreenKeyEvent.Press.Post` listener never fired while the ESC injection in P83 did close the
  chest, so the synthetic key reaches GLFW but not Balm's screen-key event dispatch. The action
  itself passes at provider level (`runs/p65-trash-empty/`);
- lithium gameplay/rendering: a smoke test passes (81/81 forced chunks, place + real block break,
  server and client alive; `runs/p73-lithium-play/`) and a 60-second TPS sample reports 20.03 with
  289/289 chunks (`runs/p84-lithium-tps/`), but mob AI, redstone and long sessions are still
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
  target method, and slice/local capture remain unparsed.
- **Forge member-level analysis**: out of the current Fabric 1.21.1 target; would need an SRG /
  NeoForge index and a separate loader target.
- **Client-only samples** (`appleskin`, `modmenu`): they cannot be meaningfully booted on a
  dedicated server; no new profile is claimed.
