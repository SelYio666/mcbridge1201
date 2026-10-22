# 下载源策略与实测记录

最后更新：2026-10-21。本文回答：**哪些地址有镜像、镜像怎么验证的、失败怎么重试、怎么查
一个文件到底从哪来**。

## 1. 外部实测报告（2026-10-21）

一份独立的外部测试（`mcbridge1201-下载源测试-2026-10-21.md`，23:10–23:20 采样）对当时的
提交做了下载源实测，结论摘要：

| 环节 | 外部测试结果 |
|---|---|
| Mojang 版本清单 / JSON / 资源索引 | 正常 |
| 1.20.1、1.21.1 客户端 jar | 两个均通过大小 + SHA-1 + ZIP/CRC |
| 原版依赖库 / 资源对象 | 抽样通过；观测到 BMCL 失败后回退官方成功 |
| Fabric Loader 列表 / profile | 正常 |
| Fabric Maven 文件 | 13 个里 9 个失败（TLS 超时/中断）；**BMCL maven 对 fabric-api、intermediary 返回 404** |
| Forge | 推广列表正常；安装器下载波动（一个 TLS 超时、一个成功） |
| NeoForge | API 两次连接失败，无法验证 |

本仓库对报告的每条建议都在代码里落实了；报告本身是外部数据，镜像是否可用以本仓库
2026-10-21 23:47 的复测为准（见 §3）。

## 2. 现在的实现

### 2.1 逐路径镜像（不整域名替换）

`launcher/mclaunch.py` 的 `MIRRORS` 只重写**验证过**的前缀：

| 官方前缀 | 镜像 | 验证 |
|---|---|---|
| `resources.download.minecraft.net/` | `bmclapi2.bangbang93.com/assets/` | 外部测试回退成功 |
| `libraries.minecraft.net/` | `bmclapi2.bangbang93.com/maven/` | 外部测试回退成功 |
| `piston-data.mojang.com/` | `bmclapi2.bangbang93.com/` | 自带下载成功 |
| `piston-meta.mojang.com/` | `bmclapi2.bangbang93.com/` | 本仓库复测 HTTP 200（278,138 B） |
| `launchermeta.mojang.com/` | `bmclapi2.bangbang93.com/` | 同一 BMCL 元数据服务 |
| `meta.fabricmc.net/v2/` | `bmclapi2.bangbang93.com/fabric-meta/v2/` | 本仓库复测 HTTP 200（403,856 B） |
| `maven.fabricmc.net/net/fabricmc/fabric-loader/` | `bmclapi2.bangbang93.com/maven/net/fabricmc/fabric-loader/` | 本仓库复测 HTTP 200（1,984,980 B） |
| `maven.fabricmc.net/net/fabricmc/intermediary/` | `bmclapi2.bangbang93.com/maven/net/fabricmc/intermediary/` | 本仓库 canary 复测 206（2026-10-22） |

**故意不镜像**（复测 404，机械替换只会把可用地址换成 404）：

- `maven.fabricmc.net` 下的 `fabric-api`（BMCL 404；2026-10-22 再次确认）；
- `files.minecraftforge.net` 的推广列表（BMCL 对应路径 404）；
- NeoForge API（暂无验证可用的镜像）。

> 2026-10-22 更正：此前把 intermediary 也列为“BMCL 404”，是测试 URL 写错（用了
> 1.20.1 的 timestamp 坐标）。正确的 1.21.1 坐标在 BMCL 是可用的，已加入镜像表。

### 2.1.1 下载源模式与健康缓存

- 配置项 `download_source`：`auto`（官方优先，默认）/ `official`（只用官方）/
  `mirror`（镜像优先，官方兜底）；GUI 高级设置里可切；
- 最近失败的主机会写入 `<root>/.mcbridge/source-health.json`；`auto` 模式下
  “连续 2 次非 404 失败、且 10 分钟内”的 host 会被排到最后，成功一次后恢复；
- 404/403/410 只代表该路径在这个源不存在，**不惩罚 host**；超时/TLS/5xx/摘要失败才计入。

### 2.2 重试与错误分类

`download(url, dest, sha1=None, retries=3)`：

- 每个候选地址最多 `retries` 次，只对**可恢复错误**重试（超时、TLS、5xx、连接重置）；
- `403 / 404 / 410` 视为“这个源没有”，**立即换下一个源**，不浪费重试；
- SHA-1 不匹配：删除 `.part`，同一源重试，仍失败再换源；
- 结束/失败都会清理 `.part`；
- 返回**实际提供文件的 URL**。

`http_json(url)` 同样走镜像列表，并且是**对冲请求**：官方先发，3 秒没回就并行请求镜像，
谁先返回合法 JSON 用谁（`runs/p117` 实测：单路官方曾卡 61.9 秒，调短超时又遇到双源同时读超时）。
成功的元数据在进程内缓存 15 分钟（`METADATA_TTL`），避免重复安装/刷新时反复拉列表；
`max_age=0` 可强制绕过缓存。

`download_maven()` 会把 maven `.sha1` 记到 `<jar>.sha1`；仓库不提供/取不到时，退化为
`<jar>.local.sha1`（本地计算，只保证完整性，不宣称上游真实性）。这样 hot 安装不再为每个
Fabric 库重新请求一次 maven 侧车。

### 2.3 完整性校验

- 原版 client / libraries / assets / native：继续用 Mojang 索引里的 SHA-1；
- **Fabric Loader 库**：`download_maven()` 读取仓库的 `.sha1` 侧车文件后校验；
- **Forge / NeoForge 安装器**：同样用 `.sha1` 侧车校验（仓库发布侧车时）；
- 研究脚本 `tools/fetch_target_env.py` 走 `fetchlib.download()`，记录 `sourceUrl`。

侧车校验只证明“与仓库当前内容一致”，不防仓库本身被替换；研究用的锁定件仍以
`manifests/*.lock.json` 的 SHA-256 为准。

### 2.4 来源可见

每次下载/失败都会记一条 `DOWNLOAD_EVENTS`：

```json
{"file": "fabric-loader-0.19.5.jar", "url": "...", "final": "...",
 "mirror": false, "redirected": false, "bytes": 1984980, "attempts": 1,
 "error": null, "time": "2026-10-21 23:49:59"}
```

`url` 是发起请求的候选地址，`final` 是跟随重定向后的真实地址（例如 BMCL 的客户端请求
会跳到 `piston-data.mojang.com`，`redirected=true`），`mirror` 表示是否用了镜像候选。

安装任务的 `/api/task` 还会带 `bytes_done`、`bytes_total`、`speed`（字节/秒，指数平滑）
和当前 `source`；界面显示“文件数 + 已下载字节 + 速度 + 来源”，没有可靠总大小时不编造剩余时间。

启动器额外提供：

```text
GET /api/downloads?limit=50
```

用于排查“到底从官方还是镜像下载的、失败原因是什么”。

## 3. 本仓库复测（2026-10-21 23:47–23:50）

| 地址 | 结果 |
|---|---|
| `maven.fabricmc.net/.../fabric-loader-0.19.5.jar` | 200，1,984,980 B，侧车 SHA-1 通过 |
| `bmclapi2.../maven/net/fabricmc/fabric-loader/...jar` | 200（重定向到 `mirror.nyist.edu.cn/bmclapi`），1,984,980 B |
| `bmclapi2.../maven/net/fabricmc/fabric-api/...jar` | **404** |
| `bmclapi2.../maven/net/fabricmc/intermediary/...-v2.jar` | **404** |
| `bmclapi2.../fabric-maven/...` | 404（该前缀不存在，勿用） |
| `bmclapi2.../mc/game/version_manifest_v2.json` | 200，278,138 B |
| `bmclapi2.../fabric-meta/v2/versions/loader/1.21.1` | 200，403,856 B |
| `bmclapi2.../forge/promotions_slim.json` | 404 |
| `bmclapi2.../neoforge/versions` | 404 |
| `piston-meta.mojang.com` 版本清单（经 `http_json`） | 成功，920 个版本 |

## 3.5 冷/热对照与连接池取舍（runs/p117）

有界基准（客户端 jar + 全部允许库 + 150 个资源样本 + Fabric，冷/热各一遍，下载完删除 root）：

| 阶段 | 1.20.1 cold | 1.21.1 cold | hot |
|---|---:|---:|---:|
| 客户端 | 68.2 s / 0.45 MB/s | 8.6 s / 2.98 MB/s | ≈0 s |
| libraries | 113.6 s / 0.51 MB/s | 211.6 s / 0.30 MB/s | ≈0.2 s |
| 150 assets | 101.2 s / 0.84 MB/s | 135.3 s / 0.63 MB/s | ≈0.1 s |
| Fabric（8 库） | 36.0 s | 40.8 s | 13.1 s（仅元数据/侧车） |

结论：冷路径是**带宽/单源限速**瓶颈（单流 0.45–2.98 MB/s，24 线程资源聚合 0.63–0.84 MB/s），
连接复用不会把它变成几 MB/s；真正拖时间的是坏源等待与元数据/侧车，已用对冲请求 + TTL +
侧车本地缓存解决。因此**本仓库不引入 httpx 连接池**；未来若尝试，必须先做配对测试并保留回退。

完整数据与边界：`runs/p117-download-bench/bench.json`、同目录 `README.md`。

## 3.6 要不要“完整测试所有源”？（runs/p122）

**不需要**。源会随时间波动，穷举“所有文件 × 所有源”既跑不完也证明不了稳定性。采用分层：

| 层 | 覆盖 | 成本 | 证据 |
|---|---|---|---|
| 策略单测（mock `urlopen`） | 镜像顺序、重试/404/校验、对冲、缓存、源模式、健康持久化 | 每次提交，秒级 | `test_review_fixes.py` DOWNLOAD 组 23 项 |
| 可达性 canary | 官方核心 + 已验证镜像 + 已知 404 + NeoForge 独立 | ~30 s，不下载大文件 | `tools/check_download_sources.py` |
| 全量安装 | 某版本全部 files/assets/libraries + 校验 | 1–2 分钟/版本 | `runs/p118`（1.21.1）、`runs/p122`（1.20.1） |

- canary 默认只让**核心官方**决定退出码；`--strict` 才把镜像/NeoForge 纳入门禁；
- GUI 的“检查下载源”按钮调用同一个工具，结果写入 `<root>/.mcbridge/canary/canary.json`，
  不覆盖仓库里的 `runs/p122-source-canary/canary.json`；
- 2026-10-22 canary：核心 12 项全通、已验证镜像 6 项全通、NeoForge 两项超时（该 host 当前不可用）；
- 1.20.1 全量冷安装：**111.7 s / 739 MB / 3575 资源对象 / `verify_install` OK**，测完删除；
- 组合穷举不做；靠“至少一个可达来源 + 校验 + 回退 + 持续健康观察”保证可用性。

## 3.7 真实 `mirror` 模式（runs/p123）

强制 `mirror` 模式跑有界链路（客户端 + 全部库 + 120 资源 + Fabric）：

- 305 次下载里 **288 次走镜像**，17 次回退官方；SHA-1 校验 191/191 全匹配；
- 105 次失败尝试/122 次重试后全部成功——镜像节点确实会抖；
- 耗时 488.8 s，明显慢于官方直连（p118 全量 115 s）；
- 健康文件记录 `bmclapi2.bangbang93.com` 的近期失败（2 次），官方 host 为 0。

结论：`mirror` 是“官方不可达时的备胎”，**默认仍用 auto（官方优先）**。

## 4. 门禁与复现

离线回归（不联网，mock `urlopen`）已并入统一门禁，覆盖 **23 项**：
镜像顺序（含 Fabric Loader / intermediary）、Fabric API 不镜像、元数据镜像与对冲、
`max_age=0` 绕过缓存、404 不重试、瞬时错误重试、校验失败回退、侧车 SHA-1/缓存/本地摘要、
来源记录、字节/速度/来源上报、`/api/task`、`/api/downloads`、三种源模式、
失败 host 排序与健康持久化。

```text
python tools/test_review_fixes.py                 # DOWNLOAD 组
python tools/check_download_sources.py            # 可达性 canary（宽松）
python tools/check_download_sources.py --strict   # 镜像/NeoForge 也门禁
```

真实网络抽检：

```text
python tools/test_launcher_e2e.py --root <root> --version <vid>
python launcher/mclaunch.py install 1.21.1 <root> fabric
```

## 5. 限制（如实）

- 外部报告与本次复测都只覆盖**抽样**：没有下载两版全部依赖与 3,900+ 资源对象，也没把
  “能下载”当成“能进游戏”；
- 镜像节点会变（BMCL 会把请求转到 `mirror.nyist.edu.cn` 等节点），今天的 404/200 不保证长期；
- Fabric API / intermediary 目前没有验证可用的 BMCL 镜像，只能靠官方 + 重试；
- NeoForge API 在部分网络不可达时，启动器会直接报错并停在“版本列表取不到”，不会瞎猜版本。
