# p121 — EntityCulling 开关 A/B 对照

日期：2026-10-22。目的：给 p119 的“功能生效”补一个对照实验——同一版本、同一世界文件、
同一 Java/模组，只切换 EntityCulling 自己的 `skipEntityCulling` / `skipBlockEntityCulling` 配置，
比较 F3 里的 culling 计数。

## 方法

- 每轮启动前都从 `work/instances/fabric-1.21.1-server/world` **重新拷贝**一份世界，避免上一轮
  写回的玩家位置影响下一轮；
- 配置直接改 `config/entityculling.json`：
  - `culling-on`：`skipEntityCulling=false`、`skipBlockEntityCulling=false`
  - `culling-off`：两条都 `true`
- Fabric Loader 0.19.5 + Fabric API 0.102.0 + 移植后的 EntityCulling（p119 的规则产物），Java 21；
- `--quickPlaySingleplayer ColdWorld` 进世界，等待 6 秒后脚本按 F3 截图。

## 结果

| 轮次 | 配置 | 进世界 | F3 里的 EntityCulling 行 |
|---|---|---|---|
| culling-on | 跳过关闭（功能开） | ✅ | `[Culling] Rendered Entities: 5 Skipped: 1`；`Rendered Block Entities: 1 Skipped: 0` |
| culling-off | 跳过开启（功能关） | ✅ | 没有任何 `[Culling]` 行（只有 Fabric 行） |

两轮都 `joined=true`，日志里没有 mixin 错误。

## 结论与限制

- 开关切换会让 EntityCulling 的调试计数出现/消失，且“开”时确实记录到 **Skipped: 1**，
  与 p119 独立复现一致；这是功能路径真正执行的证据，不是“能启动”。
- **不是像素级同场景对照**：两轮出生点不同（`11.5/68/79.5` vs `24.5/69/87.5`），
  因为这个世界没有钉死世界出生点，客户端每次加载会有偏移。因此这不构成“同场景跳过数差值”
  的严格实验，只能说开关行为与计数存在性成立。
- 只观察了短时间画面，没有 soak、没有性能数据。

## 证据

- `culling-on.png` / `culling-off.png`：两轮 F3 截图；
- `culling-on.log` / `culling-off.log`：各自客户端日志（均 join 成功）；
- `result.json`：脚本输出（含配置值与 joined 状态）。
