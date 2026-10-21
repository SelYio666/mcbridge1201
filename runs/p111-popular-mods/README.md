# p111 — popular 1.20.1 mods, first conversion attempt

Goal: stop hand-picking mods and test the toolchain on the actual download chart. The list below was
pulled from Modrinth (`/v2/search`, facets `categories:fabric` + `versions:1.20.1`, index by
downloads) on 2026-10-21.

Top hits (downloads): Fabric API 285M, Sodium 250M, Iris 194M, Entity Culling 187M,
Cloth Config 183M, FerriteCore 164M, Mod Menu 159M, Lithium 140M, ImmediatelyFast 136M,
YACL 134M, Fabric Language Kotlin 130M, Xaero's Minimap 120M, VeinMiner 99.5M.

Tested this run: **VeinMiner 2.0.7**, **EntityCulling 1.11.3**, **ImmediatelyFast 1.5.5**
(1.20.1 Fabric builds from Modrinth).

## Pipeline used

1. `CenturyBridge convert data/segments 1.20.1 1.21.1 out/popular/<slug> <mod.jar>` (bundled
   TRansition/TRender jars for EntityCulling converted separately).
2. For EntityCulling: bump nested libraries to 1.21.1 in their `fabric.mod.json` and replace them
   inside the outer jar; then `mcbridge1201 patch` with `identifier-single-arg.json` (the converted
   nested code still called the now-private `new Identifier(String)`).
3. Boot tests: dedicated server (VeinMiner) and client (EntityCulling), Fabric API 0.102.0.

## Results

| Mod | Verdict | What ran | Outcome |
|---|---|---|---|
| VeinMiner | `ok_partial` (3 L2 issues) | Server boots (`Done (1.021s)`) with fabric-language-kotlin + silk | **Boot-level only**; vein-mining behavior not exercised |
| EntityCulling | `ok_degraded_partial`, **stripped load-bearing `EntityRendererMixin`** | Client boots to menu, joins the server world (`entityculling-world.png`) | Boots, but the culling feature is not verified; a load-bearing mixin was stripped by the converter, so this is **not a functional pass** |
| ImmediatelyFast | `ok_degraded_partial`, 6 load-bearing mixins stripped | Client crashes at mixin apply | `@Overwrite method method_22992(Ljava/util/Map;Lnet/minecraft/class_287;)Lnet/minecraft/class_4597$class_4598;` descriptor does not match 1.21.1 |

Raw crash causes:

- EntityCulling first crash: `NoClassDefFoundError: dev/tr7zw/transition/manager/CodeManager` — the
  bundled TRansition/TRender jars were still 1.20.1 builds, so Loader refused them.
- After converting them, the next crash was `NoSuchMethodError: 'void net.minecraft.class_2960.<init>
  (java.lang.String)'` in `dev.tr7zw.transition.mc.GeneralUtil.getResourceLocation` — fixed by the
  existing `identifier-single-arg` rule.
- ImmediatelyFast: `InvalidMixinException: @Overwrite ... in MixinVertexConsumerProvider ...`.
  The converter keeps the mixin when the target signature changed (`kept L2 mixin (target sig
  changed)`), so the `@Overwrite` no longer lines up with the 1.21.1 method.

## What this says about the toolchain

- Data/logic-heavy mods (VeinMiner) are the near-term sweet spot: conversion finishes and the JVM
  boots the result.
- Render-internal mods (EntityCulling, ImmediatelyFast) are gated by **Fabric mixin targets**, not by
  ordinary call sites. The converter can strip or keep a mixin, but it does not rewrite `@Overwrite`
  descriptors / injection points; that still needs per-mod rules or a manual replacement class.
- Nested jars are a pipeline gap: bundled libraries must themselves be converted + their
  `fabric.mod.json` bumped, otherwise Loader rejects them and the outer mod dies at entrypoint.
- The converter's own verdicts (`ok_degraded_partial`, "stripped ... [load-bearing!]") are the honest
  signal; boot success alone must not be reported as compatibility.

## Evidence

- `server-veinminer.log` — server boot with converted VeinMiner
- `entityculling-mainmenu.png`, `entityculling-world.png` — client menu and in-world with converted EntityCulling
- `immediatelyfast-crash.txt` — mixin apply failure
- `entityculling-missing-transition-crash.txt`, `entityculling-identifier-crash.txt` — the two earlier EntityCulling crashes
- `veinminer-report.md`, `entityculling-report.md`, `immediatelyfast-report.md` — CenturyBridge verdicts
