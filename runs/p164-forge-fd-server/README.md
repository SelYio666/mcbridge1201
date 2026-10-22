# p164 — Forge 1.20.1 专用服务器 + Farmer's Delight 1.3.4 + 同模组客户端加入

日期：2026-10-23。把 p163 的“带模组专用服务器”在 Forge 侧也补齐。

## 环境

- Forge 1.20.1-47.4.28 专用服务器（安装见 p159）；
- Farmer's Delight 1.20.1-1.3.4（Modrinth，SHA-1 `26f615fd35f652021f5b0f1cba68afa7d578fe15`）；
- 服务端与客户端 `mods/` 都放同一 jar；服务端端口 25569、`online-mode=false`；
- 客户端版本 `1.20.1-forge-47.4.28` + quickPlayMultiplayer。

## 结果

```json
{"ready": true, "mod": true, "joined": true}
```

- 服务端 `Done (` 就绪，日志含 `farmersdelight`；
- 客户端 `FDForge joined the game`；
- 截图 `world.png` 为多人世界；
- 测试后清理客户端 `mods/`。

## 限制

- 只验证加载与加入，没有做方块/配方/网络同步的深度测试；
- 单次运行，无 soak。

## 证据

`server.log`、`client.log`、`result.json`、`world.png`。
