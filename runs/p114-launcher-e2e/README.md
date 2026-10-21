# p114 — launcher end-to-end: install into an empty root, then launch

Goal: prove the launcher really installs a version into a fresh directory and starts it, using
`tools/test_launcher_e2e.py`.

## Run

1. `python tools/test_launcher_e2e.py --root work/launcher-e2e --mc 1.21.1`
   - downloaded vanilla 1.21.1 into the empty root and installed Fabric 0.19.5;
   - the root grew to ~915 MB; `mclaunch verify 1.21.1` reports
     `client jar ok / libraries 70/70 / natives 9 dll / assets 3911/3911 → RESULT: OK`;
   - this phase took about **36 minutes** on this network (resource CDN slow).
2. The first run then failed at the final step with
   `FileNotFoundError: .../logs/launch-...log` — the script opened the log file before creating
   `logs/`. Fixed in `tools/test_launcher_e2e.py` (`log.parent.mkdir`).
3. Re-ran the launch phase against the same root with `--no-install`:

```text
launching fabric-loader-0.19.5-1.21.1 -> .../logs/launch-20261021-212841.log
RESULT: OK
```

Client log: `Setting user: E2EUser`, `Backend library: LWJGL version 3.3.3-snapshot`, no
`AccessDenied` / `Uncaught` markers (see `launch.log`).

## Honest scope

- Install and launch were verified, but **not in one uninterrupted run**: the install phase completed
  before the log-dir bug stopped the script, and the launch was re-run with `--no-install`.
- `--no-install` mode was also verified earlier against `work/launcher-fresh2`.
- The slow resource CDN is an environment limit, not a correctness issue; `verify` already reports
  completeness independently.
