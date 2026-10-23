# v0.5.4 — 地图 atlas 生命周期修复 + VertexBuffer fast path

v0.5.3 恢复了地图 atlas 并启用了 VertexBuffer；这版补上 atlas 的动态更新与正常退出清理，并修掉
一个**真实崩溃**：世界退出时 atlas 已释放，排队的地图帧仍往已关闭的 `NativeImage` 写入
（`Image is not allocated`）。

## 地图 atlas 生命周期

- `locked=0` 的 held map 在玩家移动后收到第二次地图更新，`map-atlas update count=2`；截图里
  地形覆盖了初始棋盘图案；
- 正常 client stop（测试 probe 调 `class_310.method_1592`）：
  `Stopping! → map-atlas keep-dummy → close id=0 → clear atlases=1`，exit 0、crash=null；
- 修复：`MapAtlasTexture` 增加幂等 `closed`/`isClosed()`；`updateAtlasTexture` 在 atlas 已 close
  时打印 `skip-closed` 并返回，不再写已释放图像。修复前的崩溃报告保留在
  `runs/p181-map-atlas-lifecycle/crash-before-fix-map.txt`；
- 证据：`runs/p181-map-atlas-lifecycle/`。

## VertexBuffer（p178，仍包含）

- 1.21.1 `method_43442/43443/60829` 全部 redirect；80 盔甲架压力 + off/off、on/on 对照；
  on 侧 60/79 条 fast 标记、最高 76k 次 `glBufferSubData`；off/on 截图差 0.0087%，低于
  off/off 对照 0.214%；无 GL/mixin 错误；
- 证据：`runs/p178-vertex-upload/`。

## 其它

- 截图 helper 按 PID 匹配窗口 + `PrintWindow`，不再依赖 topmost/屏幕抓取；
- 官方 1.21.1 无 `MixinBufferBuilder`/`MixinFontManager`，端口剩余 2 inert 是 1.20.4 遗留死代码
  （p180），不登记；
- p181 第一次 in-frame disconnect 还触发了 HUD batching 的 NPE（probe 非正常调用方式，正常
  stop 不触发）；没有为此改 HUD 代码，保留 crash 报告说明。

## 未验证

- 地图 atlas 满 1024 张换 atlas；多展示框/旋转；完整探索；
- 正常退出只验证了 probe 的 stop 路径，ESC→Save and Quit 鼠标路径未测；
- 不宣称性能收益；只测一台 NVIDIA 机器和一个合成压力场景；shader pack 下未重跑。

## 资产 / 门禁

- `mcbridge-launcher-0.5.4.zip`，11,960,114 bytes，SHA-256
  `54961b0255f60377ce2659fb4975d7a4d51742867350b8a6bfa3577da0d6e13a`；
- `tools/test_portable.py`：deps/verify/status/guide 全过；
- Java 25/25；`test_review_fixes` 共 83 项（本次 82/82 + `/api/jvm` 网络 skip）；`verify_evidence` passed；push 触发 CI。
