# p174 — v0.5.1 发布准备

日期：2026-10-23。把 v0.5.0 之后的端口补丁与服务器/mrpack 证据收成一个 release。

## 资产

- `dist/mcbridge-launcher-0.5.1.zip`，11,960,114 bytes；
- SHA-256 `3e1345e61d73eb895e4ec644c83b0fadc6dc508135c74a2bfda7ccb86a4e989b`；
- `python tools/test_portable.py --zip dist/mcbridge-launcher-0.5.1.zip --root work/launcher-e2e
  --version neoforge-21.1.264` → **RESULT: OK**（deps/verify/status/guide 全过）。

## 内容

见 `release-notes.md`：3 个 mixin 重新登记、MapTexture 显式 strip（潜在 ClassCastException）、
地图 atlas 尝试失败回滚、剩余 inert 分析、Forge/NeoForge 带 FD 专用服务器、真实 mrpack、
性能 A/B 的诚实结论。

## 门禁

- `test_review_fixes` 73/73；`check_hashes` 944/944；`verify_evidence` passed；Java 25/25；
- tag `v0.5.1`；GitHub Release 附件为上面的 zip。
