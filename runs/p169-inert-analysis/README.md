# p169 — 剩余 4 个 inert mixin 为什么不能直接重登记

日期：2026-10-23。p166–p168 救活了 ChatHud、MinecraftClient、BufferRenderer；剩下 4 个逐个查过，
结论是**不能只往 config 里加名字**，否则要么启动崩，要么“启动绿、用地图/上传时炸”。

## 1) `core/MixinBufferBuilder` — 目标字段已不存在

```text
javap class_287 | grep field_1555  -> 无输出（字段不存在）
```

该 mixin `@Shadow private ByteBuffer field_1555`，1.21.1 的 BufferBuilder 已改为
ByteBufferBuilder/MeshData 体系，没有这个字段；重登记会在 apply 时因 shadow 缺失失败。

## 2) `fast_text_lookup/MixinFontManager` — 注入方法已不存在

```text
javap class_378 | grep method_27541 -> 无输出（只有 method_27539 / method_45078）
```

mixin 明确 `@Inject(method="method_27541")`，1.21.1 索引里没有该方法；重登记会 critical injection failure。

## 3) `fast_buffer_upload/MixinVertexBuffer` — 目标在，但会改 GL 上传路径

> **2026-10-23 p178 已启用**：1.21.1 的 `method_43442` / `method_43443` / 新增
> `method_60829` 都已接上；80 盔甲架压力场景、off/off 与 on/on 对照，on 侧最高 76k 次
> `glBufferSubData`、无 GL/mixin 错误，off/on 截图差 0.0087%（低于 off/off 对照 0.214%）。
> 见 `runs/p178-vertex-upload/`。下面保留当时“未压测前保持 inert”的分析。

```text
RenderSystem.glBufferData(int, ByteBuffer, int) 存在
class_291.method_43442 / method_43443 存在
```

它可以 apply，但逻辑是把 `glBufferData` 换成 `GL15C.glBufferSubData` 以“快速上传”（受
`fast_buffer_upload` 配置控制）。p170 做了 on/off 静态截图 A/B（差 0.018%），但没有顶点上传压力/
多场景验证，因此**仍保持 inert**，等有专门的顶点上传压测再开。

## 4) `map_atlas_generation/MixinMapRenderer` — 依赖 1.20.4 纹理 API

> **2026-10-23 p175 已修复**：`MapAtlasTexture` 已按 1.21.1 的 Identifier 工厂/NativeImage/
> TextureManager 编译并 embed；`MixinMapRenderer` 按 `method_32601(class_9209, class_22)` 重写，
> `MixinMapRenderer_MapTexture` 也按 1.21.1（`method_60803` 代替已删除的 `method_1344`、去掉
> lenni `Objects.allocate`）重写。单人世界实际手持 filled_map 渲染通过，见 `runs/p175-map-atlas/`。
> 本节以下内容是 p169 当时的状态，保留作历史记录。

`MapAtlasTexture` 引用 `class_1043`/`class_1044` 等 1.20.4 纹理类（1.21.1 纹理 API 已变）。
mixin 的注入在“地图渲染”时才真正执行：启动阶段不会触发，所以重登记会**假绿**——启动过、
一用地图就炸。必须先把 `MapAtlasTexture` 移植到 1.21.1 的纹理接口，本轮不做。

p172 实际尝试过：`MapAtlasTexture` 端口写好了（Identifier 工厂/NativeImage/TextureManager 都在），
但 `MixinMapRenderer` 在 1.21.1 **无法 apply**：`method_32601` 的第一个参数从 `int` 变成
`class_9209`，注入描述符不匹配（InvalidInjectionException）。所以需要重写这个 mixin 的注入，
而不只是登记。

## 5) 追加：`MixinMapRenderer_MapTexture` 是半启用的（p171 已 strip）

审计只列出了 `MixinMapRenderer` inert，但 config 里 **`MixinMapRenderer_MapTexture` 是启用的**。
它构造时 `((IMapRenderer) field_2047).immediatelyFast$getAtlasMapping(id)`，而 `IMapRenderer` 的实现
来自 inert 的 `MixinMapRenderer` → 一旦渲染地图会 `ClassCastException`。

处理：用规则的 `mixinStrips` 显式移除 `MixinMapRenderer_MapTexture`（记录 reason），
地图回退 vanilla，直到 `MapAtlasTexture` 移植完成。证据：`runs/p171-map-strip/`。
**p175 已删除该 strip 并重新登记两个 map mixin，真实渲染通过**（`runs/p175-map-atlas/`）。

## 结论

- 已救活 3 个（p166–p168），inert 7 → 4；
- p175 救活 `MixinMapRenderer` + `MixinMapRenderer_MapTexture`，当前 inert **2**（`listed=37`）：
  `MixinBufferBuilder`、`MixinFontManager`；
- p178 在压力/对照证据下启用 `MixinVertexBuffer`（inert 3 → 2）；
- 剩余 2 个保持 inert，并在文档写明原因；不为了“审计数字好看”而假绿；
- 下一步优先级：`MixinBufferBuilder` 的 `field_1555`/`ByteBufferBuilder` 语义，以及
  `MixinFontManager` 的 1.21.1 字体管理入口（两者都需要实际移植，不是只加 config）。

## 证据

`bufferbuilder.log`、`fontmanager.log`、`vertexbuffer.log`、`maprenderer.log`（javap/grep 输出）。
