# p137 — ImmediatelyFast HUD batching A/B：关闭后计数消失

日期：2026-10-22。对照 p134：同一套移植 jar、同一世界/参数，只把
`config/immediatelyfast.json` 的 `hud_batching` 设为 `false`。

## 结果

| 项 | hud_batching=true（p134） | hud_batching=false（本次） |
|---|---|---|
| 进世界 | ✅ `IFUser joined the game` | ✅ `IFUserOff joined the game` |
| `[mcbridge-port] hud batching begin` | ✅ | ❌ 无 |
| `[mcbridge-port] batched-draws ... hud=` | ✅ hud=1501 → 4052 | ❌ 无任何标记 |

关闭后 HUD 仍由 vanilla 路径渲染（能正常进世界/显示），但移植代码的 HUD 批处理入口没有被调用。
这证明 p134 的 `hud=` 计数是 HUD batching 真正启用时才产生的。

## 证据

- `launch.log`：无 `[mcbridge-port]` 标记；
- `result.json`：`joined: true`、`port_markers: 0`。

## 限制

- 只验证 HUD batching 开关；物品 per-lighting 变体未移植（p134 中 itemModel/itemOverlay=0）；
- 单次运行，无 soak/帧率基准。
