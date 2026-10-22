# p149 — item per-lighting 变体移植并验证

日期：2026-10-22。补上之前文档里写“未移植”的 item per-lighting 变体。

## 实现

- 新增 `LightingState`：快照 `RenderSystem.shaderLightDirections`（字段是 private，用缓存反射读），
  `saveAndApply/revert` 调 `RenderSystem.setShaderLights`；
- 新增 `BatchingBuffers.WrappedRenderLayer`：包装原 RenderLayer，并在 start/end 里额外
  apply/revert 光照状态（层名用唯一字符串，避免直接访问 protected `field_21363`）；
- `HudBatchingBufferSource.getBuffer` 恢复官方逻辑：
  - `renderingItem` 时按 `(layer, LightingState)` 缓存 `WrappedRenderLayer`，分包绘制；
  - `renderingItemDecorations` 时把 `class_1921.method_51785()` 换成 GUI 纹理层；
  - glint 层不包装（层名反射读取判断）；
- `MixinDrawContext` 在 `method_51425`（物品）与 `method_51432`（overlay）前后设置
  `setRenderingItem` / `setRenderingItemDecorations`；
- 嵌套类 `BatchingBuffers$WrappedRenderLayer` 加进规则的 `alsoEmbed`（否则 NoClassDefFoundError）。

## 验证

```text
[mcbridge-port] item lighting variants active
[mcbridge-port] batched-draws total=18885 hud=3741 itemModel=912 itemOverlay=912 fps=105
[mcbridge-port] batched-draws total=23376 hud=4604 itemModel=1128 itemOverlay=1128 fps=105
```

- 单人 `ColdWorld` + 快捷栏 64 石头，`IFUser joined the game`，无 crash；
- `item lighting variants active` 证明光照变体层真的创建；
- itemModel/itemOverlay 继续增长。

## 限制

- 静态场景里光照状态基本不变，所以只创建了少量变体；没有做多光照/多物品的压力对比；
- 变体层的名字是唯一的运行时字符串，不是原层名（仅用于内部 map/调试）；
- 未验证 shader pack 下的 per-lighting 组合。

## 证据

`launch.log`、`result.json`、`world.png`。
