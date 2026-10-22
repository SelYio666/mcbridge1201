# p137 — ImmediatelyFast HUD batching A/B：关闭后计数消失

日期：2026-10-22。对照 p134：同一套移植 jar、同一世界/参数，只把
`config/immediatelyfast.json` 的 `hud_batching` 设为 `false`。

## 结果

| 项 | hud_batching=true（p134） | hud_batching=false（本次） |
|---|---|---|
| 进世界 | ✅ | ✅ `IFUserOff joined the game` |
| `[mcbridge-port] hud batching begin` | ✅ | ❌ 无 |
| `[mcbridge-port] batched-draws=...` | ✅ 545 → 2209 → 4329 | ❌ 无 |

关闭后 HUD 仍由 vanilla 路径渲染（截图可正常进世界），但移植代码的批处理入口没有被调用。
这证明 p134 的计数不是无条件打印，而是 HUD batching 真正启用时才走。

## 证据

- `launch.log`：无 `[mcbridge-port]` 标记；
- `result.json`：`joined: true`、`port_markers: 0`。

## 限制

- 只验证 HUD batching 开关；`debug_only_and_not_recommended_disable_universal_batching`
  与物品照明变体没有单独 A/B；
- 单次运行，无 soak/帧率基准。
