# p146 — ImmediatelyFast + 最新 Iris 1.8.14-beta.1 + Sodium 0.8.13 + shader pack r5.3

日期：2026-10-22。把“最新 Iris + shader pack”的组合也验掉。

## 环境

- Iris 1.8.14-beta.1（SHA-1 `6776c0340845887477bfa463acc736ce7fcb6de5`）；
- Sodium 0.8.13（SHA-1 `003c114c85ca88ef3362e018deb6aca0c682d6a1`）；
- Complementary Reimagined r5.3（SHA-1 `4dfb4278bdca478cb0a8c185ff8a3d2d1c646c86`），
  `config/iris.properties` 里 `enableShaders=true`、`shaderPack=ComplementaryReimagined_r5.3.zip`；
- 复制 world 后 `DayTime=6000`、`difficulty=0`（白天 + 和平）。

## 结果

```text
Using shaderpack: ComplementaryReimagined_r5.3.zip
[mcbridge-port] iris compat active (skipExtension=true)
[mcbridge-port] batched-draws total=10979 hud=5917 itemModel=0 itemOverlay=0
[mcbridge-port] batched-draws total=14883 hud=7776 itemModel=0 itemOverlay=0
```

- shader pack 被 Iris 1.8.14 加载并创建管线；
- 进世界成功（`IFShaderLatest joined the game`），无 crash report/JVM fatal error；
- HUD 批处理在 shader 下继续工作；
- 截图 `world.png`：Iris/Sodium 渲染器、shader 画面、约 117 fps；该次没给物品，item 计数 0 属预期。

## 限制

- 只测了 r5.3 这个与 1.8.1 同期的 pack；r5.9.3 在 Iris 1.8.1 下会编译失败（见 p145），
  没有在 1.8.14 上重试 r5.9.3；
- 只跑了一遍，无长时 soak。
