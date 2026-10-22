# p148 — HUD batching on/off 帧率对照（诚实结果：没有收益）

日期：2026-10-22。给移植版加了一个只做采样的 `MixinMinecraftClientBench`（每约 2 秒在
`MinecraftClient.method_1523` 打一行 `[mcbridge-port] fps=`），然后在同一世界、同样 40 秒
稳定运行下对比 `hud_batching=true/false`。

## 方法

- 同一个移植 jar、Fabric API、单人 `ColdWorld` 复制世界；
- on：`hud_batching=true`（p148-bench-on）；off：`hud_batching=false`（p148-bench-off）；
- 每次进世界后保持 40 秒，取日志里的 `fps=` 采样；
- 去掉启动阶段（0/低值）样本后取中位数。

## 结果

| 配置 | 稳态样本 | 中位数 | 范围 |
|---|---|---|---|
| hud_batching=true | 16 | **≈113** | 106–119 |
| hud_batching=false | 14 | **≈116** | 110–119 |

原始样本（on）：`108,112,114,111,106,113,111,118,110,118,117,118,119,117,118,117`
原始样本（off）：`116,115,116,110,112,114,116,117,118,117,118,119,117,119`

**结论：在这套静态 HUD 场景里，开 batching 反而低约 2–3%，没有可测的正收益。**
这可能是自定义 RenderLayer/反射调用的开销、场景太简单、以及一次运行噪声共同造成的；
不能据此宣称 ImmediatelyFast 的性能收益，本鱼也不会把这条写成“更快”。

## 诚实限制

- 只测 HUD 场景（没有物品/实体负载），不是典型的渲染压力场景；
- 单次运行、没有 GPU 固定频率、没有多轮取置信区间；
- 采样器本身在 `MinecraftClient.method_1523` 里只做时间判断，开销可忽略，但仍是侵入式观测。

## 证据

`runs/p148-bench-on/`、`runs/p148-bench-off/` 的 launch.log。
