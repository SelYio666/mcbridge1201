# p125 — 总验收（2026-10-22）

本文件是一次**可交接的验收快照**：在这台机器上把仓库的自动化门禁全部重跑了一遍，并把
“已验证 / 未验证”的边界写清楚。结论只覆盖下面列出的范围，不外推。

## 门禁结果（本次重跑）

| 门禁 | 结果 |
|---|---|
| `gradle -p java test installDist` | ✅ BUILD SUCCESSFUL |
| Java JUnit | ✅ 25/25 |
| `python tools/test_review_fixes.py` | ✅ **62/62** |
| `python tools/check_hashes.py` | ✅ **707/707**（mismatch 0 / missing 0） |
| `python tools/verify_evidence.py` | ✅ passed（62/62） |
| GitHub CI（master，dispatch） | ✅ `39731909944` success |
| Release 资产 | ✅ `v0.4.4` / `mcbridge-launcher-0.4.4.zip` |
| 工作区 | ✅ 干净（`git status` 无改动） |

环境：Windows + JDK 21（`.toolchain/jdk`）、Gradle 9.8.1（`.toolchain/gradle`）、
本地 CPython 3.12 运行时；网络为中国大陆环境（官方源 + BMCL 镜像）。

## 已验证（可以对外说）

| 能力 | 证据 |
|---|---|
| Fabric 1.21.1 全量冷安装（3,911/3,911 assets、933.6 MB、0 失败）并进入单人世界 | `runs/p118-full-install-world/`（含世界截图、install-summary.json） |
| NeoForge 21.1.264 安装并到达主菜单 | `runs/p116-neoforge-launch/`（含主菜单截图、installer/launch 日志） |
| 渲染模组能力：EntityCulling 的 mixin 移植后真正生效 | `runs/p119-entityculling-mixin/`（F3 `Skipped: 1`）+ `runs/p121-entityculling-ab/`（开/关对照） |
| 下载源：按路径验证的 BMCL 镜像（含 intermediary）、404 快退、超时重试、SHA-1、来源记录 | `runs/p122-source-canary/`、`docs/download-sources.md` |
| 下载源模式：自动 / 仅官方 / 镜像优先；失败 host 健康缓存 + GUI canary 回写 | `runs/p122`、`runs/p123`、`runs/p124` |
| 1.20.1 全量冷安装 111.7 s / 739 MB / verify OK（测完删除） | `runs/p122-source-canary/full-1.20.1.json` |
| 便携包（内嵌 Python、无需梯子/无需 Python 环境） | v0.4.4 资产，`tools/test_portable.py` OK |
| 规则引擎 + 证据门禁 + CI（规则/桥/证据绑定） | `docs/FINAL-STATUS.md`、`runs/SHA256SUMS.txt` |

## 未验证 / 明确不算通过（不能对外说）

| 项 | 状态 |
|---|---|
| ImmediatelyFast 渲染批处理 | ❌ 未解决：描述符已能移植，但卡在 `BatchableBufferSource.<clinit>` 的 1.21.1 BufferBuilder API，需重写 batching 引擎（`runs/p120`） |
| Sodium / Iris | ❌ 未触碰 |
| 渲染模组“性能提升”数字 | ❌ 未测（只有 EntityCulling 的 F3 计数，不是帧率基准） |
| 完整镜像模式全量安装 | ❌ 只做了有界链路（客户端+库+120 资源）；全量镜像太慢已中止（p123） |
| NeoForge/Forge 的**带模组**世界 | ❌ 未做（NeoForge 只到主菜单；Forge 早期到主菜单） |
| 便携包在其他机器/无网环境 | ❌ 未验证（仅本机解包 + `test_portable`） |
| 真实浏览器里的 UI 点击 E2E | ❌ 未做（只验证了 HTTP 端点与返回 JSON） |
| 长时间 soak / 崩溃恢复 | ❌ 未做 |

## 复现命令

```text
# Java
gradle -p java test installDist

# Python 门禁
python tools/test_review_fixes.py
python tools/check_hashes.py
python tools/verify_evidence.py

# 下载源健康（可选）
python tools/check_download_sources.py
python tools/check_download_sources.py --strict

# 安装/启动（示例）
python launcher/mclaunch.py install 1.21.1 <游戏目录>
python launcher/server.py

# 便携包
python tools/build_portable.py --label 0.4.4
python tools/test_portable.py --root <测试目录> --version 1.21.1
```

## 已知风险

- 镜像节点会随时间/地区变化，canary 只是单次采样；
- 规则文件按 `capability/risk/evidence` 绑定，新增能力必须先有真实 boot/进世界证据；
- `work/` 与 `dist/` 不入库；仓库不分发游戏/模组/转换后的 jar；
- ImmediatelyFast 若要做，属于独立大工程（batching 引擎移植 + 性能/画面验证），不应在规则层假装完成。
