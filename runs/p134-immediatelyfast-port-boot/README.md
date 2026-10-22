# p134 — ImmediatelyFast 1.21.1 batching 移植：启动、进世界、HUD 批处理生效

日期：2026-10-22。目标 B 的核心结果：1.20.4 的 ImmediatelyFast batching 引擎移植到 1.21.1，
**启动、进单人世界，HUD 专用批处理真的在跑**（可测计数 + 关闭开关对照）。

## 移植内容

| 类 | 作用 | 1.21.1 适配 |
|---|---|---|
| `BatchableBufferSource` | 每 RenderLayer 的 BufferBuilder 批处理与绘制 | `ByteBufferBuilder` + `BufferBuilder(allocator, DrawMode, VertexFormat)`；反射私有 `Immediate.method_60893`、`field_52071/field_52156` |
| `BatchingBuffers` | HUD/物品批处理开关与消费者（保留 1.20.4 mixin API） | 内部用 `HudBatchingBufferSource`；per-batch 计数日志 |
| `HudBatchingBufferSource` | HUD 批处理消费者 | 继承移植后的 `BatchableBufferSource` |
| `SimpleImmediate` | 关闭 universal batching 时的普通 Immediate | 公开构造器 |
| `BatchingRenderLayers` | 自定义 GUI textured/colored 层 | 1.21.1 `RenderLayer` 构造 + shader 引用 |
| `BlendFuncDepthFuncState` | 混合/深度状态快照 | `GlStateManager` 私有字段反射读取 |
| `MixinVertexConsumerProvider` | `class_4597.method_22992` 工厂 | 新描述符返回 `BatchableBufferSource` |
| `MixinTextRenderer_Drawer` | 字体 getBuffer 去重 | 私有 `field_1556` 反射替代 `method_22893` |
| `MixinDrawContext` | HUD fill/drawTexture 写入批缓冲 | 1.21.1 方法签名；检查 DrawContext 的 `HudBatchingBufferSource` |
| `MixinGameRendererHud` | 把 `InGameHud.render` 包进 `runBatched` | 用 `@Redirect` 替代 MixinExtras `WrapOperation` |

规则：`rules/fabric-1.21.1/immediatelyfast-batching-port.json`
（6 个类替换 + 2 个 mixin 配置补充 + 2 条 Identifier 重定向）。

## 启动与功能证据

- Fabric Loader 0.19.5 + Fabric API 0.102.0 + 移植后的 ImmediatelyFast，Java 21；
- `--quickPlaySingleplayer ColdWorld`，`IFUser joined the game`；
- 真实计数（本次）：

  ```text
  [mcbridge-port] hud batching begin
  [mcbridge-port] batched-draws total=5632  hud=1501 itemModel=0 itemOverlay=0
  [mcbridge-port] batched-draws total=9414  hud=2409 itemModel=0 itemOverlay=0
  [mcbridge-port] batched-draws total=13374 hud=3289 itemModel=0 itemOverlay=0
  [mcbridge-port] batched-draws total=16968 hud=4052 itemModel=0 itemOverlay=0
  ```

- A/B（`runs/p137-immediatelyfast-hud-off/`）：`hud_batching=false` 时仍进世界，但**没有任何**
  `[mcbridge-port]` 标记（hud 计数不产生）→ HUD 批处理确实由该开关控制；
- 截图 `world.png`：世界内 F3/HUD 文字、心、物品栏正常。

## 诚实限制

- `itemModel/itemOverlay` 专用批次仍为 0：1.21.1 的物品渲染路径（`MixinItemRenderer`/照明变体）
  未移植；HUD 内的物品 quad 由 HUD consumer 批处理，但没有 ImFast 原版的 per-lighting 分批；
- Iris 兼容未移植；
- 私有成员/状态走反射（官方用 access widener），字体路径每 glyph 读一次私有布尔；
- 只有单人 integrated server，无多人/soak/帧率基准。
