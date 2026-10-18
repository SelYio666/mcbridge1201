# P50: first real client run (PCL, Fabric 1.21.1) — new blocker

Date: 2026-10-19 (Asia/Shanghai). The dedicated-server evidence did not cover this path.

## What was installed

PCL existed at:

- launcher: `D:\浏览器所下载文件\我的世界PCL2启动器_2.12.8.2\plain craft launcher 2.exe`
- home: `D:\我的世界\.minecraft`
- base: `1.21.1` (client jar + 1.21.1 libraries + asset index 17 objects)
- Fabric profile: `fabric-loader-0.19.5-1.21.1`

The Fabric installer needed the PCL Microsoft Java 21
(`...\java-runtime-delta\...\java.exe`); the workspace JDK failed TLS with
`NoSuchAlgorithmException: Error constructing implementation` even with an explicit trust store.

Mods in the profile:

- Fabric API `0.102.0+1.21.1`
- Balm `21.0.66`
- lithium `0.11.4+1.21.1-patched`
- ironchests-safe-aw (P26)
- trashslot-client-aw (P29)

## Result

The client started, Fabric loaded all mods (including ResourcefulLib 2.0.6 nested in
ironchests), got to `Initializing game`, then crashed:

```text
java.lang.RuntimeException: Could not execute entrypoint stage 'main' due to errors,
provided by 'ironchests' at '...IronChestsFabric'!
Caused by: java.lang.NoClassDefFoundError:
  net/fabricmc/fabric/api/client/networking/v1/ClientPlayNetworking$PlayChannelHandler
  at ...resourcefullib...FabricClientPacketHelper.clientOnlyRegister(...)
```

This is a **real client-only blocker** that the dedicated server never executes: ResourcefulLib
2.0.6 uses the old Fabric `ClientPlayNetworking.PlayChannelHandler` /
`registerGlobalReceiver(Identifier, PlayChannelHandler)` API. 1.21.1 has
`PlayPayloadHandler` and `CustomPayload` instead.

A quick experiment replacing the nested ResourcefulLib with the 1.21.1 `3.0.12` build moved the
failure to `NoClassDefFoundError: ...networking.base.PacketHandler` (removed/renamed in 3.x), so
that is not a drop-in fix.

## Next work

1. Client networking bridge for ResourcefulLib 2.0.6:
   - old `registerGlobalReceiver(Identifier, PlayChannelHandler)` → new payload id + payload
     handler;
   - old `send(Identifier, FriendlyByteBuf)` → `ClientPlayNetworking.send(CustomPayload)`;
   - needs a payload type/codec and the old handler interface kept linkable.
2. Or replace/patch ResourcefulLib's client helper to its 1.21.1 shape while preserving the old
   `PacketHandler` API used by ironchests.
3. Then re-run: client main menu, ironchests GUI, trashslot GUI, clientbound delivery, restart
   persistence, two-client sync.

## Scope / evidence

This is a **failure record**, not a pass. No client profile status is upgraded. Jars are not
committed; the PCL profile is outside the repository.

- `client.log`
- `crash-report.txt`
- `launch.pid` / `launch-rl3.pid`
