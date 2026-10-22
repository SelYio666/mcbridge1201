# p159 — Forge 1.20.1 专用服务器 + 启动器客户端加入

日期：2026-10-22。补上 P2 里“Forge 专用服务器未测”的空白。

## 环境

- Forge **1.20.1-47.4.28** 专用服务器：`java -jar forge-installer.jar --installServer`
  （安装器本地缓存 `work/launcher-e2e/installers/`，安装成功）；
- 服务器：`online-mode=false`、端口 25566、level-name=world；
- 客户端：启动器已安装的 `1.20.1-forge-47.4.28` 版本，`--quickPlayMultiplayer 127.0.0.1:25566`，
  用户名 `ForgeGuest`，无额外模组。

## 结果

- 服务端 `Done (` 就绪；
- 客户端加入成功：服务端日志 `ForgeGuest joined the game`；
- 截图 `world.png` 为多人游戏画面；
- 结果 JSON：`{"server_ready": true, "client_joined": true}`。

## 限制

- 只测了“能加入”，没有做 Forge 网络包/模组同步的深度验证；
- 没有装服务端模组；Forge 客户端也是原版模组集；
- 单次运行，无 soak。

## 证据

`server.log`、`client.log`、`result.json`、`world.png`。
