# P70: chest persistence fixed + clientbound content sync verified

Date: 2026-10-19 (Asia/Shanghai). Corrects the P67 NBT bridge direction and proves the S2C chest
content sync.

## The bug P69 did not catch

P69 put an item in, then took it back out — it never closed and reopened. Adding that step showed:

```text
IRONCHESTS_BE tick=240 slot0=25 diamonds
IRONCHESTS_CLOSED screen=null
IRONCHESTS_BE tick=280 slot0=25 diamonds
IRONCHESTS_BE tick=320 slot0=0 air          <- reopen wiped the chest
```

The item survived the close (tick 280) but the **reopen** cleared it.

## Root cause: the converted bodies are swapped, not the calls

Decompiling the converted `GenericChestBlockEntity`:

- `method_11014(NbtCompound, Provider)` **clears `items` and reads the tag into the entity**
  (`class_1262.method_5429` = read);
- `method_11007(NbtCompound, Provider)` **writes the entity into the tag**
  (`class_1262.method_5426` = write).

So the converter swapped the method **bodies**, while the call sites were already correct
(`getSyncTag` → `method_11007`, `loadSyncTag` → `method_11014`). The P67 bridge "corrected" the calls
by name and therefore inverted them: `getSyncTag` ran the read path with an empty tag, wiping the
inventory on every open.

## Fix

`IronChestsNbtBridge` now calls the converted bodies by behaviour:

- `writeSyncTag` (for `getSyncTag`) → `method_11007` (writes);
- `readSyncTag` (for `loadSyncTag`) → `method_11014` (reads).

The call-site rules are unchanged; only the bridge body direction changed.

## Result

```text
IRONCHESTS_BE tick=240 slot0=25 diamonds
IRONCHESTS_CLOSED screen=null
IRONCHESTS_BE tick=280 slot0=25 diamonds
IRONCHESTS_BE tick=320 slot0=25 diamonds
IRONCHESTS_SERVER_MENU tick=320 sync=2 slot0=25 diamonds
IRONCHESTS_REOPEN screen=ChestScreen sync=2 slot0=25 diamonds
```

The chest keeps its contents across close/reopen, and the reopened client menu shows the server
state (`slot0=25 diamonds`) — i.e. the clientbound chest content sync works too.

## Evidence

- `latest.log`, `IronChestsGuiProbe.java`, `IronChestsNbtBridge.java`

## Note

This supersedes the P67 claim that the sync NBT was fully fixed: the rules were applied, but the
bridge direction was wrong and introduced silent data loss. P67's README carries a correction note.
