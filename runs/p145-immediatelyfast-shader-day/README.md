# p145 — ImmediatelyFast 移植 + Iris 1.8.1 + Sodium 0.6.1 + Complementary Reimagined r5.3

日期：2026-10-22。补上 Iris 的最后一块：**真正启用 shader pack**（不只是 no-shader 管线）。

## 环境

- Iris 1.8.1（SHA-1 `292dd61803e8e7c0f18db77a11b1aaaaa6b07ccc`）；
- Sodium 0.6.1（SHA-1 `362e702115cc7958bf7ee660833690148b10baf1`）；
- Complementary Reimagined **r5.3**（Modrinth，SHA-1 `4dfb4278bdca478cb0a8c185ff8a3d2d1c646c86`）；
- 复制 world 后把 `DayTime=6000`、`difficulty=0`（白天 + 和平），避免夜里被僵尸打死；
- `config/iris.properties`：`enableShaders=true`、`shaderPack=ComplementaryReimagined_r5.3.zip`。

## 结果

```text
Using shaderpack: ComplementaryReimagined_r5.3.zip
[mcbridge-port] iris compat active (skipExtension=true)
[mcbridge-port] batched-draws total=20756 hud=9303 itemModel=1395 itemOverlay=1395
[mcbridge-port] batched-draws total=25658 hud=11146 itemModel=1856 itemOverlay=1856
```

- shader pack 被 Iris 真正加载并创建管线（日志 `Using shaderpack`，F3 里能看到 Iris/Sodium 渲染器）；
- 进世界成功，HUD/物品/overlay 三条批处理路径在 shader 下继续有真实计数；
- 截图 `world.png`：白天、草地/树、HUD 正常，约 113 fps（F3 显示）。

## 版本兼容备注

- 先试了最新的 Complementary Reimagined **r5.9.3**：Iris 1.8.1 下 `CustomUniforms` 编译失败，
  Iris 回退到 vanilla 管线（游戏没崩，但 shader 没生效）——这是 pack 与 Iris 版本不匹配，
  不是 ImmediatelyFast 的问题；换同期的 r5.3 后正常。
- 未测 Iris 1.8.14 + Sodium 0.8.13 + shader pack 的组合。

## 证据

`launch.log`、`result.json`、`world.png`。
