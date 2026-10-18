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
(`setTrashItem(ItemStack.EMPTY)` in `PlayerLoginEvent`), not a bridge persistence failure. GUI
drag still did not transfer. Trash transfer is therefore still **not verified**:

- trashslot client GUI, `ClientPlayNetworking` receiver, actual packet delivery;
- lithium gameplay/rendering;
- two-client synchronization;
- ironchests GUI/render.

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
