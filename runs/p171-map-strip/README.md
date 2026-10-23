# p171 — 摘掉半启用的 MixinMapRenderer_MapTexture（避免地图渲染 ClassCastException）

> **已被 p175 取代**：2026-10-23 已在 `runs/p175-map-atlas/` 恢复两个 map mixin 并完成真实
> 地图渲染；本文件保留为当时的止血记录。

日期：2026-10-23。查 p165 剩余 inert 时发现一个**潜在运行时崩溃**，这轮先止血。

## 问题

- `immediatelyfast-common.mixins.json` 里 **`map_atlas_generation.MixinMapRenderer_MapTexture` 是启用状态**；
- 它构造时执行 `((IMapRenderer) this.field_2047).immediatelyFast$getAtlasMapping(id)`；
- 但提供 `IMapRenderer` 实现的 `map_atlas_generation.MixinMapRenderer` 是 **inert**（未登记）；
- 因此一旦渲染地图，`class_330` 没有实现 `IMapRenderer`，强转会抛 `ClassCastException`。

启动阶段不碰地图，所以之前的启动验证发现不了；这是“启动绿、用地图炸”的典型。

## 处理

- 规则新增 `mixinStrips`（工具已有能力，显式记录降级）：

```json
{
  "id": "immediatelyfast/strip-map-atlas-texture",
  "config": "immediatelyfast-common.mixins.json",
  "classes": ["map_atlas_generation.MixinMapRenderer_MapTexture"],
  "reason": "...casts MapRenderer to IMapRenderer while MixinMapRenderer is inert..."
}
```

- 补丁后 config 里 `MapTexture` 已不存在（`maptexture present: False`）；
- 审计：`listed=34 inert=5`，`MixinMapRenderer_MapTexture` 现在明确是 inert，不再半启用；
- p171 启动进单人世界：`{"joined": true, "crash": null}`。

## 结果与限制

- **地图渲染回退 vanilla**：地图图集功能整体关闭，直到 `MapAtlasTexture` 移植到 1.21.1 纹理 API
  并把 `MixinMapRenderer` 重新登记；
- 没有实际渲染地图验证（目前只保证不再半启用、启动不崩）；
- 这是显式降级（`mixinStrips` 有 reason），不是偷偷删 mixin。

## 证据

`launch.log`、`result.json`、`world.png`、`audit.log`；规则见
`rules/fabric-1.21.1/immediatelyfast-batching-port.json` 的 `mixinStrips`。
