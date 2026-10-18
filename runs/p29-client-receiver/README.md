# P29: clientbound receiver for the Balm networking bridge

Date: 2026-10-18 (Asia/Shanghai). Adds the client side of the P17 payload bridge; dedicated
server boot is the only executed path in this environment.

## What changed

`BalmNetworkingBridge` now has a nested client-only helper:

```java
public static final class Client {
    public static <T> void register(PacketType<Payload<T>> type,
                                    BiConsumer<Player, T> handler) {
        ClientPlayNetworking.registerGlobalReceiver(type,
            (payload, context) -> handler.accept(context.player(), payload.value()));
    }
}
```

`registerClientbound` checks the Fabric environment through reflection and, only on
`CLIENT`, reflectively invokes `BalmNetworkingBridge$Client.register`. The server never loads
the client class. The nested class is embedded by the existing `BalmNetworkingBridge$...`
prefix rule.

## Server verification

Patched trashslot with the updated bridge, injected AW, and booted the dedicated server:

```text
Done (4.894s)! For help, type "help"
```

`doneSeen=true`, runner/JVM exit 0. The embedded bridge now contains
`BalmNetworkingBridge`, `$Payload`, `$Client`; no server-side class-loading error from
`ClientPlayNetworking`.

## Limitation

No client fixture is available, so the client branch, `ClientPlayNetworking` registration,
and `MessageTrashSlotContent` delivery/decoding are **not executed or verified**. The server
boot only proves the server branch is inert and the class bundle loads.

## Evidence

- `build-bridges.log`
- `patch.log`
- `inject-aw.log`
- `server.log` / `server.result.json`
