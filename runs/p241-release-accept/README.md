# p241 — 发版检查器再进一步：打包后自动跑“干净环境验收”

日期：2026-11-03。p240 的 `release_check.py` 只到“门禁 + 打包”；本回合把 p208 的干净宿主验收
也接进去，让发版真正一条命令跑完。

## 改动

- `runs/p208-cross-platform/run_clean_host.py` 新增 `--zip <path>`：可指定某个包，
  不再只能“按版本号取 dist 里最新的”；
- `tools/release_check.py` 新增 `--accept`：`--build <label> --accept` 时，打包后立刻对
  `dist/mcbridge-launcher-<label>.zip` 跑 `run_clean_host.py`，结果写
  `runs/p208-cross-platform/release-accept.json`；任一步非 0 即停。

## 实测（`result.json`，测试标签 test-0.5.11）

```text
== hash manifest matches the tree          rc 0  ok=1700 mismatch=0 missing=0
== every run README/result is hashed       rc 0  325/325 coverage OK
== evidence gate (suite + unit + encoding) rc 0  passed
== portable build test-0.5.11              rc 0  11,976,725 B
== clean-host acceptance                   rc 0  8/8
release_check: PASS
```

干净宿主验收的 8 项：无系统 Python/JDK、包内解释器、0 jar、`/api/status`、`/guide` 等。

测试包已删除（避免干扰 `dist/` 里“取最新包”的逻辑）。

## 边界

- `--accept` 只跑 p208 的干净宿主验收；p227（发布包里的网页 UI 点击）仍需单独跑，
  因为它要起浏览器和 CDP；
- 测试标签不是正式版本，正式发版用真实版本号；
- 验收是“同机不同环境”，不是另一台电脑。
