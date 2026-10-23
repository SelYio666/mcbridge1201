# v0.5.1 — ImmediatelyFast 端口补丁 + 服务器/mrpack 证据收口

v0.5.0 之后没有新功能大改，主要是把 ImmediatelyFast 端口的审计问题修掉、把剩余风险写清楚，
并补齐 Forge/NeoForge 带模组专用服务器与 mrpack 的证据。

## ImmediatelyFast 端口

- 重新登记并验证 3 个被转换时丢掉的 mixin：
  - `hud_batching.MixinChatHud`（inert 7 → 6）
  - `core.MixinMinecraftClient`（6 → 5）
  - `hud_batching.compat.MixinBufferRenderer`（5 → 4；随后地图 strip 后当前为 5）
- 发现并修掉一个**潜在崩溃**：`map_atlas_generation.MixinMapRenderer_MapTexture` 原本启用，
  会强转 `MapRenderer` 为 `IMapRenderer`，而提供实现的 `MixinMapRenderer` 是 inert →
  渲染地图时 `ClassCastException`。已用规则的 `mixinStrips` 显式移除并记录原因（p171）。
- 地图 atlas 尝试恢复失败并回滚：`MapAtlasTexture` 已移植（Identifier 工厂/NativeImage/
  TextureManager），但 `MixinMapRenderer` 在 1.21.1 的 `method_32601` 参数从 `int` 变为
  `class_9209`，旧注入无法 apply（p172）；回滚后 p173 启动正常，地图 atlas 暂时关闭。
- 剩余 inert（BufferBuilder/VertexBuffer/FontManager/MapRenderer）的阻塞原因已逐条记录
  （p169），不为了审计数字硬登记。

## 启动器 / 证据

- Forge 1.20.1 与 NeoForge 21.1.264 **带 Farmer's Delight** 的专用服务器 + 同模组客户端加入
  （p163/p164）；之前已有原版服务端加入（p159/p161）。
- 真实 mrpack（含 files 下载 + SHA-1 校验 + overrides）导入通过（p160）。
- 性能：HUD 场景 on/off 差异在噪声内；80 盔甲架实体压力交错两轮显示开启 universal batching
  慢约 13%（p157）；`MixinVertexBuffer` 静态截图 A/B 差 0.018%（p170）但证据不足，未启用。

## 资产

- `mcbridge-launcher-0.5.1.zip`（内置 CPython，约 11.96 MB）；
- SHA-256：`3e1345e61d73eb895e4ec644c83b0fadc6dc508135c74a2bfda7ccb86a4e989b`；
- `tools/test_portable.py`：deps/verify/server/guide 全过。

## 门禁

- Java 25/25；`test_review_fixes` 73/73；`check_hashes` 944/944；`verify_evidence` passed；
- push 触发的 CI `build` success（见仓库 Actions）。
