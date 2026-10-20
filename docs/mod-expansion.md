# 扩模结果：6 个新模组（2026-10-19）

这一步回答“三个样本的成功能不能推广”。结论：**不能**。6 个原始 1.20.1 模组都完成了
CenturyBridge 转换和现有通用规则 patch，但 5 个有明确兼容性阻断，1 个只到启动范围。

| 模组 | 客户端 | 服务端/功能 | 结论 |
|---|---|---|---|
| AppleSkin 2.5.2 | 初始化、同步包、HUD、状态效果 tooltip 路径均通过（契约级） | 真实悬停未测 | 基本修复 |
| Mod Menu 7.2.2 | 主菜单 + 列表行可见；滚动与搜索过滤均验证（截图） | 背景简化为填充；真实输入/配置界面未测 | 通过（视觉级） |
| Clumps 12.0.0.4 | 主菜单 120 tick | 经验球合并通过（companion 桥：3+7→10；tick 驱动、固定 2 格） | 核心功能恢复 |
| FallingTree 4.3.4 | 初始化已修 | 入服 send/receive 已复测通过；砍树未测 | 部分修复 |
| FerriteCore 6.0.1 | 主菜单 120 tick | 启动/200 tick/正常停服；移除 2 个 mixin | 仅启动、降级 |
| ShulkerBoxTooltip 4.0.4 | 主菜单 | provider 契约通过：`diamondCount=5`；HUD 悬停未测 | 部分修复 |

## 网络桥进展（2026-10-19 补）

已新增 `rules/fabric-1.21.1/fabric-legacy-networking.json`、`identifier-single-arg.json`，以及
`FabricLegacyNetworking` / `IdentifierBridge` 两个桥：

- 旧 `ClientPlayNetworking.registerGlobalReceiver(Identifier, PlayChannelHandler)` → 注册原始
  payload 并回调旧 handler；被删除的 `PlayChannelHandler` 由嵌入的 shim 提供（只嵌嵌套类，不覆盖
  Fabric API 的 `ClientPlayNetworking`）；
- 旧 `new CustomPayloadC2SPacket(Identifier, PacketByteBuf)` → 用新 `class_2658(payload)` 构造；
- 旧 `ServerPlayNetworking.send(player, id, buf)` → 包成 S2C 原始 payload；
- `new Identifier(String)` → 拆 `namespace:path` 调 `Identifier.of`。

实测：FallingTree 入服已复测——服务端旧 `send` 走桥、客户端 receiver 收包，`TestPlayer` 正常
加入（`runs/p90-fallingtree-join/`）；AppleSkin 初始化与 `SyncHandler.makeSyncPacket` 不再崩；食物 tombstone 也已用
`AppleSkinFoodBridge`（`appleskin-food.json`）映射到 `DataComponentTypes.FOOD`，HUD 不再抛
`UnsupportedOperationException`，客户端保持在单人世界。仅剩原版 `icons.png` 材质缓存告警（环境
资源不完整），FallingTree 入服路径未复测。证据 `runs/p89-legacy-networking/`。

## 需要新增的适配（按类型）

1. **Fabric 网络桥（AppleSkin / FallingTree）**：旧的 `ClientPlayNetworking.registerGlobalReceiver(Identifier, PlayChannelHandler)` 和
   `ServerPlayNetworking.send(player, Identifier, PacketByteBuf)` 在 1.21.1 已换成 payload +
   新 handler 接口。与 ResourcefulLib/Balm 桥同类，但需要按调用点写规则。
2. **字段访问权限（Mod Menu）**：`TitleScreen.field_32271` 在 1.21.1 变私有，需要 accessor/mixin
   或改用公开 API。
3. **Mixin 重建（Clumps / FerriteCore）**：转换器移除了 load-bearing mixin（经验球合并、
   FastMapStateHolder 等），只“启动”不等于功能保留。Clumps 的合并已用 companion 桥恢复
   （`java/src/compat-clumps/` + `tools/build_clumps_companion.py`，证据 `runs/p93-clumps-merge/`）；
   FerriteCore 仍未做。
4. **NBT → 数据组件（ShulkerBoxTooltip）**：旧 `ItemStack` NBT 读取被 tombstone，需要桥接到
   1.21.1 的 `CONTAINER` 数据组件；
5. **食物组件（AppleSkin）已补**：`appleskin-food.json` 把 5 个 tombstone 映射到
   `DataComponentTypes.FOOD`（`runs/p89-legacy-networking/`）。

## 本次修掉的分析器误判

FallingTree 同一个 jar 同时带 `fabric.mod.json`（含 main/client 入口）和 `META-INF/mods.toml`，
分析器原先优先 TOML，把它标成 `forge` / `wrong_loader`，掩盖了真正的网络 API 不兼容。现在：

- `ArtifactScanner` 先读 Fabric 元数据，有 entrypoints 就以 `loader=fabric` 为准，并记录
  `multiLoader=true`；
- `Analyzer` 对“有有效 Fabric 入口的 jar”不再把闲置 Forge/NeoForge 引用判成 `wrong_loader`，
  只在 notes 里注明忽略了多少条。

验证：`gradle test installDist` → 23 个测试全过（含新增的多 loader 用例）。

## Mod Menu 列表进展（2026-10-20 补）

模组列表**打开并稳定 60 tick**（无异常、无崩溃报告），截图见
`runs/p94-modmenu-list/modmenu-list.png`；但**列表行未绘制**（探针读到 8 个条目，画面黑区），
属真实视觉缺陷，疑似 1.20.1 列表几何字段与新选择列表状态不一致。越过：final `render`/`method_37020`
覆盖（通用改名 + 重复方法丢弃）、`class_4280`/`class_350` 旧构造（`LegacyEntryListWidget`/
`LegacyParentWidget` + 旧字段与 `setLeftPos`）、`Identifier(String)`、`TexturedButtonWidget`
旧纹理构造（`LegacyTexturedButton` 用 `DrawContext.drawTexture` 重绘旧图集区域）、
`TextFieldWidget.tick()`（1.21.1 改为按真实时间闪烁，桥仅保持调用点可链接）。
未测：截图、滚动/搜索/配置界面交互。证据 `runs/p94-modmenu-list/`。

## Mod Menu 进展（2026-10-19 补）

- 私有 `TitleScreen.field_32271` 用反射桥读取；
- 新增规则类型 `methodRenames`：把 `ModMenuButtonWidget.method_25394` 改名为 1.21.1 的
  `renderWidget`（`method_48579`），并把 `super` 调用改到新钩子，避免删掉更新角标绘制；
- 真实客户端主菜单不再抛 `IllegalAccessError` / `IncompatibleClassChangeError`，无新崩溃报告；
  模组列表界面未打开验证。证据 `runs/p92-modmenu/`。

## ShulkerBoxTooltip 进展（2026-10-19 补）

`shulker-nbt.json` 把旧 `BlockEntityTag.Items` NBT 路径桥到 1.21.1 的 `CONTAINER` 组件，
`dyecolor-components.json` 修掉 `DyeColor.method_7787` 返回类型变化，网络 shim 补齐客户端/集成服务端
的旧 receiver。契约探针输出：

```text
SHULKER_FIXTURE nativeContainerCount=5
SHULKER_PROVIDER class=...ShulkerBoxPreviewProvider
SHULKER_CONTRACT_RESULT diamondCount=5 expected=5 shouldDisplay=false
```

证据 `runs/p91-shulker-provider/`；`shouldDisplay=false` 与真实悬停视觉未排查。

## 边界

这些扩模结论来自启动、命令和契约级测试，不是完整玩法验收；没有新增玩法规则，也没有做六模组
混装。完整报告与日志在 `runs/p88-mod-expansion/`。
