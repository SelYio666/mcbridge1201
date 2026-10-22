# p142 — ImmediatelyFast 移植 + Iris 1.8.1 + Sodium 0.6.1

日期：2026-10-22。目标：把官方那套 Iris 兼容（`IrisCompat` + `BatchableBufferSource` 的
`skipExtension` / `renderWithExtendedVertexFormat`）接到移植版上，并在真实 Iris 环境下验证。

## 环境

- Iris 1.8.1（Modrinth，SHA-1 `292dd61803e8e7c0f18db77a11b1aaaaa6b07ccc`）；
- Sodium 0.6.1（SHA-1 `362e702115cc7958bf7ee660833690148b10baf1`）；
- Fabric Loader 0.19.5 + Fabric API 0.102.0 + 移植后的 ImmediatelyFast；
- 单人 quickPlay 进 `ColdWorld`，未装 shader pack。

## 实现

- 转换件自带的 `IrisCompat.init()` 在检测到 Iris 时会执行（日志
  `Found Iris/Oculus 1.8.1+mc1.21.1. Enabling compatibility.`）；
- 移植版 `BatchableBufferSource` 新增：
  - Iris 加载时 `pendingBuffers/activeLayers` 改用对象键 map；
  - `getBuffer` 里按 `isRenderingLevel` 设置 Iris 的 `skipExtension`（1.5.5 的 IrisCompat 没有
    这个字段，直接反射 Iris 的 `ImmediateState`，读不到就安全跳过）；
  - `drawDirect` 在非 level 渲染时切换 `renderWithExtendedVertexFormat`；
  - 一次性日志 `[mcbridge-port] iris compat active (skipExtension=true)`。

## 结果

```text
[mcbridge-port] iris compat active (skipExtension=true)
[mcbridge-port] batched-draws total=4737  hud=2329 itemModel=0 itemOverlay=0
[mcbridge-port] batched-draws total=11130 hud=4760 itemModel=0 itemOverlay=0
```

- Iris+Sodium 下成功进世界（`IFIris joined the game`），无 crash report、无 JVM fatal error；
- 我们的 Iris 适配分支确实执行（日志），HUD batching 继续工作；
- 截图 `world.png` 是暂停菜单（背景为世界），单人标题正确。

## 限制

- **没有装 shader pack**，只验证了 Iris 的 no-shader 管线；shader pack 下的画面/阴影未验证；
- itemModel/itemOverlay=0：这次没有给物品；
- Iris 版本只测了 1.8.1；Iris 1.8.14/Sodium 0.8 未测。
