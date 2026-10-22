# p131 — Forge 1.20.1 + 内容模组（Farmer's Delight）进世界

日期：2026-10-22。补 Forge 侧的内容模组覆盖（p129 只验证了显示类 AppleSkin）。

## 结果

| 项 | 结果 |
|---|---|
| Forge | `1.20.1-forge-47.4.28` |
| 模组 | Farmer's Delight 1.20.1-1.3.4，SHA-1 `26f615fd…` 匹配 |
| 加载 | 日志生成 `farmersdelight-common.toml`（`ForgeConfigSpec` 初始化） |
| 注册错误 | ✅ 无 `Failed to register` / farmersdelight ERROR |
| 进世界 | ✅ `joined the game`，F3 标题 `Minecraft* Forge 1.20.1 - Singleplayer` |
| 世界 | 官方 1.20.1 服务端生成（level-seed 131）后拷入 |

截图：`world.png`、`world-f3.png`；日志：`launch.log`；记录：`result.json`。

## 诚实说明

- 这张 F3 截图的准星没有落在方块上，**没有拍到 farmersdelight 的标签行**；
  内容模组注册的可见证据是“配置生成 + 无注册错误 + 进世界”，不是 tooltip 级别的截图；
- 服务端生成目录（约 107 MB）与测试实例 mods/saves 已清理。

## 边界

- 只测了 Farmer's Delight（方块/物品/作物/配方），没有逐项测试合成、食物效果、世界生成；
- 没有测网络同步或复杂多方块模组；
- 单次启动，无 soak；未测多人专用服务器。
