# p120 — ImmediatelyFast：描述符已能移植，但 batching 引擎需要整段重写（未通过）

日期：2026-10-22。目标是给 ImmediatelyFast 也做 mixin 重写。结果是**没通过**，但失败点被
推进了一层，并留下了可复现证据。这里不把“能替换类”说成“功能生效”。

## 尝试了什么

1. **修正 @Overwrite 描述符**：1.21.1 的 `VertexConsumerProvider.method_22992` 从
   `(Map<RenderLayer, BufferBuilder>, BufferAllocator)` 变成
   `(SequencedMap<RenderLayer, ByteBufferBuilder>, ByteBufferBuilder)`。
   写了一个 **vanilla 等价**的 overwrite（不构造 `BatchableBufferSource`），并加了一个
   `net.minecraft.McbridgeImmediate` 同包 helper 来调用 protected 的 `Immediate` 构造器。
2. 用规则替换 `MixinVertexConsumerProvider`（同时嵌入 helper），patched jar 审计：
   `config_errors=0`，替换类已写入。
3. 用 Fabric 1.21.1 + Fabric API + 该 patched jar 启动并 `--quickPlaySingleplayer` 进世界。

## 结果：第一层修好，第二层暴露

- 不再出现 `@Overwrite method method_22992 ... was not located`（描述符问题已解决）；
- 新失败点是 **`BatchableBufferSource.<clinit>`**：

  ```text
  java.lang.NoSuchMethodError: 'void net.minecraft.class_287.<init>(int)'
    at net.raphimc.immediatelyfast.feature.core.BatchableBufferSource.<clinit>
    at net.raphimc.immediatelyfast.feature.batching.BatchingBuffers.<clinit>
    at net.minecraft.class_332.handler$...$immediatelyfast$drawTexturedQuadIntoBuffer
  ```

  1.21.1 的 `BufferBuilder` 不再有 `(int)` 构造器，构建方式改成
  `ByteBufferBuilder` + `VertexFormat`；而 `BatchableBufferSource` / `BatchingBuffers`
  的静态字段和整个 HUD batching 代码都围绕旧模型写的。
- 客户端没能出现窗口，`joined=false`（`launch.log`）。

## 为什么停在这里

- 继续修需要重写 ImmediatelyFast 的 **universal batching / HUD batching 引擎**
  （`BatchableBufferSource`、`BatchingBuffers`、`BufferBuilder` 的 upload/clear 语义），
  不是规则引擎能“描述符级”补出来的；
- 用“删掉 @Overwrite / 永远返回 vanilla”糊过去，等于悄悄关掉它的核心功能，本仓库不这么干；
- 转换本身还剥掉了另外 8 个 mixin（`audit_mixins` 报 8 个 INERT），即使过了这一关，
  功能也只会是残的。把这些如实留在报告里，比伪装通过更有用。

## 证据

| 文件 | 内容 |
|---|---|
| `launch.log` | 完整启动日志：描述符问题消失，崩在 `BatchableBufferSource.<clinit>` |
| `result.json` | 脚本记录：`joined=false`、mod 列表、ImmediatelyFast 初始化行 |

实验性规则/源码**没有进 `rules/` 或 `java/src/compat/`**（放在本机 `work/tmp/p120-reference/`，
不入库），避免被当成“已验证能力”。

## 结论

- **EntityCulling 是目标 B 的通过案例**（`runs/p119-entityculling-mixin/`）；
- ImmediatelyFast 仍为 **❌ 未解决**；下一步需要真实的 BufferBuilder/ByteBufferBuilder
  引擎移植与性能/画面验证，属于独立的较大工程，不应在规则层假装完成。
