# p130 — NeoForge 21.1.264 + Jade（客户端/服务端数据模组）进世界

日期：2026-10-22。补“网络/数据同步类模组”的缺口：Jade 15.10.6（NeoForge 1.21.1）通过插件通道
从服务端取方块/实体信息并渲染 HUD。单人模式走 integrated server，仍会走注册与数据提供链路。

## 结果

| 项 | 结果 |
|---|---|
| 模组 SHA-1 | ✅ `88ee316e…` |
| 加载 | ✅ `Jade 15.10.6+neoforge (jade)`，`mod/jade` 资源包 |
| 插件 | ✅ 日志加载 `VanillaPlugin` / `UniversalPlugin` / `DebugPlugin` / `CorePlugin` / `AccessibilityPlugin` |
| 进世界 | ✅ `joined the game` |
| HUD 可见证据 | ✅ 低头看方块后出现 Jade tooltip：`Birch Leaves / minecraft`（`jade-tooltip.png`） |

## 一次失败与原因（如实）

第一次运行没进世界：截图显示 NeoForge 的“Warning while loading mods”警告页，原因是
`mods/` 里残留了 **Forge 版** AppleSkin（p129 结束时 Windows 文件锁导致清理失败），NeoForge
因此停在不兼容警告页，quickPlay 不继续。清空 `mods/` 只留 Jade 后通过。
教训：切加载器测试前必须清空 `mods/`，并处理文件锁重试。

## 证据

- `jade-tooltip.png`：世界内 Jade tooltip（Birch Leaves）；
- `world.png` / `world-f3.png`：进世界与 F3 画面；
- `launch.log`：模组加载、插件加载、joined；
- `result.json`：脚本记录。

## 边界

- 只验证了单人 integrated server 的数据同步与 HUD；**没有**验证真正的多人专用服务器；
- 没有逐项测试 Jade 的所有 provider（只看到方块 tooltip）；
- 单次启动，无 soak。

测试实例 mods/saves/options 已清理。
