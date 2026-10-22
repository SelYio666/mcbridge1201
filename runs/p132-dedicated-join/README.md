# p132 — 启动器客户端加入真实专用服务器（Fabric 1.21.1）

日期：2026-10-22。目标：验证启动器的客户端加入**专用服务器**的路径（
`--quickPlayMultiplayer`），而不只是单人 integrated server。

## 做法

1. 启动 `work/instances/fabric-1.21.1-server`（Fabric 1.21.1 专用服务器，`online-mode=false`，
   端口 25565），等待 `Done (`；
2. 启动器 `build_command("1.21.1", ...)` 加 `--quickPlayMultiplayer 127.0.0.1:25565` 启动客户端；
3. 等服务器日志出现 `Guest joined the game`，截图。

## 结果

| 项 | 结果 |
|---|---|
| 专用服务器启动 | ✅ `server_ready: true` |
| 客户端加入 | ✅ 服务器日志 `Guest joined the game` |
| 截图 | ✅ 标题 `Minecraft 1.21.1 - Multiplayer (3rd-party Server)`，世界内画面 |
| 客户端模式 | 原版 1.21.1（未加载模组），离线账号 |

## 一次失败与原因（如实）

第一次客户端停在**首次启动的无障碍引导页**（`Welcome to Minecraft! ... Accessibility`），
quickPlay 不继续。给客户端根目录写 `options.txt`（`onboardAccessibility:false`）后通过。
说明：**新客户端目录必须先写 options.txt，否则任何 quickPlay 都会被引导页挡住**——
这条对单人和多人同样适用。

## 与旧证据的关系

仓库早期 p75/p76 已经在专用服务器上做过**双客户端同步/移动**验证（含转换模组）；
本次补的是“启动器直接启动原版客户端 + quickPlayMultiplayer 加入”的集成路径。

## 证据

- `server.log`：`Done (`、`Guest joined the game`、正常 `Stopping the server`；
- `client.log`：启动命令含 `--quickPlayMultiplayer 127.0.0.1:25565`；
- `world.png`：多人服务器世界内截图；
- `result.json`：脚本记录。

## 边界

- 只测了 Fabric 1.21.1 专用服务器 + 原版客户端；**未测** NeoForge/Forge 专用服务器；
- 离线模式（online-mode=false），未测正版认证；
- 单次加入，未测长时间在线/断线重连/多客户端并发。
