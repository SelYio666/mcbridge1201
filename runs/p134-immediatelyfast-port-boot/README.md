# p134 — ImmediatelyFast 1.21.1 batching 移植：启动、进世界、批处理生效

日期：2026-10-22。目标 B 的核心结果：1.20.4 的 ImmediatelyFast batching 引擎移植到 1.21.1，
**真的启动、进单人世界，并且批处理绘制路径在跑**。

## 移植内容

| 类 | 作用 | 1.21.1 适配 |
|---|---|---|
| `BatchableBufferSource` | 每 RenderLayer 的 BufferBuilder 批处理与绘制 | `ByteBufferBuilder` + `BufferBuilder(allocator, DrawMode, VertexFormat)`；反射调用私有 `Immediate.method_60893`、读写 `field_52071/field_52156` |
| `BatchingBuffers` | HUD/物品批处理开关与消费者 | 保留 1.20.4 mixin 需要的字段/无参 begin/end；内部用 1.21.1 的 `HudBatchingBufferSource` |
| `HudBatchingBufferSource` | HUD 批处理消费者 | 继承移植后的 `BatchableBufferSource` |
| `SimpleImmediate` | 关闭 universal batching 时的普通 Immediate | 公开构造器，绕开 protected |
| `MixinVertexConsumerProvider` | `class_4597.method_22992` 工厂 | 新描述符 `(SequencedMap<RenderLayer, ByteBufferBuilder>, ByteBufferBuilder)`，默认返回 `BatchableBufferSource` |
| `MixinTextRenderer_Drawer` | 字体 getBuffer 去重 | 用 `field_1556`（private，反射）代替被删的 `method_22893`；字体查找 `method_27526` 也反射 |

规则：`rules/fabric-1.21.1/immediatelyfast-batching-port.json`（5 个类替换 + 2 条 Identifier
构造器重定向）。补丁命令：

```text
mcbridge1201 patch --in ImmediatelyFast-Fabric-1.5.5+1.20.4+1.21.1.jar \
  --out ImmediatelyFast-ported.jar \
  --rules rules/fabric-1.21.1/immediatelyfast-batching-port.json \
  --bridge-dir work/tmp/if-port-classes
```

## 启动与功能证据

- 环境：Fabric Loader 0.19.5 + Fabric API 0.102.0 + 移植后的 ImmediatelyFast，Java 21；
- `--quickPlaySingleplayer ColdWorld`，日志 `IFUser joined the game`；
- 移植代码插入的计数日志：

  ```text
  [mcbridge-port] hud batching begin
  [mcbridge-port] batched-draws=545
  [mcbridge-port] batched-draws=2209
  [mcbridge-port] batched-draws=4329
  ```

  说明 `BatchableBufferSource.drawDirect` 在持续执行，不是“只启动不生效”。

- A/B 对照（`runs/p137-immediatelyfast-hud-off/`）：把 `hud_batching` 设为 `false` 后仍能进世界，
  但**没有任何** `[mcbridge-port]` 日志 → 计数与 HUD batching 开关绑定；
- 截图：`world.png`（世界内、HUD 心/物品栏正常）。

## 诚实限制

- 未移植 Iris 兼容；
- 未移植物品的 per-lighting variant（`LightingState`），HUD/物品仍批处理但照明分组被简化；
- 私有成员用反射（官方用 access widener），字体路径每个 glyph 读一次私有布尔，可能有性能损耗；
- 只有单人 integrated server 验证，没有多人/soak；未做帧率基准。

## 证据文件

`launch.log`、`result.json`、`world.png`；A/B：`runs/p137-immediatelyfast-hud-off/`。
