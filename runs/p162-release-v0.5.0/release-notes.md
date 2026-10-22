# v0.5.0 — ImmediatelyFast 1.21.1 batching 移植 + 专用服务器/mrpack 验证

## 重点

- **ImmediatelyFast 1.21.1 batching 移植**（兼容性为目标）：
  - `BatchableBufferSource`（ByteBufferBuilder/MeshData、反射 draw、Iris 适配）；
  - `BatchingBuffers` + `HudBatchingBufferSource`，HUD/物品/overlay 专用批处理；
  - `MixinDrawContext` / `MixinGameRendererHud` 接入 1.21.1 的 HUD 与物品 consumer；
  - item per-lighting 变体（`LightingState` + `WrappedRenderLayer`）；
  - `SimpleImmediate` 回退路径。
- **实测证据**（均在 `runs/`）：
  - 单人/多人：`p134`、`p141`，HUD/itemModel/itemOverlay 计数真实增长；
  - HUD 开关 A/B：`p137`；95 秒 soak：`p140`；
  - Iris 1.8.1 / 1.8.14 + shader pack r5.3：`p142`/`p143`/`p145`/`p146`；
  - 关闭 universal batching 回退：`p147`；per-lighting：`p149`/`p150`。
- **诚实的性能结论**：HUD 场景差异在噪声内（`p148`）；80 盔甲架交错两轮显示开启
  universal batching **慢约 13%**（`p157`）；不宣称性能收益。
- **启动器**：Forge / NeoForge **专用服务器**客户端加入（`p159`/`p161`）；真实 mrpack
  （下载文件 + SHA-1 校验 + overrides）导入通过（`p160`）。
- **便携包修复**：嵌入式 Python 的 `._pth` 不会把脚本目录加入 `sys.path`，`mclaunch.py`
  现在显式插入；`tools/test_portable.py` 全绿。

## Sodium

1.20.1 的 Sodium 0.5.13 静态探针为 `blocked_static`（missingClass=13、missingMember=15、
descMismatch=16，`runs/p158-sodium-probe/`），需要移植其渲染内核，本轮不做，也不宣称可用。

## 资产

- `mcbridge-launcher-0.5.0.zip`（约 11.96 MB，内置 CPython 3.12 与 vendored 依赖）；
- SHA-256：`aa881f0619430374e2631a995d79065403ef69d5785498b249ae47d70c7b7258`；
- `tools/test_portable.py`：deps/verify/server/guide 全过。

## 门禁

- Java 25/25；`test_review_fixes` 73/73；`check_hashes` 892/892；`verify_evidence` passed；
- CI：push 触发的 `build` success（见仓库 Actions）。
