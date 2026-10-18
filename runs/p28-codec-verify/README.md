# P28: BytecodeVerify on the safe CodecDispatch build

Date: 2026-10-18 (Asia/Shanghai). Verifies the P26 javac bridge's bytecode in the actual
patched jar.

## Run

`work/tmp/p26-final/ironchests-safe-aw.jar` (P26 safe `CodecDispatch`, no `$Guard`) was copied
to `work/tmp/p28/bv/` and run through CenturyBridge's `BytecodeVerify`:

```text
verified 73 classes in 1 jars, 0 methods FAILED dataflow verification
```

The nested ResourcefulLib jar was extracted and verified separately:

```text
verified 142 classes in 1 jars, 0 methods FAILED dataflow verification
```

Exit 0 in both runs.

## Meaning / limits

This checks stack depth / declared `max_stack` for every method, including the javac
`CodecDispatch`/`$1`/`$2` classes and the nested ResourcefulLib classes. It is not a full JVM
type verifier and does not prove runtime dispatch semantics; the container contract in
`runs/p26-codec-safe/` and the combined contract in `runs/p27-combined-safe-codec/` cover the
runtime side.

## Evidence

- `top-level.log`
- `nested.log`
