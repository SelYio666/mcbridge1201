# P59: trash GUI transfer works after the serverbound Balm bridge

Date: 2026-10-19 (Asia/Shanghai). First successful trash GUI interaction.

## Fix

The first real trash click produced:

```text
NoSuchMethodError: 'void net.blay09.mods.balm.api.network.BalmNetworking.sendToServer(java.lang.Object)'
at DefaultDeletionProvider.deleteMouseItem(DefaultDeletionProvider.java:33)
```

Balm 21 changed the generic to `sendToServer(T extends CustomPayload)`, so the old `Object`
descriptor no longer links. Added:

- `BalmNetworkingBridge.sendToServer(BalmNetworking, Object)`: looks up the payload registered by
  `registerServerbound` and calls `ClientPlayNetworking.send`;
- `trashslot-sendtoserver.json` redirect: 4 call sites, `INVOKEINTERFACE`
  `BalmNetworking.sendToServer(Object)`.

## Result

With the patched jar, clicking the diamond stack then the trash slot moved the **5 diamonds into
the trash slot** (`after-send.png`, tooltip `Diamond`). No `NoSuchMethodError`; the client stayed
alive.

A second click on the trash slot (`undelete.png`, `after-take.png`) did not return the stack; it
remained in the trash slot. Undelete/return path is not confirmed.

## Server confirmation

A server-side tick probe reads `TrashHelper.getTrashItem(joined)` every 40 ticks. After the click:

```text
SERVER_TRASH count=5 item=minecraft:diamond
```

so the server accepted the serverbound packet and stored 5 diamonds. No `NoSuchMethodError`.

## Verified

| step | result |
|---|---|
| click item then trash slot | **5 diamonds moved into trash** |
| serverbound `sendToServer` link | no crash |
| server-side trash content | **5 diamonds** |
| client stays alive | yes |

## Not verified

- return/undelete path (`undeleteLast`; second click did not clear it);
- empty-trash action;
- restart persistence (TrashSlot clears trash on login by design);
- ironchests GUI / clientbound delivery / two-client sync.

## Environment note

`gradle test` could not start in this session: `Could not initialize native services` /
`Failed to load native library 'native-platform.dll'`. The bridge itself compiled and the javac
bridge build succeeded (`build-bridges.log`); the previous suite was 22/22. This is an environment
failure, not a code test result.

## Evidence

- `after-send.png`, `undelete.png`, `latest.log`, `client.log`
- `TrashClickProbe.java`, `trashslot-sendtoserver.json`
