# P98: bridge consistency gate

Date: 2026-10-20.

## Problem

Every patched jar embeds its own copy of the bridge classes (`top/mcbridge1201/bridge/*`), and
Fabric loads the first copy it sees. When two jars carry different bridge versions, the older copy
silently wins — this broke ShulkerBoxTooltip's handshake because an older AppleSkin jar's
`FabricLegacyNetworking` lacked `sendPacket`.

## Tool

`tools/check_bridge_consistency.py --bridge-dir work/bridges --jar a.jar --jar b.jar ...`

- hashes every embedded bridge class in each jar;
- compares present classes with the canonical bridge directory;
- also reports cross-jar disagreements for classes not in the canonical directory;
- exits non-zero on any mismatch.

## Patcher fix

`JarPatcher.embedUsedBridges` now **overwrites** every embedded bridge that has a canonical
counterpart (or is generated) with the current bytes. It deliberately does not delete
non-referenced bridge classes: a multi-stage pipeline (IronChests) still needs `CodecDispatch`
embedded by an earlier stage. An earlier attempt that pruned unused bridges removed `CodecDispatch`
and broke IronChests with `NoClassDefFoundError`; that regression is recorded here.

## Result

Six-jar combined set (AppleSkin, Mod Menu, ShulkerBoxTooltip, rebuilt IronChests, Lithium,
TrashSlot):

```text
canonical bridge classes: 33
checked 6 jar(s); problems = 0
```

A combined smoke run after the fix reports `COMBINED_SMOKE in-world` with no tombstone,
NoSuchMethodError, NoClassDefFoundError, or new crash report (`combined-world.png`).

## Evidence

`check.txt`, `client.log`, `combined-world.png`.
