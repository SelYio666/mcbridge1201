# P39: evidence-bundle verifier

Date: 2026-10-18 (Asia/Shanghai). A single command that checks the existing evidence without
launching the game.

## Tool

`tools/verify_evidence.py` reads:

- unit-test XML (`18 tests, 0 failures/errors`);
- P14 combined contract;
- P24 chunk stress;
- P26 safe-Codec contract;
- P27 safe-Codec combined contract;
- P33 all-trashslot-packets probe;
- P37 CodecDispatch semantic probe;
- P38 client-bridge BytecodeVerify;
- `git ls-files` (no tracked `.jar`).

It prints a JSON summary and exits non-zero if any check fails.

## Result

```json
{
  "passed": true,
  "checks": {
    "unit_tests": true,
    "combined_contract": true,
    "chunk_stress": true,
    "safe_codec_contract": true,
    "safe_codec_combined": true,
    "trashslot_all_packets": true,
    "codec_dispatch_probe": true,
    "client_bridge_bytecode": true,
    "no_tracked_jars": true
  }
}
```

Exit 0. This is a consistency check over existing logs/verdicts; it does not replace the
server/client contracts or prove client behavior.

## Evidence

- `verify.log` (full JSON)
