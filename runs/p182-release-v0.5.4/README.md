# p182 — v0.5.4 发布准备

日期：2026-10-23。把 p181（地图 atlas 动态更新 + 正常退出清理 + 退出崩溃修复）收成一个 bugfix
release；p178 的 VertexBuffer fast path 仍包含在内。

## 资产

- `dist/mcbridge-launcher-0.5.4.zip`，11,960,114 bytes；
- SHA-256 `54961b0255f60377ce2659fb4975d7a4d51742867350b8a6bfa3577da0d6e13a`；
- `python tools/test_portable.py --zip dist/mcbridge-launcher-0.5.4.zip --root work/launcher-e2e
  --version fabric-loader-0.19.5-1.21.1` → **RESULT: OK**（deps/verify/status/guide 全过）。

## 内容

见 `release-notes.md`：动态地图更新、正常退出清理、closed NativeImage 崩溃修复、截图工具/PID
改进、p178 VertexBuffer 压力/A-B 仍在。**不宣称性能收益**。

## 门禁

- `test_review_fixes` 共 83 项（本次 82/82 + `/api/jvm` 网络 skip）；`check_hashes` 1022/1022；`verify_evidence` passed；Java 25/25；
- tag `v0.5.4`；GitHub Release 附件为上面的 zip。
