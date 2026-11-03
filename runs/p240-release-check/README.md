# p240 — 一条命令的发版检查器

日期：2026-11-03。目标：把 `docs/handover-zcode.md` 里“发版维护要跑这些”的清单变成**可执行**，
避免下一次发版靠记忆漏门禁。

## 工具

`tools/release_check.py`：

```text
python tools/release_check.py                 # 只跑门禁
python tools/release_check.py --build 0.5.11  # 门禁 + 打 dist/mcbridge-launcher-0.5.11.zip
```

依次执行：

1. `tools/check_hashes.py`（清单必须匹配工作树）；
2. `tools/check_manifest_coverage.py`（每个 tracked 的 run README/result 必须已入清单）；
3. `tools/verify_evidence.py`（套件 + 单测 + 文本编码 + 统一门禁）；
4. 可选 `tools/build_portable.py --label <ver>`（内嵌 Python 的启动器包）。

任一步失败即停、退出码非 0；`--json` 输出结构化结果；未设置 `JAVA_HOME` /
`GRADLE_USER_HOME` 时自动指向本机 `.toolchain`。

## 实测（`result.json`，标签用 test-0.5.10，避免冒充正式版）

| 步骤 | 结果 |
|---|---|
| hash manifest | `ok=1697 mismatch=0 missing=0` |
| coverage | `323/323` 证据文件已哈希 |
| evidence gate | passed |
| portable build | `mcbridge-launcher-test-0.5.10.zip`，**11,976,724 B** |

产物已删除（`dist/` 本来就被 gitignore；测试包留着会干扰 clean-host 的“取最新包”逻辑）。

## 顺手修的

第一次跑时工具自己在**打印**阶段崩了：Windows 控制台是 GBK，子进程输出里的替换字符无法编码。
已加 `sys.stdout.reconfigure(encoding="utf-8", errors="replace")`，现在能完整打印并返回 0。

## 边界

- 只覆盖“门禁 + 打包”；`runs/p208-cross-platform/run_clean_host.py` 与
  `runs/p227-shipped-launcher-pcl/drive.py` 这两个发布验收仍是单独步骤，没塞进来（它们要起服务/浏览器）；
- 测试标签不是正式版本号，正式发版时用真实版本。
