# 扩模结果：6 个新模组（2026-10-19）

这一步回答“三个样本的成功能不能推广”。结论：**不能**。6 个原始 1.20.1 模组都完成了
CenturyBridge 转换和现有通用规则 patch，但 5 个有明确兼容性阻断，1 个只到启动范围。

| 模组 | 客户端 | 服务端/功能 | 结论 |
|---|---|---|---|
| AppleSkin 2.5.2 | 初始化已修；HUD 渲染遇 `FoodHelper` tombstone | 未测 | 部分修复 |
| Mod Menu 7.2.2 | 主菜单崩溃：私有 `TitleScreen.field_32271` | 未打开列表 | 不兼容 |
| Clumps 12.0.0.4 | 主菜单 120 tick | 3+7 经验球不合并（原版 1.21.1 会合并成 10） | 核心功能丢失 |
| FallingTree 4.3.4 | 初始化已修 | 旧 send 已重定向；入服未复测 | 部分修复 |
| FerriteCore 6.0.1 | 主菜单 120 tick | 启动/200 tick/正常停服；移除 2 个 mixin | 仅启动、降级 |
| ShulkerBoxTooltip 4.0.4 | 主菜单 | provider 读取旧 `ItemStack.method_7941` tombstone | 预览失败 |

## 网络桥进展（2026-10-19 补）

已新增 `rules/fabric-1.21.1/fabric-legacy-networking.json`、`identifier-single-arg.json`，以及
`FabricLegacyNetworking` / `IdentifierBridge` 两个桥：

- 旧 `ClientPlayNetworking.registerGlobalReceiver(Identifier, PlayChannelHandler)` → 注册原始
  payload 并回调旧 handler；被删除的 `PlayChannelHandler` 由嵌入的 shim 提供（只嵌嵌套类，不覆盖
  Fabric API 的 `ClientPlayNetworking`）；
- 旧 `new CustomPayloadC2SPacket(Identifier, PacketByteBuf)` → 用新 `class_2658(payload)` 构造；
- 旧 `ServerPlayNetworking.send(player, id, buf)` → 包成 S2C 原始 payload；
- `new Identifier(String)` → 拆 `namespace:path` 调 `Identifier.of`。

实测：AppleSkin 初始化与 `SyncHandler.makeSyncPacket` 不再崩，FallingTree 客户端可启动；AppleSkin
HUD 渲染仍撞上 `FoodHelper` 的 CenturyBridge tombstone（旧食物 API），FallingTree 入服路径未复测。
证据 `runs/p89-legacy-networking/`。

## 需要新增的适配（按类型）

1. **Fabric 网络桥（AppleSkin / FallingTree）**：旧的 `ClientPlayNetworking.registerGlobalReceiver(Identifier, PlayChannelHandler)` 和
   `ServerPlayNetworking.send(player, Identifier, PacketByteBuf)` 在 1.21.1 已换成 payload +
   新 handler 接口。与 ResourcefulLib/Balm 桥同类，但需要按调用点写规则。
2. **字段访问权限（Mod Menu）**：`TitleScreen.field_32271` 在 1.21.1 变私有，需要 accessor/mixin
   或改用公开 API。
3. **Mixin 重建（Clumps / FerriteCore）**：转换器移除了 load-bearing mixin（经验球合并、
   FastMapStateHolder 等），只“启动”不等于功能保留。
4. **NBT → 数据组件（ShulkerBoxTooltip）**：旧 `ItemStack` NBT 读取被 tombstone，需要桥接到
   1.21.1 的 `CONTAINER` 数据组件。

## 本次修掉的分析器误判

FallingTree 同一个 jar 同时带 `fabric.mod.json`（含 main/client 入口）和 `META-INF/mods.toml`，
分析器原先优先 TOML，把它标成 `forge` / `wrong_loader`，掩盖了真正的网络 API 不兼容。现在：

- `ArtifactScanner` 先读 Fabric 元数据，有 entrypoints 就以 `loader=fabric` 为准，并记录
  `multiLoader=true`；
- `Analyzer` 对“有有效 Fabric 入口的 jar”不再把闲置 Forge/NeoForge 引用判成 `wrong_loader`，
  只在 notes 里注明忽略了多少条。

验证：`gradle test installDist` → 23 个测试全过（含新增的多 loader 用例）。

## 边界

这些扩模结论来自启动、命令和契约级测试，不是完整玩法验收；没有新增玩法规则，也没有做六模组
混装。完整报告与日志在 `runs/p88-mod-expansion/`。
