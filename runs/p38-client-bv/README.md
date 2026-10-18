# P38: BytecodeVerify for the P29 trashslot client bridge build

Date: 2026-10-18 (Asia/Shanghai). Verifies the javac client/receiver bridge classes in the
actual patched jar.

## Run

`work/tmp/p29/trashslot-client-aw.jar` (P29 build with `BalmNetworkingBridge$Client`) through
CenturyBridge's `BytecodeVerify`:

```text
verified 47 classes in 1 jars, 0 methods FAILED dataflow verification
```

Exit 0.

This covers `BalmNetworkingBridge`, `$Payload`, `$Client`, the NBT packet bridges and the
rest of the trashslot jar. It does **not** prove client runtime behavior (the client branch is
still unexecuted) and is not a full JVM type verifier.

## Evidence

- `top-level.log`
