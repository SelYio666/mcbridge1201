# p179 — v0.5.3 发布准备

日期：2026-10-23。把 p177（地图 atlas 多 tile + 物品展示框）与 p178（VertexBuffer 动态上传
fast path 启用）收成一个 release。

## 资产

- `dist/mcbridge-launcher-0.5.3.zip`，11,960,113 bytes；
- SHA-256 `5eaef399affc5ec745848c6615932382bcb7bcd42058a07330028c5f91b57ce3`；
- `python tools/test_portable.py --zip dist/mcbridge-launcher-0.5.3.zip --root work/launcher-e2e
  --version fabric-loader-0.19.5-1.21.1` → **RESULT: OK**（deps/verify/status/guide 全过）。

## 内容

见 `release-notes.md`：地图 atlas 边界验证、MixinVertexBuffer 压力/A-B、剩余 2 个 inert、
截图工具修复。**不宣称性能收益**。

## 门禁

- `test_review_fixes` 81/81；`check_hashes` 1000/1000；`verify_evidence` passed；Java 25/25；
- tag `v0.5.3`；GitHub Release 附件为上面的 zip。
