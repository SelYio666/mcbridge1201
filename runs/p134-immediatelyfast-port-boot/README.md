# p134 — ImmediatelyFast 1.21.1 batching 移植：启动、进世界、HUD + 物品批处理生效

日期：2026-10-22。目标 B 的核心结果：1.20.4 的 ImmediatelyFast batching 引擎移植到 1.21.1，
**启动、进单人世界，HUD 与物品模型的专用批处理都在跑**（可测 per-batch 计数 + HUD 开关对照）。

## 移植内容

| 类 | 作用 | 1.21.1 适配 |
|---|---|---|
| `BatchableBufferSource` | 每 RenderLayer 的 BufferBuilder 批处理与绘制 | `ByteBufferBuilder` + `BufferBuilder(allocator, DrawMode, VertexFormat)`；反射私有 `Immediate.method_60893`、`field_52071/field_52156`；**不再二次 close allocator** |
| `BatchingBuffers` | HUD/物品批处理开关与消费者 | 内部用 `HudBatchingBufferSource`；per-batch 计数日志 |
| `HudBatchingBufferSource` | HUD 批处理消费者 | 继承移植后的 `BatchableBufferSource` |
| `SimpleImmediate` | 关闭 universal batching 时的普通 Immediate | 公开构造器 |
| `BatchingRenderLayers` | 自定义 GUI textured/colored 层 | 1.21.1 RenderLayer 构造 + shader 引用 |
| `BlendFuncDepthFuncState` | 混合/深度状态快照 | `GlStateManager` 私有字段反射读取 |
| `MixinVertexConsumerProvider` | `class_4597.method_22992` 工厂 | 新描述符返回 `BatchableBufferSource` |
| `MixinTextRenderer_Drawer` | 字体 getBuffer 去重 | 私有 `field_1556` 反射替代 `method_22893` |
| `MixinDrawContext` | HUD fill/drawTexture + 物品 consumer 切换 | 1.21.1 方法签名；`method_51425` 切 ITEM_MODEL、`method_51432` 切 ITEM_OVERLAY |
| `MixinGameRendererHud` | 把 `InGameHud.render` 包进 `runBatched` | 用 `@Redirect` 替代 MixinExtras `WrapOperation` |

规则：`rules/fabric-1.21.1/immediatelyfast-batching-port.json`
（6 个类替换 + 2 个 mixin 配置补充 + 2 条 Identifier 重定向）。

## 启动与功能证据

- Fabric Loader 0.19.5 + Fabric API 0.102.0 + 移植后的 ImmediatelyFast，Java 21；
- `--quickPlaySingleplayer ColdWorld`，`IFUser joined the game`；
- 测试用最小 playerdata 在快捷栏放了一把钻石剑（DataVersion 3955），真实计数：

  ```text
  [mcbridge-port] hud batching begin
  [mcbridge-port] batched-draws total=8251  hud=2661 itemModel=631  itemOverlay=0
  [mcbridge-port] batched-draws total=9662  hud=3037 itemModel=725  itemOverlay=0
  [mcbridge-port] batched-draws total=13278 hud=3941 itemModel=951  itemOverlay=0
  [mcbridge-port] batched-draws total=17012 hud=4796 itemModel=1165 itemOverlay=0
  ```

- A/B（`runs/p137-immediatelyfast-hud-off/`）：`hud_batching=false` 时仍进世界，但**没有任何**
  `[mcbridge-port]` 标记（hud/item 计数都不产生）→ 批处理由该开关控制；
- 截图 `world.png`：世界内 F3/HUD；测试用 playerdata 没有 Pos，角色落在 (0,0,0)，画面较暗，
  但已进世界且 HUD 正常。

## 修过的真实崩溃

第一次带物品运行时 JVM 直接崩（`EXCEPTION_ACCESS_VIOLATION` in `MemoryUtil.memPutFloat`，
`hs_err_pid11748.log`）：`drawDirect` 在 vanilla `Immediate.draw` 之后又 `close()` 了 builder 的
`ByteBufferBuilder`，造成二次释放/复用。去掉这次 close 后稳定跑完（本页计数即修复后结果）。

## 诚实限制

- `itemOverlay=0`：这次只放了无数量/耐久的剑；count/durability overlay 路径未单独验证；
- Iris 兼容未移植；
- 私有成员/状态走反射（官方用 access widener）；
- 只有单人 integrated server，无多人/soak/帧率基准；测试 world 是合成 playerdata，不是正常生存流程。
