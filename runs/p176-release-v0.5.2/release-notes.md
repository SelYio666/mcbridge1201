# v0.5.2 — ImmediatelyFast 地图 atlas 恢复（真实渲染）

这版把 v0.5.1 里显式关闭的地图 atlas 功能真正恢复，并用单人世界实际渲染证明，而不是只证明
“能启动”。其余部分与 v0.5.1 相同。

## 地图 atlas

- `MixinMapRenderer` 按 1.21.1 的 `method_32601(class_9209, class_22)` 重写，用
  `mapId.comp_2315()` 取 map id；`method_1771`（clear）保持。
- `MixinMapRenderer_MapTexture` 按 1.21.1 重写：
  - `class_4588.method_1344()` 已删除，`method_1777` 的 slice 结束改为 `method_60803(I)`；
  - 不再依赖 lenni Reflect 的 `Objects.allocate`，改用懒创建的 1×1
    `NativeImageBackedTexture`（从不注册/上传/读取/关闭）；
  - 构造函数 id 在 `super()` 之后注入捕获（1.21.1 的 inner ctor 在 super 前写 outer 字段，
    Mixin 的 `HEAD` 会被判为 before-super，实例 handler 不合法）；
  - 新增 `[mcbridge-port] map-atlas ...` 证据标记。
- `MapAtlasTexture` 使用 1.21.1 的 Identifier 工厂、NativeImage 和 TextureManager
  register/unregister，以 `alsoEmbed` 嵌入补丁 jar。
- 规则删除 p171 的 `mixinStrips`，用 `mixinConfigAdditions` 重新登记两个 mixin；编译期用
  `tools/widen_stub.py` 把包可见的 `class_330$class_331` 在**仅编译 stub** 里变 public
  （运行时由 mod 自带 access widener 负责）。

## 证据

`runs/p175-map-atlas/`：

- 单人 `ColdWorldMap`，玩家快捷栏 slot 0 为 `filled_map`（`minecraft:map_id=1`）；
- 手持地图真实渲染（`world.png`，128×128 棋盘 + 黄色对角线）；
- 日志：

```text
[mcbridge-port] map-atlas create id=0
[mcbridge-port] map-atlas assign map=1 packed=0
[mcbridge-port] map-atlas texture map=1 packed=0 atlas=0
[mcbridge-port] map-atlas bind map=map/1 texture=immediatelyfast:map_atlas/0
```

- 无 ClassCastException、无 Mixin apply 失败、无 crash report；第二次重复运行结果一致；
- 审计：`listed=36 inert=3`，两个 map mixin 不再 inert；剩余
  `MixinBufferBuilder` / `MixinVertexBuffer` / `MixinFontManager`（p169 已记录原因）。

## 未验证

- 只验证单人第一人称手持地图；物品展示框、多地图、地图动态更新、atlas 满 1024 张未测；
- 地图内容是固定图案，只证明渲染/纹理路径，不证明完整地图玩法；
- 没有性能声明；剩余 3 个 inert 与地图无关。

## 资产 / 门禁

- `mcbridge-launcher-0.5.2.zip`，11,960,114 bytes，SHA-256
  `1bfbafad716b70b07fbeddd2d7ecb69c2e69b0954255e889733a23b996e1d517`；
- `tools/test_portable.py`：deps/verify/status/guide 全过；
- Java 25/25；`test_review_fixes` 79/79；`verify_evidence` passed；push 触发 CI。
