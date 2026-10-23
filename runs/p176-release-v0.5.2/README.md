# p176 — v0.5.2 发布准备

日期：2026-10-23。把 ImmediatelyFast 地图 atlas 的恢复（p175）与真实渲染证据收成一个 release。

## 资产

- `dist/mcbridge-launcher-0.5.2.zip`，11,960,114 bytes；
- SHA-256 `1bfbafad716b70b07fbeddd2d7ecb69c2e69b0954255e889733a23b996e1d517`；
- `python tools/test_portable.py --zip dist/mcbridge-launcher-0.5.2.zip --root work/launcher-e2e
  --version fabric-loader-0.19.5-1.21.1` → **RESULT: OK**（deps/verify/status/guide 全过）。

## 内容

见 `release-notes.md`：两个 map mixin 按 1.21.1 重写并重新登记、MapAtlasTexture 嵌入、
单人真实手持 filled_map 渲染（atlas id 绑定 + UV 重定向）、p172 失败点保留、剩余 3 个 inert
如实记录。

## 门禁

- `test_review_fixes` 79/79；`check_hashes` 以最终清单为准；`verify_evidence` passed；
  Java 25/25；地图证据 `runs/p175-map-atlas/`；
- tag `v0.5.2`；GitHub Release 附件为上面的 zip。
