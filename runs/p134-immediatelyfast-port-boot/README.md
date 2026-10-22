# p134 — ImmediatelyFast 1.21.1 batching 移植：启动进世界，universal batching 生效

日期：2026-10-22。当前状态：**batching 引擎移植成功、能启动并进世界，universal batching 在跑**；
但 ImmediatelyFast 的 HUD/物品**专用** fast-path（`BatchingBuffers` 的 FILL/TEXTURE/ITEM 消费者）
还没有被 1.21.1 的 DrawContext/InGameHud 调用路径喂到（per-batch 计数为 0），下一轮继续。

## 移植内容

| 类 | 作用 | 1.21.1 适配 |
|---|---|---|
| `BatchableBufferSource` | 每 RenderLayer 的 BufferBuilder 批处理与绘制 | `ByteBufferBuilder` + `BufferBuilder(allocator, DrawMode, VertexFormat)`；反射调用私有 `Immediate.method_60893`、读写 `field_52071/field_52156` |
| `BatchingBuffers` | HUD/物品批处理开关与消费者（保留 1.20.4 mixin API） | 内部用 `HudBatchingBufferSource`；带 per-batch 计数日志 |
| `HudBatchingBufferSource` | HUD 批处理消费者 | 继承移植后的 `BatchableBufferSource` |
| `SimpleImmediate` | 关闭 universal batching 时的普通 Immediate | 公开构造器 |
| `MixinVertexConsumerProvider` | `class_4597.method_22992` 工厂 | 新描述符 `(SequencedMap<RenderLayer, ByteBufferBuilder>, ByteBufferBuilder)`，默认返回 `BatchableBufferSource` |
| `MixinTextRenderer_Drawer` | 字体 getBuffer 去重 | `field_1556`（private，反射）替代被删的 `method_22893` |

规则：`rules/fabric-1.21.1/immediatelyfast-batching-port.json`（5 个类替换 + 2 条 Identifier 重定向）。

## 启动与批处理证据

- Fabric Loader 0.19.5 + Fabric API 0.102.0 + 移植后的 ImmediatelyFast，Java 21；
- `--quickPlaySingleplayer ColdWorld`，日志 `IFUser joined the game`；
- 日志（本次实际）：

  ```text
  [mcbridge-port] hud batching begin
  [mcbridge-port] batched-draws total=1646 hud=0 itemModel=0 itemOverlay=0
  [mcbridge-port] batched-draws total=2960 hud=0 itemModel=0 itemOverlay=0
  [mcbridge-port] batched-draws total=4956 hud=0 itemModel=0 itemOverlay=0
  [mcbridge-port] batched-draws total=7256 hud=0 itemModel=0 itemOverlay=0
  ```

  **解读**：`BatchableBufferSource.drawDirect` 在持续执行（universal batching 覆盖 DrawContext/
  实体的 Immediate），所以总数在涨；但 `hud/itemModel/itemOverlay` 为 0，说明 ImFast 的 HUD/物品
  专用批次当前没有被喂到。**不能**据此宣称“HUD batching 已生效”。
- 截图 `world.png`：世界内、HUD 心/物品栏正常（当前由 universal batch 路径渲染）。

## A/B（p137，需按上述解读）

`hud_batching=false` 时仍能进世界，但 `[mcbridge-port] hud batching begin` 与总计数日志都不再打印
（日志点在 `endHudBatching` 里）。这证明“日志/入口与开关绑定”，**尚未**证明 HUD 专用批次本身。

## 下一轮要做的

- 把 `MixinDrawContext` / `MixinInGameHud` 等 HUD 消费者按 1.21.1 的真实调用路径对齐，使
  `FILL_CONSUMER/TEXTURE_CONSUMER/ITEM_*` 真正收到 draw 调用（per-batch 计数 > 0），再重跑 A/B；
- 之后才把目标里的“HUD/物品批处理功能生效”标为完成。

## 诚实限制

未移植 Iris；未移植 per-lighting 物品变体；私有成员走反射；只有单人 integrated server。
