# p153/p154 — 实体压力下 universal batching on/off（负结果）

日期：2026-10-22。HUD 静态场景的 on/off 差异落在噪声里（p148），于是换**实体负载**再测：
专用服务器 + 80 个盔甲架，关 vsync、maxFps=260，用 `-Dmcbridge.bench=true` 采样。

## 场景

- Fabric 1.21.1 专用服务器 + 启动器客户端（Fabric API + 移植后的 ImmediatelyFast）；
- 服务端控制台先 `kill @e[type=armor_stand]`，再在玩家周围 summon 80 个
  `{NoAI:1b,NoGravity:1b,Invulnerable:1b}` 盔甲架；
- `enableVsync:false`、`maxFps:260`；
- on：默认（实体走 `BatchableBufferSource`）；off：`debug_only_and_not_recommended_disable_universal_batching=true`
  （实体走 `SimpleImmediate`，HUD batching 仍开）。

## 结果（两种顺序，各一次）

| 顺序 | on 中位数 | off 中位数 | 样本数 on/off |
|---|---|---|---|
| A：先 on 后 off（p153） | **536** | **649.5** | 21 / 20 |
| B：先 off 后 on（p154） | **557** | **669.5** | 19 / 20 |

两种顺序方向一致：**开启 universal batching 反而慢约 15–20%**。范围也重叠不多
（on 约 330–680，off 约 400–780）。

## 解读

- 这套移植版在实体渲染上的额外开销（反射调用 `Immediate.draw`、allocator 管理、自定义层）
  超过了批处理省下的 draw call；
- 之前 HUD 场景（p148）差异在噪声内，说明“有没有收益”高度依赖场景与实现开销；
- 本项目的目标是**兼容性**，不是性能；文档不宣称 ImFast 移植带来提速，反而记录这里的负结果。

## 限制

- 每种顺序只跑一次，没有 GPU 固定频率/多轮置信区间；
- 80 个盔甲架是合成负载，不代表真实整合包；
- 客户端还带 Fabric API 等公共开销；未测 shader pack 下的实体压力。

## 证据

`runs/p153-stress-on|off/`、`runs/p154-stress-on|off/` 的 client.log/server.log/result.json/world.png。
