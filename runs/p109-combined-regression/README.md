# P109: combined regression run

Date: 2026-10-20 (after v0.2.0).

## Purpose

Re-run the combined mod set with the jars rebuilt during this session, to check that the later
bridge changes (Identifier constructors, status-effect bridges, FallingTree bridges, AppleSkin
tooltip bridge, bridge overwrite logic) did not regress the earlier combined smoke.

## Setup

Client mods: AppleSkin (patched), Mod Menu (patched), ShulkerBoxTooltip (patched), IronChests
(rebuilt), Lithium, TrashSlot, Balm and Fabric API. Quickplay into `New World`; a probe waits for a
loaded world and screenshots it.

## Result

```text
[23:12:41] [STDOUT]: COMBINED_SMOKE in-world player=literal{TestPlayer}
[23:12:41] [STDOUT]: COMBINED_SCREENSHOT screenshot.success combined-world.png
```

No tombstone, NoSuchMethodError, NoClassDefFoundError or new crash report (newest crash file is from
21:05, before the run).

## Scope

- Load/join smoke only; it does not exercise each mod's features again (those have their own P
  runs).
- Client-only; the dedicated server was not part of this run.

## Evidence

`client.log`, `combined-world.png`.
