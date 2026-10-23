# v0.5.3 — VertexBuffer 动态上传 fast path + 地图 atlas 边界验证

v0.5.2 恢复了 ImmediatelyFast 的地图 atlas；这版补上边界验证，并启用最后一个经过压力测试的
渲染 mixin：`fast_buffer_upload.MixinVertexBuffer`。不宣称性能收益。

## VertexBuffer 动态上传

- `MixinVertexBuffer` 按 1.21.1 重写：redirect `method_43442`、`method_43443` 和新增的
  `method_60829`；STATIC（35044）仍走 `glBufferData`，较大的 dynamic buffer 复用
  `glBufferSubData`；加低频 `[mcbridge-port] fast-buffer-upload subdata` 证据计数。
- 80 个静止盔甲架压力场景（相机每 tick 锁定）：
  - off 侧 0 条 fast 标记；on 侧 60/79 条，最高 76k 次 `glBufferSubData`；
  - off/off 对照像素差 0.214%，on/on 0.208%，off/on **0.0087%**；
    off/on 差异没有超过同 jar 的 run-to-run 基线；
  - 无 `GL_INVALID` / `OpenGL error` / Mixin apply / crash。
- 证据：`runs/p178-vertex-upload/`。

## 地图 atlas 边界

- 两张地图（map id 1/2）分别落到 atlas tile 0/1（packed 0 / 256），与物品展示框里的地图同屏
  渲染；截图、bind 日志、无 ClassCastException/crash（`runs/p177-map-atlas-edge/`）。
- p175 的第一人称手持地图证据仍在（`runs/p175-map-atlas/`）。

## 其他

- 截图工具改为按启动 PID 匹配窗口 + `PrintWindow(PW_RENDERFULLCONTENT)`；此前
  topmost+屏幕抓取偶发抓到浏览器（p178 实测），现在证据截图稳定。
- 剩余 inert：`MixinBufferBuilder`（`field_1555` 已不存在）、`MixinFontManager`
  （`method_27541` 不存在），都需要实际移植，不是只加 config。

## 未验证

- 不宣称性能提升；只测一台 NVIDIA 机器、一个合成压力场景；shader pack 下未重跑；
- 地图动态更新/标记、atlas 满 1024 张、世界退出清理未测；
- 长时间 soak / 其它 GPU 驱动未测。

## 资产 / 门禁

- `mcbridge-launcher-0.5.3.zip`，11,960,113 bytes，SHA-256
  `5eaef399affc5ec745848c6615932382bcb7bcd42058a07330028c5f91b57ce3`；
- `tools/test_portable.py`：deps/verify/status/guide 全过；
- Java 25/25；`test_review_fixes` 81/81；`verify_evidence` passed；push 触发 CI。
