# p170 — MixinVertexBuffer 截图 A/B（结论：证据不足，暂不启用）

日期：2026-10-23。目标：在决定是否重新登记 `fast_buffer_upload.MixinVertexBuffer` 之前，先做
“fast_buffer_upload on/off 截图对比”，看 GL 上传路径有没有明显画面破坏。

## 方法

- 临时把 `fast_buffer_upload.MixinVertexBuffer` 加进 config；
- 两次运行同一复制世界（`ColdWorld`、64 石头 playerdata）：
  - on：`fast_buffer_upload=true`（走 `GL15C.glBufferSubData`）；
  - off：`fast_buffer_upload=false`（走原来的 `glBufferData`）；
- options：`renderClouds:false`、`pauseOnLostFocus:false`；截图前把 Minecraft 窗口设为 topmost；
- 用 Pillow 比较两张 870×519 截图，统计单通道差 >8 的像素比例。

## 踩坑（如实记录）

- 前两次截图抓到的是浏览器/支付页/Game Menu：原来的 `_grab_window` 按窗口矩形抓屏，窗口被盖住就
  抓到前景窗口，且失焦会暂停显示菜单；
- 修复：`pauseOnLostFocus:false` + 截图前 `SetWindowPos(HWND_TOPMOST)`，之后截图才是游戏画面。

## 结果

```json
{"pixels": 451530, "changed": 80, "diff_fraction": 0.000177...}
```

- 两张截图几乎一致（差异 0.018%，80 像素，推测来自 HUD/光照的微小差异）；
- 场景是 (0,0,0) 的暗场景 + 快捷栏 64 石头（见 `p170-vertex-on/world.png`）。

## 决定

**证据不足，不启用。** 这只是一个静态暗场景的对比，没有顶点上传压力（大量区块/实体/复杂模型），
也没有多场景/多次运行。为了避免把未验证的 GL 路径带进稳定版：

- 规则里的 `fast_buffer_upload.MixinVertexBuffer` 登记已撤回；
- 端口 jar 恢复为 `inert=4`（sha256 `c68e0768...`）；
- 将来要启用，至少需要：顶点上传压力场景 + 多场景截图对比 + 崩溃/画质回归。

## 证据

`result.json`、`run-on.log`、`run-off.log`、`p170-vertex-on/world.png`、`p170-vertex-off/world.png`。
