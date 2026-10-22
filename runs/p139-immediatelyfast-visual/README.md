# p139 — ImmediatelyFast HUD batching 正常世界可视截图

日期：2026-10-22。用途：给 p134 的计数证据补一张**正常出生、白天、无合成 playerdata** 的进世界截图。

## 条件

- 同一个移植 jar（sha256 `49719cfef70d7303214af48dbbda30234ccb19b8deb2321edccec5363e3a9b6c`，
  带 HUD/物品 consumer 注入与二次释放修复）；
- 复制 `fabric-1.21.1-server` 的 world，`allowCommands=1`、`DayTime=6000`（通过 level.dat 字节补丁）；
- `--quickPlaySingleplayer ColdWorld`，用户名 `IFVis`，未写任何 playerdata。

## 结果

```text
[mcbridge-port] hud batching begin
[mcbridge-port] batched-draws total=10977 hud=3733 itemModel=0 itemOverlay=0
[mcbridge-port] batched-draws total=13915 hud=4584 itemModel=0 itemOverlay=0
```

- 进世界：`IFVis joined the game`；
- HUD batching 在正常世界同样生效（hud=4584）；
- 该次快捷栏为空，所以 itemModel/itemOverlay 为 0 属预期；物品计数证据看 p134。

## 证据

`launch.log`、`result.json`、`world.png`（白天、草地/树、F3 + HUD 正常）。
