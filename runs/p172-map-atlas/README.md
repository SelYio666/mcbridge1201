# p172 — 尝试恢复地图 atlas：MapAtlasTexture 移植 + MixinMapRenderer 重登记（失败，已回滚）

日期：2026-10-23。p171 把半启用的 `MixinMapRenderer_MapTexture` strip 掉后，地图 atlas 整体关闭。
本轮尝试真正修好它，结果是**失败**，但失败点很有价值。

## 做了什么

1. 新增 `MapAtlasTexture` 的 1.21.1 端口（`java/src/compat/.../feature/map_atlas_generation/`）：
   - `Identifier(String,String)` → `class_2960.method_60655(...)`；
   - `NativeImage(4096,4096,true)` 仍在；
   - TextureManager 的 `method_4616`（注册）/`method_4615`（注销）仍在；
   - 编译通过（`javac exit: 0`）。
2. 规则里 embed 这个类，并重新登记 `map_atlas_generation.MixinMapRenderer`。
3. 造了一个带 `minecraft:filled_map`（map component id=1）的 playerdata，选中 slot 1，尝试触发地图渲染。

## 失败点

启动直接失败（`runs/p172-map-atlas/launch.log`）：

```text
InvalidInjectionException: Invalid descriptor on ...MixinMapRenderer
@Inject::createMapAtlasTexture(ILnet/minecraft/class_22;...)
Expected (Lnet/minecraft/class_9209;Lnet/minecraft/class_22;...)V
but found (ILnet/minecraft/class_22;...)V
```

即 1.21.1 的 `class_330.method_32601` 第一个参数从 `int` 变成了 `class_9209`（MapId），
转换件里的注入方法签名对不上，Mixin 在 apply 阶段就拒绝。

## 回滚

- 撤回 `map_atlas_generation.MixinMapRenderer` 的 config 登记；
- 从 `alsoEmbed` 移除 `MapAtlasTexture`；
- 恢复 p171 的 `mixinStrips`（继续 strip `MixinMapRenderer_MapTexture`）；
- 补丁后 jar sha256 回到 `3043c978...`，审计 `listed=34 inert=5`；
- p173 启动进单人世界：`{"joined": true, "crash": null}`。

## 结论 / 下一步

- `MapAtlasTexture` 端口本身没问题，但**只移植它不够**：`MixinMapRenderer` 需要按 1.21.1 的
  `class_9209` 参数重写注入方法（可能还要适配 `MapTexture` 的内部逻辑）；
- 在完成之前，地图 atlas 保持关闭（MapTexture 被 strip），不会出现地图渲染 ClassCastException；
- `MapAtlasTexture.java` 作为后续工作的基础保留在 compat 源码里（未 embed）。

## 证据

`launch.log`、`result.json`；回滚后的 p173 见 `runs/p173-restore/`。
