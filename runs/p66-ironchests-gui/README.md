# P66: IronChests GUI blocked by a missing client model helper

Date: 2026-10-19 (Asia/Shanghai). Real server-placed iron chest; client rendering crash.

## Setup

Chat commands failed because the world has cheats disabled (`Unknown or incomplete command`). A
server probe then placed the block directly:

```text
IRONCHESTS_SERVER block=Block{ironchests:iron_chest} item=1 ironchests:iron_chest
IRONCHESTS_PLACED=true
```

The client then interacted with `(78,65,-68)`.

## Crash

```text
java.lang.NoClassDefFoundError: net/fabricmc/fabric/api/client/model/BakedModelManagerHelper
at tech.thatgravyboat.ironchests.client.IronChestsClient.loadModel(IronChestsClient.java)
at tech.thatgravyboat.ironchests.client.ChestRenderer.initModels(ChestRenderer.java:99)
```

The 1.20.1 IronChests client model code calls the removed Fabric API helper while rendering the
placed chest. This is a client model bridge gap, not a container/GUI handler failure.

## Status

- block exists and is placed on the server (`PLACED=true`);
- client crashes before a chest GUI can open;
- no IronChests GUI claim;
- existing work-only `IronChestsFabricClient` model replacement may be the fix, but it is not in the
  shipped jar and must be compiled/injected properly.

## Next

Restore the IronChests model-loading bridge (or port `IronChestsClient.loadModel` to
`ModelLoadingPlugin`), then repeat the server-placed chest + client interact test.

## Evidence

- `crash-report.txt`, `latest.log`, `IronChestsGuiProbe.java`
