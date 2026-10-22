# p143 — ImmediatelyFast 移植 + Iris 1.8.14-beta.1 + Sodium 0.8.13

日期：2026-10-22。验证 Iris 兼容不是只对 1.8.1 有效，最新 1.21.1 组合也能跑。

## 环境

- Iris 1.8.14-beta.1（Modrinth，SHA-1 `6776c0340845887477bfa463acc736ce7fcb6de5`）；
- Sodium 0.8.13（SHA-1 `003c114c85ca88ef3362e018deb6aca0c682d6a1`）；
- Fabric Loader 0.19.5 + Fabric API 0.102.0 + 移植后的 ImmediatelyFast；
- 单人 quickPlay 进 `ColdWorld`，未装 shader pack。

## 结果

```text
Found Iris/Oculus 1.8.14-beta.1+mc1.21.1. Enabling compatibility.
[mcbridge-port] iris compat active (skipExtension=true)
[mcbridge-port] batched-draws total=7288 hud=3321 itemModel=0 itemOverlay=0
[mcbridge-port] batched-draws total=9541 hud=4144 itemModel=0 itemOverlay=0
```

- 进世界成功（`IFLatest joined the game`），无 crash report、无 JVM fatal error；
- 我们的 Iris 兼容分支执行，HUD batching 继续工作；
- 截图 `world.png`（暂停菜单，背景为世界）。

## 限制

- 未装 shader pack，只验证 no-shader 管线；
- itemModel/itemOverlay=0：这次没有给物品；
- Iris 1.8.14 是 beta 版本。
