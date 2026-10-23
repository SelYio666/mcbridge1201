# p168 — 重登记 MixinBufferRenderer（inert 5 → 4）

日期：2026-10-23。继续处理 p165 的 inert：`hud_batching.compat.MixinBufferRenderer`。

## 内容

- 1.20.4 逻辑：在 `class_286.method_43437/43438`（BufferRenderer 的原始 draw 调用）HEAD 检查
  是否处于 HUD 批处理且有数据，若是则 `BatchingBuffers.forceDrawBuffers()`，避免批处理期间
  直接 draw 造成顺序错乱；
- 1.21.1 里 `class_286.method_43437(class_9801)` 与 `method_43438(class_9801)` 都存在；
  `BatchingBuffer.IS_DRAWING`（public static boolean）也在；
- 规则里重新登记 `hud_batching.compat.MixinBufferRenderer`。

## 结果

```text
audit: listed=35 inert=4 problems=4   （5 → 4）
p168: {"joined": true, "crash": null}  （单人 ColdWorld，64 石头 playerdata）
```

HUD/物品批处理计数继续工作，没有崩溃。

## 诚实限制

- 没有专门制造“批处理中发生原始 draw”的场景去验证 forceDrawBuffers 的时序效果；
- 其余 4 个 inert（BufferBuilder、VertexBuffer、FontManager、MapRenderer）未处理。

## 证据

`launch.log`、`result.json`、`world.png`、`audit.log`。
