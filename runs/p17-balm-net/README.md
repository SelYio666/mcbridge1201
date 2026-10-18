# P17: trashslot reaches Done with native Balm 21 + call-site bridges

Date: 2026-10-18 (Asia/Shanghai). This resolves the P15/P16 Balm blocker enough for a dedicated
server boot. TrashSlot 15.1.5 (1.20.1, converted by CenturyBridge) runs against **native Balm
21.0.66 for 1.21.1**, with three call-site bridges:

1. `Balm.initialize(String, Runnable)` -> `initialize(String, EmptyLoadContext.INSTANCE, Runnable)`
   (`BalmInitializeBridge`)
2. old Balm networking `registerServerboundPacket(Identifier, Class, BiConsumer, Function, BiConsumer)`
   -> 1.21.1 Fabric payload registration (`BalmNetworkingBridge`; 2 serverbound packets)
3. same for `registerClientboundPacket` (1 clientbound payload type; no client receiver on a
   dedicated server)

The four CenturyBridge ItemStack/NBT tombstones are also bridged by `TrashSlotNbtBridge`
(`ItemStack.CODEC` + `RegistryOps(NbtOps)`, `FriendlyByteBuf` NBT write/read).

## Why the earlier attempts failed

- Converted Balm 7.3.44: `NoClassDefFoundError ServerPlayNetworking$PlayChannelHandler`
  (Fabric API 0.102 removed the old handler interface).
- Native Balm 21: `NoSuchMethodError Balm.initialize(String,Runnable)` (P15).
- After the initializer bridge: `NoSuchMethodError BalmNetworking.registerServerboundPacket`
  (P16). The networking bridge wraps the packet class in a `CustomPayload`, builds a
  `StreamCodec<RegistryFriendlyByteBuf, Payload<T>>` from the old encode/decode lambdas, registers
  playC2S/playS2C payload types, and installs a `ServerPlayNetworking` global receiver.
- First networking rewrite left the `invokeinterface` receiver on the stack (`VerifyError:
  operand stack overflow`); the bridge now takes the `BalmNetworking` receiver as its first
  static parameter so the stack shape is identical.

## Result

`server-net2.log`:

```text
Loading 45 mods: ... balm 21.0.66, trashslot 15.1.5 ...
Preparing level "world"
Done (4.655s)! For help, type "help"
Stopping the server
Saving chunks for level 'ServerLevel[world]'...
ThreadedAnvilChunkStorage: All dimensions are saved
```

`doneSeen=true`, runner exit 0, JVM exit 0. Only Balm refmap warnings are present (the native
Balm jar's refmaps are not readable in this environment; not a trashslot failure).

This is **BOOTED on a dedicated server**, not a gameplay/client pass:
- no client was connected, so the trashslot GUI, clientbound packet delivery, and packet
  encode/decode paths were not exercised;
- the clientbound payload type is registered but no client receiver is installed by the bridge;
- the `ItemStack` NBT bridges are registered but not exercised by a player action.

## Commands / logs

```powershell
python tools/build_bridges.py --stub work/cb/data/jars/client-1.21.1-intermediary.jar `
  --lib <gson> --lib <datafixerupper> --lib work/corpus/deps/balm-fabric-1.21.1-21.0.66.jar `
  --lib <fabric-networking-api-v1> --lib work/target/fabric-api-0.102.0+1.21.1.jar `
  --lib <netty-buffer> --lib <netty-common> --out work/bridges
mcbridge1201 patch --in work/cb/out/trashslot/trashslot-fabric-1.20.1-15.1.5+1.21.1.jar `
  --out work/cb/out/trashslot/trashslot-patched-net2.jar `
  --rules rules/fabric-1.21.1/trashslot.json --bridge-dir work/bridges
python tools/inject_aw.py --jar ... --out ...-aw.jar --aw rules/fabric-1.21.1/mcbridge.accesswidener
python tools/run_server.py --instance work/instances/fabric-1.21.1-server-trashslot `
  --log runs/p17-balm-net/server-net2.log --timeout 240
```

Patch: `initialize` 1, serverbound 2, clientbound 1, NBT 1+1+2+2; bridges embedded.

Hashes (SHA-256):

| Artifact | SHA-256 |
|---|---|
| `trashslot-patched-net2-aw.jar` | `34a22eb1952d52d70f793b49955e9fb021916d7dd967a4fd8b3093836987d770` |
| `server-net2.log` | `b55a1c3931ea312a8fca636ed0c5d97fe6bbf1075f08476b9b7ed38332ea94b4` |
| `patch2.log` | `e08a083d464657a13770c67551d8494160898988e10fdcad76c43649963a83c3` |

## Scope / next

Client GUI, clientbound receiver, packet round-trip, and player trash-slot behavior remain
unverified. The next step is a client fixture or a real player connection, not another server
boot.
