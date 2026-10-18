# P47: field `@At` target parsing

Date: 2026-10-18 (Asia/Shanghai). Adds a synthetic test for the FIELD branch of the P34/P35
at-target parser.

## Test

```java
@Inject(method = "method_59()V")
@At(value = "FIELD", target = "Lnet/minecraft/class_14;field_99:Lnet/minecraft/class_1799;")
```

Assertions:

- `atValue == "FIELD"`;
- `atTargetField == true`;
- owner `net/minecraft/class_14`;
- name `field_99`;
- descriptor `Lnet/minecraft/class_1799;`.

The analyzer only checks intermediary FIELD targets, so this pins the parse shape it relies on.

## Result

`gradle --no-daemon test --rerun-tasks`: **20/20 pass** (was 19).

## Evidence

- `gradle-test.log`
