# p133 — ImmediatelyFast 1.21.1 batching 移植：可行性拆解

日期：2026-10-22。目标 B 的剩余项：让 ImmediatelyFast 的 batching 真正工作（不是只启动）。
本文件记录**为什么规则层修不了**、**需要重写哪些类**、以及**可执行的移植方案**。
状态：方案已定，代码未开始（目标 `goal-e805c526…` 跟踪）。

## 已知失败（p120）

```text
java.lang.NoSuchMethodError: 'void net.minecraft.class_287.<init>(int)'
  at net.raphimc.immediatelyfast.feature.core.BatchableBufferSource.<clinit>
  at net.raphimc.immediatelyfast.feature.batching.BatchingBuffers.<clinit>
```

`class_287` 是 `BufferBuilder`。1.20.4 的 `BufferBuilder(int)` 自己分配内存，`begin(mode, format)`
再设定格式；1.21.1 改成**外部 allocator + 构造时给 mode/format**，`build()` 产出 `MeshData`。
所以不是改一个描述符能解决的。

## 参考实现（native 1.21.1）

从 Modrinth 取了官方 `ImmediatelyFast-Fabric-1.6.15+1.21.1.jar`（SHA-1 `5067bdff…`，
仅作行为参考，不入库，放 `work/tmp/if-native-1.21.1.jar`）。`javap -p -c` 得到 1.21.1 的实际形状：

- `FALLBACK_BUFFER`：`class_9799`（`ByteBufferBuilder`），不再是 `class_287`；
- `pendingBuffers`：`Map<class_1921 (RenderLayer), ReferenceSet<class_287 (BufferBuilder)>>`；
- 构造器：`(class_9799, SequencedMap<class_1921, class_9799>)`，委托给
  `class_4597$class_4598.<init>(ByteBufferBuilder, SequencedMap)`；
- `getBuffer(layer)` 的关键调用：

  ```text
  new class_287(getNextBufferAllocator(),
                layer.method_23033(),   // DrawMode
                layer.method_23031())   // VertexFormat
  ```

- 绘制/关闭：`method_37104` / `method_22993` / `method_22994` / `close`，与 `Immediate` 一致。

## 工作包（WP）

| WP | 内容 | 预估 |
|---|---|---|
| WP1 | 移植 `BatchableBufferSource`：allocator 池、per-layer BufferBuilder 集合、build/draw | ~250 行 |
| WP2 | 移植 `BatchingBuffers` / `HudBatchingBufferSource`：静态状态、begin/end HUD batching | ~150 行 |
| WP3 | 适配 HUD 消费者 mixin（`MixinDrawContext` 等）到新 API | ~50–100 行 |
| WP4 | 规则：替换/内嵌新类 + `mixinConfigAdditions`，保持配置可审计 | 规则 JSON |
| WP5 | 证据：启动进世界、HUD 文本在 batching 开启时仍正确、日志计数、回归测试 | runs/ + tests |

## 验收标准（反“假通过”）

- 启动进世界（不是只到主菜单）；
- 打开 HUD batching 时，HUD 文本/图标渲染正确（截图对照）；
- 我们的移植代码里**有可见计数/日志**（例如成功构建并 draw 的 buffer 数），证明 batching 路径
  被执行，而不是回退到 vanilla；
- `@Overwrite`/mixin 不得删除或空实现来绕过；不能把“能启动”当“功能生效”。

## 风险

- 上游代码许可：仅以 native jar 的**行为**为参考，重写实现，不整段复制源码；
- Iris/Sodium 兼容不在本轮；
- 1.21.1 的 `RenderLayer` draw 需要 `MeshData`，与 1.20.4 的 immediate 语义不同，调试成本高。

## 下一步

WP1：写 `BatchableBufferSource` 的 1.21.1 版本并编译；启动到第一个新错误，逐个 WP 推进。

## WP1 进度（2026-10-22）

- 源码：`java/src/compat/java/net/raphimc/immediatelyfast/feature/core/BatchableBufferSource.java`；
- 编译脚本：`tools/build_immediatelyfast_port.py`（intermediary 1.21.1 jar + fastutil）；
- 结果：`javac exit: 0`（见 `wp1-compile.txt`）；
- 与官方的差异（如实）：
  - 无 Iris 兼容（Iris 本来就未测试）；
  - 无 `BufferAllocatorPool`：每个 buffer 用独立 `ByteBufferBuilder`，draw 后关闭（batching 行为不变，只是少了分配复用）；
  - 层排序只保留“半透明最后”，未实现马/狼/村民纹理的特殊顺序（只影响实体 z-fighting 顺序）；
  - `class_4598.method_60893` 与 `class_287.field_52071` 在 1.21.1 是 private，改用反射访问（官方用 access widener）。
- 还没做的：`BatchingBuffers` / `HudBatchingBufferSource`（WP2）、HUD mixin（WP3）、规则与启动验证（WP4/WP5）。
