# p150 — per-lighting 物品批处理 + Iris + shader pack 组合

日期：2026-10-22。p149 只验证了无 shader 的 per-lighting；这里把 shader pack 也叠上。

## 环境

- Iris 1.8.14-beta.1 + Sodium 0.8.13（SHA-1 见 p146）；
- Complementary Reimagined r5.3（SHA-1 `4dfb4278...`），`iris.properties` 已启用；
- 移植后的 ImmediatelyFast（含 p149 的 per-lighting 移植）；
- 单人 `ColdWorld` + 64 石头（合成 playerdata 触发物品渲染）。

## 结果

```text
Using shaderpack: ComplementaryReimagined_r5.3.zip
[mcbridge-port] iris compat active (skipExtension=true)
[mcbridge-port] item lighting variants active
[mcbridge-port] batched-draws total=2768 hud=856 itemModel=204 itemOverlay=204 fps=69
[mcbridge-port] batched-draws total=4536 hud=1448 itemModel=352 itemOverlay=352 fps=73
```

- 进世界成功，无 crash；
- shader 管线、Iris 兼容分支、item per-lighting 变体三者同时执行；
- itemModel/itemOverlay 继续增长。

## 限制

- 静态场景，只产生少量光照变体；
- 单次运行，没有做 shader 下的帧率/视觉 A/B；
- 未测 r5.9.3（已知在 Iris 1.8.14 上编译失败，见 p146）。

## 证据

`launch.log`、`result.json`、`world.png`。
