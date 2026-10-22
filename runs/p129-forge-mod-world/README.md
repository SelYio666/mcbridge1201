# p129 — Forge 1.20.1-47.4.28 + AppleSkin 进世界

日期：2026-10-22。目标：补上三加载器里的 Forge 缺口（之前只到主菜单）。过程中又抓到一个
安装流程的真 bug。

## 过程

1. `install_forge("1.20.1")` 装好 `1.20.1-forge-47.4.28`（95 s）；
2. 首次启动失败：`version 1.20.1 not installed`——Forge profile `inheritsFrom` 原版，但安装器
   不负责原版 base；
3. 补装原版 1.20.1（11 s，共用已有 assets），重新启动；
4. 用官方 1.20.1 服务端生成一个世界（`p129-server/world`，服务端正常 `Done` + 保存退出）；
5. 放入 AppleSkin Forge 2.5.1（Modrinth，SHA-1 `81919356…`），`--quickPlaySingleplayer` 进世界。

## 结果

| 项 | 结果 |
|---|---|
| Forge | `1.20.1-forge-47.4.28`（`--launchTarget forgeclient`） |
| 模组 | AppleSkin 2.5.1 Forge，SHA-1 匹配 |
| 模组初始化 | `appleskin-client.toml` 配置生成（`ForgeConfigSpec` 日志） |
| 进世界 | ✅ `ModUser joined the game`，截图标题 `Minecraft* Forge 1.20.1 - Singleplayer` |
| quickPlay 参数 | ✅ 命令行包含 `--quickPlaySingleplayer ColdWorld120`（p127 的修复同样生效） |

截图：`world.png`；日志：`launch.log`；记录：`result.json`、`server-gen.json`。

## 顺带修复

`install_forge()` / `install_neoforge()` 之前**不确保原版 base**（GUI 会先调
`install_vanilla_launcher_profile`，CLI 直接调 loader 安装就会踩坑）。现在两者安装前都会补
原版 base；新增离线回归 `LOADER install_forge ensures the vanilla base first`。

## 边界

- 只测了 AppleSkin（显示类），**没测** Forge 内容模组/网络模组；
- 世界是服务端生成后拷入，未测新建世界/多人/soak；
- 单次启动。

测试实例的 mods/saves/options 已清理；服务端生成目录 `work/tmp/p129-server`（约 107 MB）
在验证后已删除，不占磁盘。
