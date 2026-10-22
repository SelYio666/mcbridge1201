# p161 — NeoForge 21.1.264 专用服务器 + 启动器客户端加入

日期：2026-10-22/23。补上“NeoForge 专用服务器未测”的空白。

## 安装过程（如实记录）

- 安装器前两次 `--installServer` 都失败：`maven.neoforged.net` 连接超时，一批库没下下来
  （`install.log` / `install-retry2.log`）；
- 把客户端实例 `work/launcher-e2e/libraries` 复制进服务端目录后，安装器复用已有库，
  第三次 `install-retry3.log`：`The server installed successfully`；
- 说明：不是安装器/NeoForge 本身有问题，是网络 + 库复用。

## 加入测试

- 服务端：`java @user_jvm_args.txt @libraries/net/neoforged/neoforge/21.1.264/win_args.txt nogui`，
  `online-mode=false`、端口 25567；
- 客户端：启动器已装的 `neoforge-21.1.264`，`--quickPlayMultiplayer 127.0.0.1:25567`，
  用户名 `NeoGuest`；
- 结果：服务端 `Done (`，客户端加入成功（服务端日志 `NeoGuest joined the game`），
  `result.json` 为 `{"server_ready": true, "client_joined": true}`。

## 限制

- 只验证“能加入”，没有装服务端模组/深度网络同步；
- 单次运行，无 soak；
- 服务端库是复用客户端安装的，不是全新干净下载（干净环境需要网络恢复）。

## 证据

`server.log`、`client.log`、`result.json`、`world.png`。
