# p128 — NeoForge 21.1.264 + 内容模组（Farmer's Delight）进世界

日期：2026-10-22。p127 只验证了显示类模组（AppleSkin）；这次换一个会**注册方块/物品/标签/
世界生成**的内容模组（Farmer's Delight 1.21.1-1.3.4，Modrinth），验证注册链路。

## 结果

| 项 | 结果 |
|---|---|
| 模组 SHA-1 | ✅ `27675ddf…` 匹配 |
| 加载 | ✅ `Farmer's Delight 1.3.4 (farmersdelight)`，`mod/farmersdelight` 资源包 |
| 注册错误 | ✅ 日志里没有 `Failed to register` / Registration ERROR |
| 进世界 | ✅ `joined the game`，F3 标题 `Minecraft NeoForge* 1.21.1 - Singleplayer` |
| 证据细节 | F3 目标信息出现 `#farmersdelight:unaffected_by_rich_soil` 标签 |

截图见 `world.png`；`launch.log` 是完整日志；`result.json` 是脚本记录。

## 边界

- 只验证了加载 + 进世界 + 标签注册；**没有**逐项测试方块放置/合成/食物效果/世界生成；
- 没有测需要网络同步或复杂多方块结构的模组；
- 单次启动，无 soak；世界仍是服务端拷来的 1.21.1 世界。

## 结论

NeoForge 21.1.264 能加载并运行至少一个**内容模组**（不只是 HUD 类），且 quickPlay 进世界正常。
测试实例的 mods/saves/options 已清理。
