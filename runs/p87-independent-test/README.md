# P87: independent test report and the fixes it triggered

Date: 2026-10-19. Report tested commit `d9e88a1`.

Files:

- `TEST-REPORT.md` — the independent report (Chinese), 3 × P1 + 3 × P2 findings;
- `test-evidence.zip` — the tester's logs (build, JUnit XML, real server logs, negative
  controls). No game/mod/converted jars inside.

## Findings and disposition

| # | Finding | Fix in this commit |
|---|---|---|
| P1-1 | `docs/distribution.md` presented patching a raw 1.20.1 jar as conversion; the rebuild script needs an intermediate `ironchests-modelbridge2.jar` | Docs now describe the three-stage pipeline and mark single-file `patch` as "converted input only"; the rebuild script fails with a message naming the missing stage |
| P1-2 | `run_chunk_stress.py` counted the `# > execute ...` echo as `STRESS_OK_A/B` | Marker matching skips `# >` echo lines |
| P1-3 | `run_server.py` returned 0 after seeing `Done` even when the JVM later exited non-zero | Exit code is propagated; timeout is failure |
| P2-1 | "feature-preserving" wording vs lithium's explicit mixin degradations | `docs/distribution.md` lists the disabled mixins and un-rewritten chunk fast paths |
| P2-2 | Two-client probe assumed terrain/distance and indexed slot 54 unguarded | Probe builds a 3×3 platform, clears the space above, and returns `n/a` when the menu has fewer than 55 slots |
| P2-3 | `runs/SHA256SUMS.txt` stale for `tools/verify_evidence.py` | Regenerated; now also covers `run_server.py`, `rebuild_ironchests_client.py`, `distribution.md` |

## Verification

- `python tools/verify_evidence.py` → `passed: true`;
- `python -m py_compile` on the three edited scripts → exit 0;
- **negative control re-run**: extracted the tester's `CrashAfterDone.java`, packaged it as a fake
  `fabric-server-launch.jar`, and ran `tools/run_server.py` against it. The stub prints
  `Done (0.001s)` and then exits 7; `doneSeen=true, exitCode=7`, and the script now returns **7**
  (before the fix it returned 0). Log: `run-server-exitcode.log`;
- probe source changes are guarded (no unguarded `method_7611(54)`).

## Not yet re-run

The fixed chunk-stress marker matching was not re-exercised against a live server in this commit;
the tester's negative control (`logs/controls/false-marker.log`) is preserved in
`test-evidence.zip`, and the new matcher skips `# >` echo lines.
