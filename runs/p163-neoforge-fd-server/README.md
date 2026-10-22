# p163 — NeoForge 专用服务器 + Farmer's Delight 1.3.4 + 同模组客户端加入

日期：2026-10-23。补“专用服务器只测了原版服务端”的空白：服务端和客户端都装同一个内容模组。

## 环境

- NeoForge 21.1.264 专用服务器（库复用本地安装，见 p161）；
- Farmer's Delight 1.21.1-1.3.4（Modrinth，SHA-1 `27675ddfcb8cc37e6ea1ab6c15051c7949d94657`）；
- 服务端 `mods/FarmersDelight-1.21.1-1.3.4.jar`；客户端 `work/launcher-e2e/mods/` 放同一 jar；
- 服务端端口 25568、`online-mode=false`；客户端 `neoforge-21.1.264` + quickPlayMultiplayer。

## 结果

```json
{"ready": true, "mod": true, "joined": true}
```

- 服务端 `Done (` 就绪，日志含 `farmersdelight`（模组已加载）；
- 客户端 `FDGuest joined the game`；
- 截图 `world.png` 为多人世界；
- 测试后已清理客户端 `mods/`。

## 限制

- 只验证“客户端/服务端同模组能加载并加入”，没有做方块交互/配方/网络同步的深度测试；
- 单次运行，无 soak；
- 服务端库复用本地客户端安装，干净环境需要网络恢复后重装。

## 证据

`server.log`、`client.log`、`result.json`、`world.png`。
