# p217 — v0.5.7 发布准备

日期：2026-10-31。把 p216 页面美术优化收进便携包，并修掉验收发现的两个问题。

## 修复

- `launcher/web/app.js`：`items.slice(0, 400)` → 显式 `MAX_RENDERED = 2000`；
  计数文案改为取实际渲染行数（`shown.length`），不再用下拉选项数冒充列表数；
- `tools/test_review_fixes.py` 新增 3 条静态回归：
  - 不允许再出现 `slice(0, 400)`；
  - 上限必须显式（`MAX_RENDERED`）；
  - 计数文案必须来自渲染列表（且不得再读 `sel.options.length`）。

## 验证

- 真实后端 + Edge CDP：列表 **921** 行，文案“当前列出 921 个”，控制台 0 错误；
- `test_review_fixes` **466/466**；
- 便携包 `dist/mcbridge-launcher-0.5.7.zip`，11,963,982 bytes，
  sha256 `917faf249714e0111c0b0ee43f84ad457b8eea997f86400329dab4acdd3e8497`；
- `test_portable --root work/launcher-e2e --version neoforge-21.1.264` → RESULT: OK；
- 包内 `launcher/web/app.js` 已确认含 `MAX_RENDERED`、无 400 截断。

## 备注

- `tools/pcl_panel.py` 不在便携包内（面板为单独资产），本版只保证其源码与契约回归；
- 一轮抓取里出现过重复行（1.14.x），但干净重载后 921 行 / 921 唯一 id、与 API 一致，
  未复现，按瞬态记录（不当作已确认 bug）。

## 证据

`release-notes.md`、`fixed-list-count.png`（启动器计数修复后的真实截图）。
