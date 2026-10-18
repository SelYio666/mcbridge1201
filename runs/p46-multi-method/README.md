# P46: pin multi-method injection arrays

Date: 2026-10-18 (Asia/Shanghai). Regression test for the P34 scanner fix.

## What

A synthetic `@Inject` with

```java
method = {"method_59()V", "method_60()V"}
```

must produce **two** `Injection` entries, each carrying the shared `@At` target. Before the
P34 fix the scanner collapsed the array into one entry (lithium dropped from 214 to 207).

The test asserts:

- `injections.size() == 2`;
- target names `method_59`, `method_60`;
- both share at-target `method_61`.

## Result

`gradle --no-daemon test --rerun-tasks`: **19/19 pass** (was 18; new test added).

## Evidence

- `gradle-test.log`
