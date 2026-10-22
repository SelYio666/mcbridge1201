# p157 — 实体压力交错多轮：universal batching 慢约 13%

日期：2026-10-22（23:07–23:12）。p153/p154 只是顺序各跑一次，这次改成**交错执行**
on → off → on → off，控制机器冷热漂移，再下结论。

## 方法

- 专用服务器 + 启动器客户端；每轮先 `kill @e[type=armor_stand]`，再 summon 80 个
  `{NoAI:1b,NoGravity:1b,Invulnerable:1b}` 盔甲架；
- `enableVsync:false`、`maxFps:260`、`-Dmcbridge.bench=true`；
- 每轮进世界后保持 35 秒，取客户端 `fps=` 样本（去启动噪声，取 ≥20 的稳态样本中位数）；
- 顺序：on(1) → off(1) → on(2) → off(2)；每轮都确认服务端 `joined the game`。

## 结果

| 轮次 | on 中位数 | off 中位数 | 样本数 |
|---|---|---|---|
| 第 1 轮 | **583.5** | **642.5** | 20 / 20 |
| 第 2 轮 | **517.0** | **629.0** | 20 / 21 |
| 总体中位数 | **550.25** | **635.75** | — |

**交错两轮方向一致：开启 universal batching 慢约 13%（550 vs 636）。**
和 p153/p154 的“慢 15–20%”一致；这次交替顺序，降低了“先跑谁谁吃亏”的解释力。

## 解读

- 移植版的额外开销（反射 `Immediate.draw`、allocator 管理、自定义层）在实体渲染场景
  压过了批处理省下的 draw call；
- 之前 HUD 场景（p148）差异在噪声内，说明这个实现的收益/损失高度依赖场景；
- 结论仍不宣称性能收益；本项目定位是兼容性。

## 限制

- 80 个盔甲架是合成负载，不代表真实整合包；
- 每条件 2 轮，没有锁 GPU 频率/温度，绝对帧率会漂移（但交错顺序已缓解）；
- 未测 shader pack 下的实体压力。

## 证据

`runs/p157-stress-on-1|off-1|on-2|off-2/`（client.log/server.log/result.json/world.png）
与 `results.json`。
