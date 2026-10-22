# p122 — 下载源要不要“完整测试所有”？分层测试结论

日期：2026-10-22。问题：下载源需要把所有文件 × 所有源都测一遍吗？

**结论：不需要，也不应该。** 源会随时间波动，穷举测试既跑不完也证明不了稳定性。正确做法是
分层：**策略单测（离线）+ 可达性 canary + 目标版本全量安装**；镜像健康按 host 记录、动态排序。

## 三层各测什么

| 层 | 覆盖 | 频率/成本 | 证据 |
|---|---|---|---|
| 策略单测（mock `urlopen`） | 镜像顺序、404/超时/校验失败处理、元数据对冲、缓存、源模式、健康持久化 | 每次提交，秒级 | `tools/test_review_fixes.py` DOWNLOAD 组 23 项 |
| 可达性 canary | 官方核心 + 已验证镜像 + 已知 404 + NeoForge 独立时段 | 手动/换网络时，约 30 s，**不落盘大文件** | `tools/check_download_sources.py`、`canary.json` |
| 全量安装 | 一个版本的全部 files/assets/libraries 真实下载 + 校验 | 发布前，1–2 分钟/版本 | `runs/p118`（1.21.1）、本目录 `full-1.20.1.json` |

## 本次全量安装（1.20.1，冷启动）

| 指标 | 值 |
|---|---:|
| 耗时 | **111.7 s** |
| 落盘 | 739,217,987 B ≈ 705 MB |
| 资源对象 | 3575 |
| 文件数 | 3650 |
| `verify_install` | **OK** |
| 清理 | root 已删除（`root_cleaned: true`） |

1.21.1 的全量安装见 `runs/p118-full-install-world/`（115 s、3911/3911 assets、进世界）。

## 本次 canary（当前网络，2026-10-22 12:5x）

- 官方核心 12 项全部可达（Mojang manifest/version/asset index、client jar、library、asset
  object、Fabric meta、Fabric Loader/API/intermediary、Forge promos/installer）；
- **完整性 4 项**：官方资源对象下载后 sha1 与索引一致、镜像同一对象 sha1 一致、client jar 与
  library jar 的 PK 头正确（见 `canary.json` 的 `integrity` 段）；
- 镜像 6 项：两次连续运行结果不同——第一次 asset/manifest 超时（20 s / 28 s），第二次全部 206；
  说明镜像可用但会波动，重试即可；
- **NeoForge 两项两次均超时**（API 与 installer，20 s）：该 host 当前不稳定，不是代码结论；
  canary 默认只让“核心官方 + 完整性”决定退出码，`--strict` 才把镜像/NeoForge 纳入门禁。

## 为什么不做“所有文件 × 所有源”

- 组合是 3911 assets × N 源 + 47/70 libraries × N 源 …，每次网络波动都要重跑，成本无上限；
- 很多“镜像失败”是路径不存在（HTTP 404）而非节点故障，全量测会把正常 404 当故障；
- 真正要保证的是：**每个文件至少有一个可达来源 + 校验 + 可回退**，而全量安装正好验证了这一点；
- 源健康用 canary + 下载失败回退来持续观察，而不是一次性“证明永远可用”。

## 下载源设置与健康缓存（本次新增）

- GUI/配置新增 `download_source`：`auto`（官方优先）/ `official`（仅官方）/ `mirror`（镜像优先）；
- 近期失败的 host 记录在 `<root>/.mcbridge/source-health.json`，`auto` 模式下自动排到最后，
  成功一次后恢复；
- 失败分类：404 不惩罚 host（路径问题），超时/TLS/5xx/摘要失败才计入健康。

## 复现

```text
python tools/check_download_sources.py          # 宽松：核心必过
python tools/check_download_sources.py --strict # 镜像/NeoForge 也门禁
python tools/test_review_fixes.py               # 策略单测
```
