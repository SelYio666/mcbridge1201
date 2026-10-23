# p167 — 重登记 MixinMinecraftClient（inert 6 → 5）

日期：2026-10-23。继续处理 p165 审计出的 inert：这次是 `core.MixinMinecraftClient`。

## 内容

- 1.20.4 逻辑：`<init>` RETURN 调 `ImmediatelyFast.lateInit()`；`method_1481` HEAD 调
  `ImmediatelyFast.onWorldJoin()`；
- 1.21.1 里 `<init>` 与 `method_1481(class_638, class_434$class_9678)` 都存在，按名字注入；
- 规则 `mixinConfigAdditions` 重新登记 `core.MixinMinecraftClient`。

## 结果

```text
audit_mixins: configs=2 errors=0 listed=34 inert=5 problems=5   （inert 6 → 5）
p167: {"joined": true, "crash": null}   （单人 ColdWorld，64 石头 playerdata）
```

- 启动、进世界、HUD 批处理正常，无崩溃；
- `MixinMinecraftClient` 不再 inert，`lateInit()` / `onWorldJoin()` 会被调用（没有单独日志证明内部
  效果，只能证明注入生效且不崩）。

## 诚实限制

- 没有验证 `lateInit()/onWorldJoin()` 的具体副作用（如缓存/告示牌文本缓存）；
- 其余 5 个 inert（BufferBuilder、VertexBuffer、FontManager、BufferRenderer、MapRenderer）未处理。

## 证据

`launch.log`、`result.json`、`world.png`、`audit.log`。
