# p140 — ImmediatelyFast batching 在世界上 soak ~95 秒

日期：2026-10-22。目的：不是在菜单/加载画面“算通过”，而是在单人世界里连续跑约 95 秒，
确认 HUD 批处理持续工作且没有再次出现 allocator 二次释放的 JVM 崩溃。

## 条件

- 同一个移植 jar（sha256 `49719cfef70d7303214af48dbbda30234ccb19b8deb2321edccec5363e3a9b6c`）；
- 复制 world、`allowCommands=1`、用户名 `IFSoak`；
- 进世界后保持 ~95 秒，再开 F3 截图并正常结束。

## 结果

```text
[mcbridge-port] batched-draws total=178363 hud=42073 itemModel=0 itemOverlay=0
[mcbridge-port] batched-draws total=182392 hud=43021 itemModel=0 itemOverlay=0
[mcbridge-port] batched-draws total=186404 hud=43965 itemModel=0 itemOverlay=0
```

- `IFSoak joined the game`，约 95 秒内无 crash report、无 JVM fatal error（唯一的 401 是离线认证）；
- hud 从几百涨到 **43,965**，说明批处理在持续运行，不是一次性计数；
- itemModel/itemOverlay=0 属预期：合成 playerdata 是按 `IFUser` 的 UUID 写的，`IFSoak` 没有物品；
  物品/overlay 证据看 p134。

## 证据

`launch.log`、`result.json`、`world.png`。
