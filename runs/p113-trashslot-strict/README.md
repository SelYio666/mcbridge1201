# p113 — strict TrashSlot NBT bridge, runtime regression (ISSUE-01)

Goal: prove the ISSUE-01 fix in a real client, not just at compile time. A small client probe calls
`TrashSlotNbtBridge` directly inside a live Fabric 1.21.1 client that joined a local server.

## Setup

- Client root: `work/launcher-fresh2` (installed by our launcher: vanilla 1.21.1 + Fabric Loader 0.19.5).
- Mods: `fabric-api` + `probes/strictprobe` (calls the bridge once a player exists).
- Server: `work/instances/fabric-1.21.1-server`, Fabric API only.
- Launch: our `mclaunch.build_command` with
  `--quickPlayPath <file> --quickPlayMultiplayer 127.0.0.1:25565`.
  Note: quick play needs **both** args; `--quickPlayMultiplayer` alone was ignored. The first-run
  accessibility screen also blocks quick play, so `options.txt` contains `onboardAccessibility:false`.

## Results (runs/p113-trashslot-strict/strict-markers.txt)

```text
STRICT_READY tick=80
STRICT_VALID OK                 # diamond x5 via writeItem -> readItem round-trip
STRICT_SAVE OK                  # save() into a fresh compound -> load()
STRICT_EMPTY OK                 # empty compound -> ItemStack.EMPTY (legal empty, no throw)
STRICT_INVALID_THROWN           # unknown item id -> IllegalStateException
STRICT_TYPED_THROWN             # string "count"/"Slot" -> IllegalStateException
STRICT_DONE
```

## Discovery while testing

The first run showed `STRICT_TYPED_NOT_THROWN count=1`: the vanilla ItemStack codec silently coerced a
string `count` to its default `1`. That is exactly the silent data change ISSUE-01 is about, so the
bridge now rejects string-typed `count`/`Slot` before parsing.

## Honest scope

This exercises the bridge API (save / writeItem / readItem / load) with real Minecraft classes and
registries. The normal path is covered (VALID/SAVE/EMPTY), and both failure branches throw.

It does **not** re-run the full TrashSlot UI flow (open panel, move item, close, rejoin). That flow was
already recorded with the previous bridge build under `runs/p63-trash-debug/`, `p64-trash-s2c/` and
`p65-trash-empty/`; the strict change only touches failure branches and the new string-type guard, which
this probe covers directly.

## Reproduce

```text
gradle -p java installDist                 # patch CLI + bridges deps
python tools/build_strict_probe.py         # needs JAVA_HOME and work/bridges
# copy work/tmp/strictprobe/strictprobe.jar into <client-root>/mods
python launcher/mclaunch.py launch fabric-loader-0.19.5-1.21.1 <client-root> StrictUser
```

(Launch with the quick-play args above when driving the probe automatically.)
