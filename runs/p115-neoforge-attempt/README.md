# p115 — NeoForge 1.21.1: install works, launch blocked in ModLauncher

Goal: turn the launcher's "NeoForge 未实测" note into a real result.

## What worked

- Version list via the official maven JSON (urllib; `requests` gets SSL-reset on
  `maven.neoforged.net`): 259 builds for 1.21.1, latest `21.1.264`.
- Installer downloaded and run by `backend.install_neoforge_direct`:
  `neoforge-21.1.264` profile created.
- `ensure_version_libraries` filled 47 libraries (bootstraplauncher 2.0.2 etc.);
  `ensure_version_jar` copied the inherited `1.21.1.jar` to `<id>.jar` because the library command
  expects it.
- Java selection fixed: NeoForge 21.1 needs Java 21, but `pick_java` had chosen the Java 25 runtime
  (`java-runtime-epsilon`); it now reads `inheritsFrom` and picks `java-runtime-delta` (21.0.7).

## Where it fails

Client launch reaches ModLauncher 11.0.5 and then:

```text
[LaunchServiceHandler/MODLAUNCHER]: Launching target 'forgeclient' with arguments [...]
java.lang.RuntimeException: java.util.NoSuchElementException: No value present
  at cpw.mods.modlauncher.LaunchServiceHandlerDecorator.launch(...)
```

Trying `neoforgeclient` instead gives `Missing launch handler: neoforgeclient`. The real cause is
inside NeoForge's early display, not the launch target:

```text
Caused by: java.util.NoSuchElementException: No value present
  at java.base/java.util.Optional.orElseThrow(Optional.java:377)
  at fml_earlydisplay@4.0.45/net.neoforged.fml.earlydisplay.DisplayWindow.updateModuleReads(DisplayWindow.java:603)
  at fml_loader@4.0.45/.../ImmediateWindowHandler.acceptGameLayer
  ... CommonLaunchHandler.launchService
```

`updateModuleReads` cannot find the expected module in the game layer. Replacing the copied
`neoforge-21.1.264.jar` entry with the inherited `1.21.1.jar` does not help
(`neoforge-basejar-test.log`), so the issue is in how the game layer/module names are built from our
classpath + `-p` module path, not the jar name alone. Logs: `neoforge-launch.log`,
`neoforge-target-test.log`, `neoforge-basejar-test.log`.

## Honest status

- **NeoForge install: verified** (profile + libraries).
- **NeoForge launch: not working.** Not claimed as supported.
- Suspects to investigate next: the `-p` module path contents, `-DlegacyClassPath` need, or the
  library command missing an arg that official launchers pass for NeoForge.

## Improvements kept

- `backend.install_neoforge_direct` (urllib-based installer + version list) as a fallback when the
  library's `requests` cannot reach `maven.neoforged.net`.
- `ensure_version_libraries` / `ensure_version_jar` in `mclaunch` (also benefits Forge).
- `pick_java` now prefers Java 21 for 1.21.1 instead of Java 25 (fixes a real mis-selection).
