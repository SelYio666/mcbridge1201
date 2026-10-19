# P88: six new mods — expansion results and the analyzer fix

Date: 2026-10-19. Tested the content tree `a165ff60…` (remote `3a46e84…`).

Files:

- `EXPANSION-REPORT.md` — the independent expansion report (Chinese);
- `mod-expansion-evidence.zip` — conversion/patch logs, runtime logs, crash reports,
  contract probes, metadata. No game/mod/converted jars inside.

## Result matrix (as reported)

| Mod | Client | Server / feature | Verdict |
|---|---|---|---|
| AppleSkin 2.5.2 | init crash: missing `ClientPlayNetworking$PlayChannelHandler` | not reached | incompatible |
| Mod Menu 7.2.2 | title-screen crash: private `TitleScreen.field_32271` | list not opened | incompatible |
| Clumps 12.0.0.4 | main menu, 120 ticks | boots; orbs 3+7 stay separate (native 1.21.1 merges to 10) | core feature lost |
| FallingTree 4.3.4 | init crash: missing client network handler | server boots, player join throws old `ServerPlayNetworking.send` | incompatible |
| FerriteCore 6.0.1 | main menu, 120 ticks | boots, 200 ticks, saves; 2 mixins removed | boot-only, degraded |
| ShulkerBoxTooltip 4.0.4 | main menu | provider throws `ItemStack.method_7941` tombstone | preview read fails |

All six were converted from the original jar and patched with `container.json` only — no
mod-specific bridges. The report's conclusion is the correct one: the three-mod success does **not**
generalize, and these need new rules/bridges.

## What was fixed in this repository

**Analyzer multi-loader misdetection** (`java/src/main/java/top/mcbridge1201/scan/ArtifactScanner.java`):

- previously `META-INF/neoforge.mods.toml` > `META-INF/mods.toml` > `fabric.mod.json`, so FallingTree
  (Fabric entrypoints **and** a Forge `mods.toml`) was labeled `forge` / `wrong_loader`;
- now Fabric metadata is read first; if it declares entrypoints, `loader=fabric` wins, and
  `Artifact.multiLoader` records that both metadata files exist;
- `Analyzer` no longer turns idle Forge/NeoForge references into `wrong_loader` when the jar has
  valid Fabric entrypoints; it adds a note that those refs were ignored.

Verified: `gradle test installDist` — 23 tests, 0 failures, including a new
`prefersFabricMetadataWhenEntrypointsArePresent` case.

## Not done (needs new rules/bridges)

- AppleSkin / FallingTree: Fabric networking bridge for `registerGlobalReceiver(Identifier,
  PlayChannelHandler)` and `ServerPlayNetworking.send(player, id, buf)` (same class as the
  ResourcefulLib/Balm bridges, but per-call-site rules are required);
- Mod Menu: title-screen field access adaptation;
- Clumps: re-implement the experience-orb merge mixin;
- ShulkerBoxTooltip: ItemStack NBT → data-component bridge for the preview provider;
- FerriteCore: restore the removed `FastMapStateHolderMixin` / `ModelResourceLocationMixin` paths.

## Scope

The report's tests are client boot + server commands, not retail gameplay; Clumps used a frozen-tick
orb fixture, ShulkerBoxTooltip a provider-level read, and no GUI/multiplayer coverage was added.
