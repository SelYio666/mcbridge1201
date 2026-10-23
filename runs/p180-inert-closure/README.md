# p180 — ImmediatelyFast 端口收尾：剩余 2 个 inert 是上游 1.21.1 已删除的遗留类

日期：2026-10-23。p178 之后端口只剩 `MixinBufferBuilder` / `MixinFontManager` 两个 inert。
本轮不硬登记它们，而是拿**官方 1.21.1 build** 做对照，确认它们不是“待移植功能”。

## 对照

| | 官方 ImmediatelyFast 1.21.1 | 本仓库端口 jar |
|---|---|---|
| jar | `work/tmp/if-native-1.21.1.jar`，342,235 bytes，sha256 `9c391f08…` | `ImmediatelyFast-ported.jar`，sha256 `fdde23e1…` |
| `audit_mixins --allow-inert` | `listed=37 inert=0 problems=0` | `listed=37 inert=2 problems=0` |
| `core/MixinBufferBuilder.class` | **不存在** | 存在但 inert（1.20.4 遗留） |
| `fast_text_lookup/MixinFontManager.class` | **不存在** | 存在但 inert（1.20.4 遗留） |
| `fast_text_lookup/MixinTextRenderer_Drawer` | 启用 | 启用（我们的端口） |
| `fast_buffer_upload/MixinVertexBuffer` | 启用 | 启用（p178） |
| map atlas 两个 mixin | 启用 | 启用（p175） |

官方 1.21.1 的常见 mixin config 里没有 `core.MixinBufferBuilder`，也没有
`fast_text_lookup.MixinFontManager`；jar 里同样没有这两个 class。也就是说：

- `MixinBufferBuilder` 依赖 `class_287.field_1555`（1.20.4 的 ByteBuffer 字段）；1.21.1 的
  BufferBuilder 改为 ByteBufferBuilder/MeshData，字段不存在，上游直接删除了这个 mixin；
- `MixinFontManager` 依赖 `field_24256`（字体 override map）、`method_27541`、`method_27542`；
  1.21.1 的 `class_378` 没有这些成员（只剩 `field_2259`、`method_27539`、`method_45078`），
  上游也删除了这个 mixin；
- 端口 jar 基于 1.20.4 多版本 jar，因此这两个 class 仍在包里；它们没有 config 条目、没有
  `IBufferBuilder` 的使用方，运行时不会生效。**保持 inert 是最诚实的处理**（不删 class 冒充
  “审计 0”，也不往 config 里加名字制造假启用）。

## 端口状态

- 官方 1.21.1 的 `fast_buffer_upload.MixinVertexBuffer`、`map_atlas_generation.*`、
  `fast_text_lookup.MixinTextRenderer_Drawer` 等本轮涉及的路径都已在端口里启用并有证据
  （p175/p177/p178）；
- 端口的 HUD batching 使用 1.20.4 架构（`MixinInGameHud`/`MixinDrawContext` 等）而不是官方
  1.21.1 的 `MixinLayeredDrawer`/`MixinItemRenderer`/`MixinRenderSystem`，这是已单独验证的
  移植选择（p134–p150），不在本文件重新声称“与官方逐 mixin 相同”；
- 审计剩余 `inert=2` 是**死代码**，不是待办。以后若有人想“清零”，应先确认这两个 1.20.4
  类是否还需要随包分发，而不是直接登记。

## 回归

`tools/test_review_fixes.py` 新增一条规则级检查：主规则不得把
`MixinBufferBuilder` / `MixinFontManager` 加进 config 或 replacement（防止未来误登记死 mixin）。

## 证据

`audit-native.log`、`audit-port.log`、`native-entries.txt`、`native-config.txt`。
