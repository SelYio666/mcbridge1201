# p125 — 总验收（2026-10-22）

本文件是一次**可交接的验收快照**：在这台机器上把仓库的自动化门禁全部重跑了一遍，并把
“已验证 / 未验证”的边界写清楚。结论只覆盖下面列出的范围，不外推。

## 门禁结果（本次重跑）

| 门禁 | 结果 |
|---|---|
| `gradle -p java test installDist` | ✅ BUILD SUCCESSFUL |
| Java JUnit | ✅ 25/25 |
| `python tools/test_review_fixes.py` | ✅ **70/70** |
| `python tools/check_hashes.py` | ✅ **790/790**（mismatch 0 / missing 0） |
| `python tools/verify_evidence.py` | ✅ passed（70/70） |
| GitHub CI（master，dispatch） | ✅ `39743576915` success |
| Release 资产 | ✅ `v0.4.6` / `mcbridge-launcher-0.4.6.zip` |
| 工作区 | ✅ 干净（`git status` 无改动） |

环境：Windows + JDK 21（`.toolchain/jdk`）、Gradle 9.8.1（`.toolchain/gradle`）、
本地 CPython 3.12 运行时；网络为中国大陆环境（官方源 + BMCL 镜像）。

## 已验证（可以对外说）

| 能力 | 证据 |
|---|---|
| Fabric 1.21.1 全量冷安装（3,911/3,911 assets、933.6 MB、0 失败）并进入单人世界 | `runs/p118-full-install-world/`（含世界截图、install-summary.json） |
| NeoForge 21.1.264 安装并到达主菜单 | `runs/p116-neoforge-launch/`（含主菜单截图、installer/launch 日志） |
| NeoForge 带模组进世界：AppleSkin / Farmer's Delight / Jade | `runs/p127`、`runs/p128`、`runs/p130`（含世界截图、模组日志、Jade tooltip） |
| Forge 1.20.1-47.4.28 带模组进世界：AppleSkin / Farmer's Delight | `runs/p129`、`runs/p131` |
| Forge/NeoForge 安装自动补原版 base（quickPlay 参数不丢） | `runs/p127`、`runs/p129`、LOADER/NEOFORGE 回归 |
| 渲染模组能力：EntityCulling 的 mixin 移植后真正生效 | `runs/p119-entityculling-mixin/`（F3 `Skipped: 1`）+ `runs/p121-entityculling-ab/`（开/关对照） |
| 下载源：按路径验证的 BMCL 镜像（含 intermediary）、404 快退、超时重试、SHA-1、来源记录 | `runs/p122-source-canary/`、`docs/download-sources.md` |
| 下载源模式：自动 / 仅官方 / 镜像优先；失败 host 健康缓存 + GUI canary 回写 | `runs/p122`、`runs/p123`、`runs/p124` |
| 1.20.1 全量冷安装 111.7 s / 739 MB / verify OK（测完删除） | `runs/p122-source-canary/full-1.20.1.json` |
| 便携包（内嵌 Python、无需梯子/无需 Python 环境） | v0.4.6 资产，`tools/test_portable.py` OK |
| 规则引擎 + 证据门禁 + CI（规则/桥/证据绑定） | `docs/FINAL-STATUS.md`、`runs/SHA256SUMS.txt` |

## 未验证 / 明确不算通过（不能对外说）

| 项 | 状态 |
|---|---|
| ImmediatelyFast 渲染批处理 | ✅ 已移植并生效：单人 + 专用服务器多人（hud=4659、itemModel=2258、itemOverlay=1129），关闭开关归零（`runs/p134`、`runs/p141`、`runs/p137`）；Iris 1.8.1/1.8.14-beta.1 兼容分支跑通（`runs/p142`/`runs/p143`，未测 shader pack） |
| Sodium / Iris | ❌ 未触碰 |
| 渲染模组“性能提升”数字 | ❌ 未测（只有 EntityCulling 的 F3 计数，不是帧率基准） |
| 完整镜像模式全量安装 | ❌ 只做了有界链路（客户端+库+120 资源）；全量镜像太慢已中止（p123） |
| NeoForge/Forge 的**带模组**世界 | ✅ 已做（p127–p131：显示/内容/数据同步）；**未测** NeoForge/Forge 专用服务器、复杂多方块模组 |
| 多人**专用**服务器（dedicated server） | ✅ Fabric 1.21.1：早期双客户端（p75/p76）+ 启动器客户端加入（p132）；**未测** NeoForge/Forge 专用服务器 |
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
- ImmediatelyFast 已完成 batching 引擎移植（HUD/物品批处理生效，A/B 可复现）；Iris、per-lighting 物品变体与帧率基准仍未做。
