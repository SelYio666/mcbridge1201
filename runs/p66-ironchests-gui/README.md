# P66: IronChests client model fixed; next blocker is BlockEntity NBT

Date: 2026-10-19 (Asia/Shanghai). Iterative real-client test of the IronChests GUI path.

## 1. First blocker: removed Fabric model helper (fixed)

Rendering the server-placed chest crashed with:

```text
NoClassDefFoundError: net/fabricmc/fabric/api/client/model/BakedModelManagerHelper
at tech.thatgravyboat.ironchests.client.IronChestsClient.loadModel
```

Root cause: the 1.20.1 IronChests client calls `BakedModelManagerHelper.getModel(BakedModelManager,
Identifier)`, removed in 1.21.1. Work-only fix (not shipped yet):

- `BakedModelManagerHelper.java`: compatibility shim implementing
  `getModel(class_1092 manager, class_2960 id)` as
  `manager.method_4742(class_1091.method_61078(id))`;
- `IronChestsFabricClient.java`: 1.21.1 entrypoint that calls `IronChestsClient.init()` and
  registers the lid/base models through `ModelLoadingPlugin`;
- both were compiled and injected into the client mod jar for this test.

After that, the chest **renders without crashing**.

## 2. Second blocker: 1.20.1 `BlockEntity.readNbt`

Driving the chest's own `onUse` server-side (`GenericChestBlock.method_9534`) now reaches:

```text
IRONCHESTS_USE_ERROR cause=java.lang.NoSuchMethodError:
  'void tech.thatgravyboat.ironchests.common.blocks.GenericChestBlockEntity.method_11007(net.minecraft.class_2487)'
```

That is the old one-argument `readNbt(NbtCompound)`. 1.21.1 uses
`readNbt(NbtCompound, RegistryWrapper.WrapperLookup)`, so the converted block entity no longer has
the one-arg method that another call site still invokes. This must be bridged before the chest menu
can open; it is the same NBT-signature family as the TrashSlot bridges.

## 3. Other observations

- chat `give`/`setblock` fail: the test world has cheats disabled (`Unknown or incomplete command`);
- the block is placed successfully via a server probe
  (`IRONCHESTS_STATE=Block{ironchests:iron_chest}[facing=north,lock=no_lock,...]`);
- `PLACED=false` on later runs just means the block is already present;
- no `NoClassDefFoundError`/model crash after the shim.

## Status

| step | result |
|---|---|
| IronChests client model rendering | **fixed by shim (work-only)** |
| chest block placement | pass |
| chest menu open | blocked by `method_11007(NbtCompound)` |
| GUI screenshot | not yet |

## Next

Add a `method_11007(NbtCompound)` → 1.21.1 NBT-read bridge for the IronChests block entity (or a
class replacement that supplies the one-arg method delegating to the two-arg form), then repeat the
server-use + client screenshot test.

## Evidence

- `crash-report.txt` (first model crash), `latest-model-shim.log` (shim result + new blocker)
- `BakedModelManagerHelper.java`, `IronChestsFabricClient.java`, `IronChestsGuiProbe.java`
