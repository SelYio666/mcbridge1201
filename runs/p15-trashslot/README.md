# P15: third sample attempt — trashslot blocked on Balm/Fabric API

Date: 2026-10-18 (Asia/Shanghai). This records a real attempt at a third Fabric sample
(`trashslot 15.1.5`, 1.20.1 -> 1.21.1). The mod's own 4 tombstones were bridged, but the
dependency layer blocks a server boot. Nothing here is claimed as a compatibility pass.

## What was done

1. CenturyBridge conversion of `trashslot-fabric-1.20.1-15.1.5.jar`:
   - verdict `ok_partial`, 4 tombstones at `1.20.4 -> 1.20.5`:
     - `ItemStack.method_7953(NbtCompound)NbtCompound` (write NBT)
     - `ItemStack.method_7915(NbtCompound)ItemStack` (from NBT)
     - `FriendlyByteBuf.method_10793(ItemStack)FriendlyByteBuf` (write item)
     - `FriendlyByteBuf.method_10819()ItemStack` (read item)
   - log: `convert.log`; report: `work/cb/out/trashslot/report.md` (local).
2. Added `TrashSlotNbtBridge` and `rules/fabric-1.21.1/trashslot.json`:
   - uses 1.21.1 `ItemStack.CODEC` + `RegistryOps(NbtOps)` for NBT;
   - packet methods write/read the codec NBT through `FriendlyByteBuf.method_10794/10798`;
   - patch applied 1+1+2+2 calls (4 rules), bridge embedded; jar
     `trashslot-patched.jar` (SHA-256 `89873304...d5d6`).
   - **Status: prepared but not boot-verified**; see blocker.
3. `trashslot` requires `balm-fabric >=7.0.0`.
   - Downloaded Balm 7.3.44 (1.20.1) and converted it: `ok_degraded_partial`, 4 tombstones +
     9 stripped mixins; details in `convert-balm.log` / `work/cb/out/balm/report.md`.
   - Injected the project access widener to fix the private `Identifier(String,String)`
     constructor: `inject-aw-balm.log`.
   - Boot still fails in Balm before TrashSlot's own code:
     `NoClassDefFoundError: net/fabricmc/fabric/api/networking/v1/ServerPlayNetworking$PlayChannelHandler`
     (`server-trashslot2.log`). Fabric API 0.102 removed that handler interface.
   - Tried native Balm 21.0.66 for 1.21.1: boot fails at
     `NoSuchMethodError: Balm.initialize(String, Runnable)` because TrashSlot 15.1.5 was built
     against the older Balm API (`server-trashslot3.log`).

## Result

No `Done`; no trashslot runtime verification. `doneSeen=false`, runner exit 11. The blocker is
the **Balm/Fabric networking API**, not the four trashslot tombstones. The prepared trashslot
rules/bridge are explicitly marked unverified until Balm can boot.

## Commands / logs

```powershell
# conversion (CenturyBridge, run from work/cb)
java -cp "<engine classes>;<asm/gson>" top.dext.centurybridge.Main `
  convert data/segments 1.20.1 1.21.1 out/trashslot in/trashslot-fabric-1.20.1-15.1.5.jar

# bridge + patch
python tools/build_bridges.py --stub work/cb/data/jars/client-1.21.1-intermediary.jar `
  --lib work/lib/gson-2.11.0.jar --lib <datafixerupper> --lib <netty-buffer> --lib <netty-common> `
  --out work/bridges
mcbridge1201 patch --in work/cb/out/trashslot/trashslot-fabric-1.20.1-15.1.5+1.21.1.jar `
  --out work/cb/out/trashslot/trashslot-patched.jar `
  --rules rules/fabric-1.21.1/trashslot.json --bridge-dir work/bridges

# boot attempt (Balm 7.3.44 converted + AW, then native Balm 21.0.66)
python tools/run_server.py --instance work/instances/fabric-1.21.1-server-trashslot `
  --log runs/p15-trashslot/server-trashslot3.log --timeout 240
```

Hashes (SHA-256):

| Artifact | SHA-256 |
|---|---|
| `trashslot-patched.jar` | `89873304eb00f81743c3686215200f759f908255d1075cc24de4278ab37bd5d6` |
| converted `trashslot...+1.21.1.jar` | `8e9ce536ddbf8d1d76f127be891344a81b7dbc0338c1657d0f894d10aefd86ed` |
| converted Balm + AW | `0fd242d3fef669c869697183d83597cefda5e1b28546c7befcc30e1961937269` |
| `server-trashslot3.log` | `38b563a3b7a855dd71eb371b1c2fd1155c3c981045ee91822cdce6d5a5c78fab` |

## Next step

Either bridge Balm's `ServerPlayNetworking.PlayChannelHandler` use (Fabric API shape change) or
use a Balm build that still exposes `Balm.initialize(String, Runnable)` / the old networking
handler. Do not mark the prepared trashslot rules as passed until a real boot + contract exists.
