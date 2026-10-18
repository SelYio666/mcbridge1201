# P32: trashslot packet codec round-trip (server-side probe)

Date: 2026-10-18 (Asia/Shanghai). Exercises the four ItemStack/NBT bridges without a client.

## Probe

A tiny Fabric test mod (`codecprobe`) registers `ServerLifecycleEvents.SERVER_STARTED` and runs
`MessageTrashSlotClick.encode/decode` against a `FriendlyByteBuf`:

1. empty `ItemStack` (`ItemStack.EMPTY`) -> decode -> assert `isEmpty()`;
2. `new ItemStack(Items.DIAMOND, 5)` -> decode -> assert non-empty, count 5, same item.

The probe is loaded into `fabric-1.21.1-server-trashslot` alongside the P29 trashslot build and
native Balm 21.0.66.

## Result

```text
Done (5.025s)! For help, type "help"
[STDOUT]: TRASHSLOT_CODEC_OK
```

`doneSeen=true`, runner/JVM exit 0. This covers:

- `MessageTrashSlotClick.encode` / `decode`;
- `TrashSlotNbtBridge.writeItem` / `readItem` (P17/P29 packet bridges);
- `FriendlyByteBuf` NBT write/read and the registry-aware `ItemStack.CODEC` path;
- both empty and non-empty stack components.

It does **not** cover client network delivery, `ClientPlayNetworking`, the trash GUI, or a
player action; those remain pending.

## Evidence

- `compile.log`
- `jar.log`
- `server.log` / `server.result.json`
