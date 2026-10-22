# p147 — universal batching 关闭时的 SimpleImmediate 回退路径

日期：2026-10-22。补一个之前没单独验证的分支：配置
`debug_only_and_not_recommended_disable_universal_batching=true` 时，
`MixinVertexConsumerProvider` 应返回 `SimpleImmediate` 而不是 `BatchableBufferSource`，
HUD 批处理仍应工作、游戏不崩。

## 条件

- 同一个移植 jar + Fabric API；
- `config/immediatelyfast.json` 里 `debug_only_and_not_recommended_disable_universal_batching=true`；
- 单人 quickPlay 进 `ColdWorld`（无合成 playerdata）。

## 结果

```text
[mcbridge-port] batched-draws total=2881 hud=2881 itemModel=0 itemOverlay=0
[mcbridge-port] batched-draws total=3761 hud=3761 itemModel=0 itemOverlay=0
[mcbridge-port] batched-draws total=4797 hud=4616 itemModel=0 itemOverlay=0
```

- `IFNoUni joined the game`，无 crash report、无 JVM fatal error；
- `total == hud`：universal batching 关闭后没有实体/通用 Immediate 的批处理，只剩 HUD 专用批次，
  符合预期；
- itemModel/itemOverlay=0 属预期（没有物品）。

## 证据

`launch.log`、`result.json`、`world.png`；配置测试后已恢复为 `false`。
