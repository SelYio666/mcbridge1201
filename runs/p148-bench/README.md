# p148 — HUD batching on/off 帧率对照（诚实结果：差异在噪声内）

日期：2026-10-22。给移植版加了 **opt-in** 采样：只有 JVM 参数 `-Dmcbridge.bench=true` 时，
`MixinMinecraftClientBench`（`MinecraftClient.method_1523`）与 `BatchingBuffers` 的周期日志才会
每 ~2 秒打印 `[mcbridge-port] fps=`；默认运行保持安静（p151 验证：0 条周期日志）。

## 方法

- 同一个移植 jar、Fabric API、单人 `ColdWorld`，各跑 40 秒稳态；
- on：`hud_batching=true`（p148-bench-on）；off：`hud_batching=false`（p148-bench-off）；
- 启动时 `JAVA_TOOL_OPTIONS=-Dmcbridge.bench=true`；
- 去掉启动阶段（0/低值）样本后取中位数。

## 结果（多次运行）

| 运行 | on 中位数 | off 中位数 | on 样本 | off 样本 |
|---|---|---|---|---|
| ① | ≈113 | ≈116 | 16 | 14 |
| ② | ≈112.5 | ≈111.5 | 20 | 20 |
| ③ | ≈111 | ≈107 | 19 | 18 |

三次里 on 有时低 3、有时高 1、有时高 4——**差异与运行间噪声同量级**。
结论：在这套静态 HUD 场景里，**没有可复现的帧率收益或损失**；不能宣称 ImmediatelyFast
的 batching 带来性能提升。真实收益需要固定 GPU、加载实体/物品压力、多轮采样后再评估。

## 诚实限制

- 只测 HUD 场景（无实体/大量物品负载）；
- 单机、无 GPU 固定频率、无置信区间；
- 采样器本身只做时间判断，但仍是侵入式观测，默认关闭（opt-in）。

## 证据

`runs/p148-bench-on/`、`runs/p148-bench-off/` 的 launch.log；默认安静运行见
`runs/p151-immediatelyfast-silent/`。
