# P19: BytecodeVerify on the patched sample jars

Date: 2026-10-18 (Asia/Shanghai). Closes the "BytecodeVerify 未编译运行" gap.

## What was run

Compiled CenturyBridge's `core/tools/BytecodeVerify.java` against ASM 9.7.1 (asm, asm-tree,
asm-commons, asm-analysis) and ran it over the patched jars:

- ironchests `ironchests-5.0.2-fabric+1.21.1-aw.jar`
- lithium `lithium-patched-chunkport.jar`
- trashslot `trashslot-patched-net2-aw.jar`

Result:

```text
verified 650 classes in 3 jars, 0 methods FAILED dataflow verification
```

Then extracted the nested jar from ironchests (`ResourcefulLib 2.0.6`) and verified it separately:

```text
verified 141 classes in 1 jars, 0 methods FAILED dataflow verification
```

Exit 0 in both runs.

## What this proves / does not prove

`BytecodeVerify` uses ASM's `BasicInterpreter` to walk each method and compare tracked stack
depth with the declared `max_stack`; it catches stack under/overflow from rewrites that push
values without recomputing `max_stack`. It is **not** a full JVM type verifier and does not prove
runtime semantics. It covers the top-level classes of the three patched jars plus the one nested
ResourcefulLib jar; other nested jars/client paths are not covered.

## Commands

```powershell
javac -cp "asm-9.7.1.jar;asm-tree-9.7.1.jar;asm-commons-9.7.1.jar;asm-analysis-9.7.1.jar" `
  -d work/tmp/bytecodeverify <CenturyBridge>/core/tools/BytecodeVerify.java
java -cp "work/tmp/bytecodeverify;<asm jars>" BytecodeVerify work/tmp/bv
java -cp "work/tmp/bytecodeverify;<asm jars>" BytecodeVerify work/tmp/bv-nested
```

Logs: `compile.log`, `verify.log`, `verify-nested.log`.
