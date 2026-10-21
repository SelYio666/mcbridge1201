# p112 — local GUI launcher, offline Fabric verified

Built a small launcher next to the converter: a local web GUI that downloads Minecraft versions from
official sources (with a BMCLAPI mirror fallback), installs Fabric from the official meta, and launches
offline. No game files are bundled.

## What was verified

| Step | Evidence |
|---|---|
| Version manifest + vanilla install path (client jar, libraries, natives) | `task` progress `libraries 70/70`, natives extracted (8 dlls) |
| Fabric install from official meta (loader libs, profile json) | `task: done fabric-loader-0.19.5-1.21.1` |
| Offline launch, Fabric 1.21.1 | `launcher-fabric-menu.png` — `Minecraft* 1.21.1` first-run screen, `Setting user`, `Backend library: LWJGL` |
| GUI page | `launcher-gui.png` — version list (1.16.5 / 1.20.1 / Forge / 1.21.1), filters, install form, console |
| GUI API end-to-end | `POST /api/install` → `task done`; `POST /api/launch` → pid + log, window up |
| Asset mirror | official `resources.download.minecraft.net` times out here; BMCLAPI returns 200 and the installer advances (40/3911 before the run was stopped) |

## Bugs found and fixed while doing this

- Placeholder substitution: version JSON uses `${name}`, a plain `format()` left a literal `$` in every
  argument (fixed by replacing `${` before formatting).
- Natives: 1.21.1 ships natives as `natives-windows` classifiers, not the old `natives` map; extraction
  now handles both, and the Fabric profile reuses the base version's natives directory.
- Runtime: the repo `.toolchain` JDK runs with a restricted token in this environment (registry/temp
  writes denied, so Fabric's `.fabric` cache could not be created). The launcher now prefers the
  official launcher runtime (`Packages\Microsoft.4297127D64EC6_*`), then system Java/Temurin, and only
  falls back to `.toolchain`.
- Assets: the official asset CDN is unreachable from this network; downloader now tries BMCLAPI first
  and falls back to the official URL.

## Honest limits

- Forge/NeoForge **install** code exists but **launch is not verified**: the module path /
  `-DlegacyClassPath` wiring still fails (`ResolutionException: Modules _1._20._1 and minecraft export
  package net.minecraft.server`). Only Fabric + vanilla are proven.
- Full asset download did not finish here (3911 objects, slow link). The two missing font objects were
  fetched manually from the mirror to confirm the menu renders.
- GUI is a local web page, not a packaged exe.
