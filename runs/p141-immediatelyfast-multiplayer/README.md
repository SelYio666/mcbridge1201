# p141 — ImmediatelyFast batching 在专用服务器多人环境生效

日期：2026-10-22。补上“只测过单人 integrated server”的空白：真实 Fabric 1.21.1 专用服务器 +
启动器客户端（带移植后的 ImmediatelyFast），服务器控制台给客户端 64 个石头。

## 条件

- 服务端：`work/instances/fabric-1.21.1-server`，`online-mode=false`、端口 25565，`fabric-server-launch.jar`；
- 客户端：Fabric Loader 0.19.5 + Fabric API 0.102.0 + 移植后的 ImmediatelyFast（同一个 jar，
  sha256 `49719cfef70d7303214af48dbbda30234ccb19b8deb2321edccec5363e3a9b6c`）；
- `--quickPlayMultiplayer 127.0.0.1:25565`，用户名 `IFMulti`；
- 加入后服务端执行 `give IFMulti minecraft:stone 64`。

## 结果

```text
[mcbridge-port] batched-draws total=20572 hud=3755 itemModel=1806 itemOverlay=903
[mcbridge-port] batched-draws total=25168 hud=4659 itemModel=2258 itemOverlay=1129
```

- 服务端 `Done (`、客户端加入成功（截图标题 `Multiplayer (3rd-party Server)`）；
- HUD、物品模型、数量 overlay 三条批处理路径在多人下同样有真实计数；
- 截图 `world.png`：快捷栏两格 64 石头（服务器给了两次，世界持久化），HUD 正常。

## 限制

- 只验证客户端侧 batching；服务端没有装 ImmediatelyFast（它是客户端模组）；
- 单次加入，无多客户端/长时间 soak；
- 没有测 Iris。
